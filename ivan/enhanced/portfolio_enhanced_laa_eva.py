"""
Enhanced LAA-EVA System with Comprehensive Portfolio Management
Includes position sizing, drawdown limits, and detailed trade logging
"""

import json
import uuid
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union, Literal, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from itertools import product
import random
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ==================== PORTFOLIO CONFIGURATION ====================
@dataclass
class PortfolioConfig:
    """Configuration for portfolio management"""
    initial_capital_eth: float = 10.0           # Starting portfolio in ETH
    position_size_pct: float = 5.0              # % of portfolio per trade
    max_concurrent_positions: int = 5           # Max open positions
    max_drawdown_pct: float = 50.0             # Stop trading at this drawdown
    recovery_threshold_pct: float = 75.0        # Resume trading at this recovery
    reserve_capital_pct: float = 20.0          # Keep as reserve
    compound_profits: bool = True               # Reinvest profits
    position_sizing_mode: str = "fixed"         # fixed, kelly, or risk_adjusted

    # Signal-based position sizing multipliers
    position_multipliers: Dict[int, float] = field(default_factory=lambda: {
        7: 1.5,   # Strong signals get 1.5x position size
        3: 1.0,   # Normal signals get 1x
        -3: 1.0,  # Normal signals get 1x
        -7: 1.5   # Strong signals get 1.5x
    })

    # Risk limits
    max_position_risk_pct: float = 2.0         # Max risk per position (% of portfolio)
    daily_loss_limit_pct: float = 10.0         # Max daily loss

    def get_position_size(self, portfolio_value: float, signal_strength: int) -> float:
        """Calculate position size based on portfolio value and signal strength"""
        base_size = portfolio_value * (self.position_size_pct / 100)

        # Apply signal strength multiplier
        multiplier = self.position_multipliers.get(abs(signal_strength), 1.0)

        # Apply reserve capital constraint
        available_capital = portfolio_value * (1 - self.reserve_capital_pct / 100)

        position_size = min(base_size * multiplier, available_capital)

        return position_size


# ==================== OPTION INSTRUMENTS ====================
class OptionInstruments:
    """Define available option instruments with costs"""
    INSTRUMENTS = {
        "3D_5PCT": {
            "duration_days": 3,
            "profit_cap_pct": 5,
            "premium_cost_pct": 2.2,
            "description": "3-day option with 5% profit cap"
        },
        "3D_10PCT": {
            "duration_days": 3,
            "profit_cap_pct": 10,
            "premium_cost_pct": 2.6,
            "description": "3-day option with 10% profit cap"
        },
        "7D_5PCT": {
            "duration_days": 7,
            "profit_cap_pct": 5,
            "premium_cost_pct": 2.8,
            "description": "7-day option with 5% profit cap"
        },
        "7D_10PCT": {
            "duration_days": 7,
            "profit_cap_pct": 10,
            "premium_cost_pct": 2.8,
            "description": "7-day option with 10% profit cap"
        }
    }

    @classmethod
    def get_instrument(cls, instrument_type: str) -> Dict[str, Any]:
        return cls.INSTRUMENTS.get(instrument_type, cls.INSTRUMENTS["3D_5PCT"])


# ==================== ENHANCED TRADE LOG ====================
@dataclass
class TradeLog:
    """Detailed trade information"""
    trade_id: str
    entry_time: datetime
    exit_time: Optional[datetime]
    instrument_type: str
    signal_strength: int
    entry_price: float
    exit_price: Optional[float]
    position_size_eth: float
    position_size_pct: float
    premium_cost_eth: float
    premium_cost_pct: float
    pnl_eth: Optional[float]
    pnl_pct: Optional[float]
    capital_before: float
    capital_after: Optional[float]
    portfolio_pct_before: float
    portfolio_pct_after: Optional[float]
    concurrent_positions: int
    win: Optional[bool]
    exit_reason: Optional[str]  # "expiry", "stop_loss", "take_profit", "max_drawdown"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'trade_id': self.trade_id,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'instrument_type': self.instrument_type,
            'signal_strength': self.signal_strength,
            'entry_price': round(self.entry_price, 2),
            'exit_price': round(self.exit_price, 2) if self.exit_price else None,
            'position_size_eth': round(self.position_size_eth, 4),
            'position_size_pct': round(self.position_size_pct, 2),
            'premium_cost_eth': round(self.premium_cost_eth, 4),
            'premium_cost_pct': round(self.premium_cost_pct, 2),
            'pnl_eth': round(self.pnl_eth, 4) if self.pnl_eth is not None else None,
            'pnl_pct': round(self.pnl_pct, 2) if self.pnl_pct is not None else None,
            'capital_before': round(self.capital_before, 2),
            'capital_after': round(self.capital_after, 2) if self.capital_after else None,
            'portfolio_pct_before': round(self.portfolio_pct_before, 2),
            'portfolio_pct_after': round(self.portfolio_pct_after, 2) if self.portfolio_pct_after else None,
            'concurrent_positions': self.concurrent_positions,
            'win': self.win,
            'exit_reason': self.exit_reason
        }


# ==================== ENHANCED OPTIONS SIGNAL ====================
@dataclass
class EnhancedOptionsSignal:
    """Enhanced options trading signal"""
    strategy_id: uuid.UUID
    signal: int
    instrument_type: str
    profit_cap_pct: float
    premium_cost_pct: float
    duration_days: int
    last_close: float
    timestamp: datetime
    rule_triggered: str
    expected_move_pct: float
    volatility: float


# ==================== PORTFOLIO MANAGER ====================
class PortfolioManager:
    """Manages portfolio state and risk limits"""

    def __init__(self, config: PortfolioConfig):
        self.config = config
        self.capital_eth = config.initial_capital_eth
        self.peak_capital = config.initial_capital_eth
        self.active_positions: List[Dict[str, Any]] = []
        self.trade_logs: List[TradeLog] = []
        self.is_trading_enabled = True
        self.daily_loss = 0
        self.last_trading_day = None

    def calculate_drawdown(self) -> float:
        """Calculate current drawdown from peak"""
        if self.peak_capital > 0:
            return ((self.peak_capital - self.capital_eth) / self.peak_capital) * 100
        return 0

    def update_peak(self):
        """Update peak capital for drawdown calculation"""
        if self.capital_eth > self.peak_capital:
            self.peak_capital = self.capital_eth

    def check_trading_enabled(self) -> bool:
        """Check if trading should be enabled based on risk limits"""
        current_drawdown = self.calculate_drawdown()

        # Check max drawdown
        if current_drawdown >= self.config.max_drawdown_pct:
            self.is_trading_enabled = False
            logger.warning(f"Trading disabled: Max drawdown {current_drawdown:.1f}% reached")
            return False

        # Check recovery threshold
        if not self.is_trading_enabled:
            recovery_level = self.peak_capital * (self.config.recovery_threshold_pct / 100)
            if self.capital_eth >= recovery_level:
                self.is_trading_enabled = True
                logger.info(f"Trading re-enabled: Capital recovered to {self.capital_eth:.2f} ETH")

        return self.is_trading_enabled

    def can_open_position(self, signal_strength: int) -> Tuple[bool, float, str]:
        """
        Check if a new position can be opened
        Returns: (can_open, position_size, reason)
        """
        if not self.check_trading_enabled():
            return False, 0, "Trading disabled due to drawdown"

        # Check max concurrent positions
        if len(self.active_positions) >= self.config.max_concurrent_positions:
            return False, 0, f"Max concurrent positions ({self.config.max_concurrent_positions}) reached"

        # Calculate position size
        position_size = self.config.get_position_size(self.capital_eth, signal_strength)

        # Check if we have enough available capital
        invested_capital = sum(pos['size_eth'] for pos in self.active_positions)
        available_capital = self.capital_eth - invested_capital

        if position_size > available_capital:
            position_size = available_capital

        if position_size <= 0:
            return False, 0, "Insufficient available capital"

        return True, position_size, "OK"

    def open_position(self, signal: EnhancedOptionsSignal, current_price: float) -> Optional[str]:
        """Open a new position"""
        can_open, position_size, reason = self.can_open_position(signal.signal)

        if not can_open:
            logger.debug(f"Cannot open position: {reason}")
            return None

        trade_id = str(uuid.uuid4())[:8]

        # Calculate premium cost
        premium_cost_eth = position_size * (signal.premium_cost_pct / 100)

        # Create position
        position = {
            'trade_id': trade_id,
            'entry_time': signal.timestamp,
            'entry_price': current_price,
            'signal_strength': signal.signal,
            'instrument_type': signal.instrument_type,
            'profit_cap': signal.profit_cap_pct / 100,
            'premium_cost': signal.premium_cost_pct / 100,
            'duration_days': signal.duration_days,
            'size_eth': position_size,
            'premium_paid_eth': premium_cost_eth
        }

        self.active_positions.append(position)

        # Deduct premium immediately
        self.capital_eth -= premium_cost_eth

        # Create trade log
        trade_log = TradeLog(
            trade_id=trade_id,
            entry_time=signal.timestamp,
            exit_time=None,
            instrument_type=signal.instrument_type,
            signal_strength=signal.signal,
            entry_price=current_price,
            exit_price=None,
            position_size_eth=position_size,
            position_size_pct=(position_size / self.config.initial_capital_eth) * 100,
            premium_cost_eth=premium_cost_eth,
            premium_cost_pct=signal.premium_cost_pct,
            pnl_eth=None,
            pnl_pct=None,
            capital_before=self.capital_eth + premium_cost_eth,
            capital_after=None,
            portfolio_pct_before=((self.capital_eth + premium_cost_eth) / self.config.initial_capital_eth) * 100,
            portfolio_pct_after=None,
            concurrent_positions=len(self.active_positions),
            win=None,
            exit_reason=None
        )

        self.trade_logs.append(trade_log)

        logger.info(f"Opened position {trade_id}: {position_size:.3f} ETH, "
                   f"{signal.instrument_type}, Signal: {signal.signal}")

        return trade_id

    def close_position(self, position: Dict, exit_price: float, exit_time: datetime,
                       exit_reason: str = "expiry") -> float:
        """Close a position and return P&L"""
        # Calculate option P&L
        price_change = (exit_price - position['entry_price']) / position['entry_price']

        if position['signal_strength'] > 0:  # CALL
            raw_pnl = max(0, price_change)
        else:  # PUT
            raw_pnl = max(0, -price_change)

        # Apply profit cap
        capped_pnl = min(raw_pnl, position['profit_cap'])

        # Calculate P&L in ETH (premium already paid)
        pnl_eth = position['size_eth'] * capped_pnl

        # Update capital
        self.capital_eth += pnl_eth
        self.update_peak()

        # Update trade log
        for trade_log in self.trade_logs:
            if trade_log.trade_id == position['trade_id']:
                trade_log.exit_time = exit_time
                trade_log.exit_price = exit_price
                trade_log.pnl_eth = pnl_eth - position['premium_paid_eth']  # Net P&L
                trade_log.pnl_pct = ((pnl_eth - position['premium_paid_eth']) / position['size_eth']) * 100
                trade_log.capital_after = self.capital_eth
                trade_log.portfolio_pct_after = (self.capital_eth / self.config.initial_capital_eth) * 100
                trade_log.win = trade_log.pnl_eth > 0
                trade_log.exit_reason = exit_reason
                break

        # Remove from active positions
        self.active_positions.remove(position)

        net_pnl = pnl_eth - position['premium_paid_eth']
        logger.info(f"Closed position {position['trade_id']}: Net P&L: {net_pnl:.4f} ETH, "
                   f"Capital: {self.capital_eth:.2f} ETH")

        return net_pnl


# ==================== TECHNICAL INDICATORS ====================
class TechnicalIndicators:
    """Manual implementation of technical indicators"""

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return pd.DataFrame({
            f'MACD_{fast}_{slow}_{signal}': macd_line,
            f'MACDs_{fast}_{slow}_{signal}': signal_line,
            f'MACDh_{fast}_{slow}_{signal}': histogram
        })

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        high_low = high - low
        high_close = (high - close.shift()).abs()
        low_close = (low - close.shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr

    @staticmethod
    def expected_move(close: pd.Series, atr: pd.Series, rsi: pd.Series,
                     macd_hist: pd.Series) -> pd.Series:
        rsi_momentum = (rsi - 50) / 50
        macd_momentum = np.tanh(macd_hist / close * 100)
        momentum_factor = (rsi_momentum + macd_momentum) / 2
        expected_move_pct = (atr / close) * 100 * (1 + momentum_factor)
        return expected_move_pct


# ==================== DSL EXECUTOR ====================
class PortfolioAwareDslExecutor:
    """DSL Executor that works with PortfolioManager"""

    def __init__(self, strategy_definition_dsl: Dict[str, Any], strategy_id: str):
        self.dsl = strategy_definition_dsl
        self.strategy_id = strategy_id
        self.constants = self.dsl.get('constants', {})
        self.indicator_outputs = {}
        self.indicators = TechnicalIndicators()
        self.option_instruments = OptionInstruments()
        logger.info(f"PortfolioAwareDslExecutor initialized for strategy {strategy_id}")

    def _resolve_value(self, value_or_ref: Any) -> Any:
        if isinstance(value_or_ref, str) and value_or_ref.startswith("@"):
            const_name = value_or_ref[1:]
            if const_name in self.constants:
                return self.constants[const_name]
            else:
                raise ValueError(f"Undefined constant: {value_or_ref}")
        return value_or_ref

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df_with_indicators = df.copy()

        for indicator in self.dsl.get('indicators', []):
            indicator_type = indicator['type'].lower()
            params = indicator['params']
            outputs = indicator['outputs']

            resolved_params = {}
            for key, value in params.items():
                if value is not None:
                    resolved_params[key] = self._resolve_value(value)

            try:
                if indicator_type == 'rsi':
                    length = resolved_params.get('length', 14)
                    rsi_result = self.indicators.rsi(df['close'], length)
                    primary_col = outputs['primary_output_column']
                    df_with_indicators[primary_col] = rsi_result
                    self.indicator_outputs[primary_col] = rsi_result

                elif indicator_type == 'macd':
                    fast = resolved_params.get('fast', 12)
                    slow = resolved_params.get('slow', 26)
                    signal = resolved_params.get('signal', 9)
                    macd_result = self.indicators.macd(df['close'], fast, slow, signal)

                    if outputs.get('component_output_map'):
                        for ta_col, user_col in outputs['component_output_map'].items():
                            if ta_col in macd_result.columns:
                                df_with_indicators[user_col] = macd_result[ta_col]
                                self.indicator_outputs[user_col] = macd_result[ta_col]

                elif indicator_type == 'sma':
                    length = resolved_params.get('length', 20)
                    sma_result = self.indicators.sma(df['close'], length)
                    primary_col = outputs['primary_output_column']
                    df_with_indicators[primary_col] = sma_result
                    self.indicator_outputs[primary_col] = sma_result

                elif indicator_type == 'ema':
                    length = resolved_params.get('length', 20)
                    ema_result = self.indicators.ema(df['close'], length)
                    primary_col = outputs['primary_output_column']
                    df_with_indicators[primary_col] = ema_result
                    self.indicator_outputs[primary_col] = ema_result

                elif indicator_type == 'atr':
                    length = resolved_params.get('length', 14)
                    atr_result = self.indicators.atr(df['high'], df['low'], df['close'], length)
                    primary_col = outputs['primary_output_column']
                    df_with_indicators[primary_col] = atr_result
                    self.indicator_outputs[primary_col] = atr_result

            except Exception as e:
                logger.warning(f"Error calculating {indicator_type}: {e}")
                primary_col = outputs['primary_output_column']
                df_with_indicators[primary_col] = np.nan

        # Calculate expected move
        if 'rsi_value' in df_with_indicators.columns and 'macd_hist' in df_with_indicators.columns and 'atr_value' in df_with_indicators.columns:
            df_with_indicators['expected_move_pct'] = self.indicators.expected_move(
                df['close'],
                df_with_indicators['atr_value'],
                df_with_indicators['rsi_value'],
                df_with_indicators['macd_hist']
            )
        else:
            if 'atr_value' in df_with_indicators.columns:
                df_with_indicators['expected_move_pct'] = (df_with_indicators['atr_value'] / df['close']) * 100
            else:
                df_with_indicators['expected_move_pct'] = 2.0

        return df_with_indicators

    def _evaluate_condition(self, condition: Dict[str, Any], row: pd.Series,
                           df: pd.DataFrame, idx: int) -> bool:
        series1 = condition['series1']
        operator = condition['operator'].lower()
        series2_or_value = condition['series2_or_value']

        val1 = self._get_value(series1, row)
        val2 = self._get_value(series2_or_value, row)

        if pd.isna(val1) or pd.isna(val2):
            return False

        if operator == '>':
            return val1 > val2
        elif operator == '<':
            return val1 < val2
        elif operator == '>=':
            return val1 >= val2
        elif operator == '<=':
            return val1 <= val2
        elif operator == '==':
            return np.isclose(val1, val2)
        elif operator == '!=':
            return not np.isclose(val1, val2)
        elif operator in ['crosses_above', 'crosses_below']:
            if idx < 1:
                return False
            prev_row = df.iloc[idx - 1]
            prev_val1 = self._get_value(series1, prev_row)
            prev_val2 = self._get_value(series2_or_value, prev_row)

            if pd.isna(prev_val1) or pd.isna(prev_val2):
                return False

            if operator == 'crosses_above':
                return prev_val1 <= prev_val2 and val1 > val2
            elif operator == 'crosses_below':
                return prev_val1 >= prev_val2 and val1 < val2

        return False

    def _get_value(self, series_or_value: Any, row: pd.Series) -> Any:
        if isinstance(series_or_value, str):
            if series_or_value.startswith('@'):
                return self._resolve_value(series_or_value)
            elif series_or_value in row.index:
                return row[series_or_value]
            else:
                return np.nan
        else:
            return series_or_value

    def _evaluate_condition_group(self, group: Dict[str, Any], row: pd.Series,
                                 df: pd.DataFrame, idx: int) -> bool:
        operator = group['operator'].upper()
        conditions = group['conditions']

        if not conditions:
            return False

        results = [self._evaluate_condition(c, row, df, idx) for c in conditions]

        if operator == 'AND':
            return all(results)
        elif operator == 'OR':
            return any(results)
        else:
            return False

    def _select_instrument(self, rule: Dict[str, Any], row: pd.Series) -> Dict[str, Any]:
        expected_move = float(row.get('expected_move_pct', 2.0))
        volatility = float(row.get('atr_value', 50) / row.get('close', 1) * 100)

        rule_metadata = rule.get('instrument_selection', {})
        time_horizon = rule_metadata.get('time_horizon_days', 3)

        vol_threshold_raw = rule_metadata.get('volatility_threshold', 3.0)
        if isinstance(vol_threshold_raw, str) and vol_threshold_raw.startswith('@'):
            volatility_threshold = float(self._resolve_value(vol_threshold_raw))
        else:
            volatility_threshold = float(vol_threshold_raw)

        signal_strength = abs(rule['action_on_true']['strength'])

        if signal_strength >= 7:
            if volatility > volatility_threshold:
                instrument_type = "3D_10PCT" if expected_move > 7 else "3D_5PCT"
            else:
                instrument_type = "7D_10PCT" if expected_move > 5 else "7D_5PCT"
        else:
            if volatility > volatility_threshold:
                instrument_type = "3D_5PCT"
            else:
                instrument_type = "7D_5PCT" if expected_move < 5 else "3D_5PCT"

        if 'instrument_type' in rule['action_on_true']:
            instrument_type = rule['action_on_true']['instrument_type']

        return self.option_instruments.get_instrument(instrument_type)

    def generate_signals(self, df: pd.DataFrame) -> List[EnhancedOptionsSignal]:
        df = df.copy()
        df.columns = [col.lower() for col in df.columns]

        df_with_indicators = self._calculate_indicators(df)

        signals = []
        default_action = self.dsl.get('default_action_on_no_match', {
            'signal_type': 'NEUTRAL',
            'strength': 0,
            'instrument_type': '3D_5PCT'
        })

        for idx in range(len(df_with_indicators)):
            row = df_with_indicators.iloc[idx]
            # Use timestamp column if available, otherwise use index
            if 'timestamp' in df_with_indicators.columns:
                timestamp = pd.to_datetime(row['timestamp'])
            else:
                timestamp = pd.to_datetime(df_with_indicators.index[idx])
            last_close = row.get('close', np.nan)

            signal_generated = False

            for rule in self.dsl.get('signal_rules', []):
                conditions_group = rule['conditions_group']

                if self._evaluate_condition_group(conditions_group, row, df_with_indicators, idx):
                    action = rule['action_on_true']
                    instrument = self._select_instrument(rule, row)

                    inst_type = None
                    for key, val in self.option_instruments.INSTRUMENTS.items():
                        if val == instrument:
                            inst_type = key
                            break

                    signals.append(EnhancedOptionsSignal(
                        strategy_id=uuid.UUID(self.strategy_id),
                        signal=action['strength'],
                        instrument_type=inst_type or '3D_5PCT',
                        profit_cap_pct=instrument['profit_cap_pct'],
                        premium_cost_pct=instrument['premium_cost_pct'],
                        duration_days=instrument['duration_days'],
                        last_close=last_close,
                        timestamp=timestamp,
                        rule_triggered=rule['rule_name'],
                        expected_move_pct=row.get('expected_move_pct', 2.0),
                        volatility=row.get('atr_value', 50) / last_close * 100 if not pd.isna(last_close) else 2.0
                    ))
                    signal_generated = True
                    break

            if not signal_generated:
                default_instrument = self.option_instruments.get_instrument(
                    default_action.get('instrument_type', '3D_5PCT')
                )
                signals.append(EnhancedOptionsSignal(
                    strategy_id=uuid.UUID(self.strategy_id),
                    signal=default_action['strength'],
                    instrument_type=default_action.get('instrument_type', '3D_5PCT'),
                    profit_cap_pct=default_instrument['profit_cap_pct'],
                    premium_cost_pct=default_instrument['premium_cost_pct'],
                    duration_days=default_instrument['duration_days'],
                    last_close=last_close,
                    timestamp=timestamp,
                    rule_triggered='DEFAULT',
                    expected_move_pct=row.get('expected_move_pct', 2.0),
                    volatility=row.get('atr_value', 50) / last_close * 100 if not pd.isna(last_close) else 2.0
                ))

        return signals


# ==================== ENHANCED BACKTESTER ====================
class PortfolioBacktester:
    """Backtester with portfolio management"""

    def __init__(self, portfolio_config: PortfolioConfig):
        self.portfolio_config = portfolio_config

    def run_backtest(self, signals: List[EnhancedOptionsSignal],
                     ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
        """Run backtest with portfolio management"""
        portfolio_manager = PortfolioManager(self.portfolio_config)

        # Create signal lookup
        signal_dict = {s.timestamp: s for s in signals}

        # Track additional metrics
        capital_history = []
        drawdown_history = []
        positions_history = []

        for idx in range(len(ohlcv_df)):
            timestamp = pd.to_datetime(ohlcv_df.index[idx])
            current_price = ohlcv_df.iloc[idx]['close']

            # Check for position expiries
            expired_positions = []
            for pos in portfolio_manager.active_positions:
                days_held = (timestamp - pos['entry_time']).days
                if days_held >= pos['duration_days']:
                    expired_positions.append(pos)

            # Close expired positions
            for pos in expired_positions:
                portfolio_manager.close_position(pos, current_price, timestamp, "expiry")

            # Check for new signals
            if timestamp in signal_dict:
                signal = signal_dict[timestamp]

                if signal.signal != 0:
                    portfolio_manager.open_position(signal, current_price)

            # Record portfolio state
            capital_history.append({
                'timestamp': timestamp,
                'capital_eth': portfolio_manager.capital_eth,
                'drawdown_pct': portfolio_manager.calculate_drawdown(),
                'active_positions': len(portfolio_manager.active_positions)
            })

        # Calculate comprehensive statistics
        stats = self._calculate_statistics(portfolio_manager, capital_history)

        # Prepare detailed output
        return {
            'trade_logs': [log.to_dict() for log in portfolio_manager.trade_logs],
            'statistics': stats,
            'capital_history': capital_history,
            'portfolio_config': {
                'initial_capital_eth': self.portfolio_config.initial_capital_eth,
                'position_size_pct': self.portfolio_config.position_size_pct,
                'max_concurrent_positions': self.portfolio_config.max_concurrent_positions,
                'max_drawdown_pct': self.portfolio_config.max_drawdown_pct
            }
        }

    def _calculate_statistics(self, portfolio_manager: PortfolioManager,
                             capital_history: List[Dict]) -> Dict[str, Any]:
        """Calculate comprehensive statistics"""
        trade_logs = portfolio_manager.trade_logs
        completed_trades = [t for t in trade_logs if t.exit_time is not None]

        if not completed_trades:
            return self._empty_statistics()

        # Basic metrics
        winning_trades = [t for t in completed_trades if t.win]
        losing_trades = [t for t in completed_trades if not t.win]

        total_return_eth = portfolio_manager.capital_eth - self.portfolio_config.initial_capital_eth
        total_return_pct = (total_return_eth / self.portfolio_config.initial_capital_eth) * 100

        win_rate = len(winning_trades) / len(completed_trades) * 100 if completed_trades else 0

        # P&L metrics
        avg_win_pct = np.mean([t.pnl_pct for t in winning_trades]) if winning_trades else 0
        avg_loss_pct = np.mean([t.pnl_pct for t in losing_trades]) if losing_trades else 0

        # Time metrics
        first_trade = min(completed_trades, key=lambda x: x.entry_time)
        last_trade = max(completed_trades, key=lambda x: x.exit_time)
        trading_days = (last_trade.exit_time - first_trade.entry_time).days

        # Capital efficiency
        avg_positions = np.mean([h['active_positions'] for h in capital_history])
        max_positions = max([h['active_positions'] for h in capital_history])

        # Position sizing metrics
        avg_position_size_eth = np.mean([t.position_size_eth for t in completed_trades])
        avg_position_size_pct = np.mean([t.position_size_pct for t in completed_trades])

        # Risk metrics
        max_drawdown = max([h['drawdown_pct'] for h in capital_history])

        # Calculate Sharpe ratio
        if len(completed_trades) > 1:
            returns = [t.pnl_pct for t in completed_trades]
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0

        # APR calculations
        # Simple APR
        simple_apr = (total_return_pct * 365 / trading_days) if trading_days > 0 else 0

        # Capital-efficiency adjusted APR
        capital_utilization = (avg_positions / self.portfolio_config.max_concurrent_positions) * 100
        effective_capital_deployed = self.portfolio_config.initial_capital_eth * (avg_position_size_pct / 100) * avg_positions

        if effective_capital_deployed > 0 and trading_days > 0:
            capital_efficient_apr = (total_return_eth / effective_capital_deployed) * 365 / trading_days * 100
        else:
            capital_efficient_apr = 0

        return {
            # Basic metrics
            'total_trades': len(completed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate_pct': win_rate,

            # Return metrics
            'total_return_eth': total_return_eth,
            'total_return_pct': total_return_pct,
            'final_capital_eth': portfolio_manager.capital_eth,

            # P&L metrics
            'avg_win_pct': avg_win_pct,
            'avg_loss_pct': avg_loss_pct,
            'profit_factor': abs(sum([t.pnl_eth for t in winning_trades]) / sum([t.pnl_eth for t in losing_trades])) if losing_trades else float('inf'),

            # Risk metrics
            'max_drawdown_pct': max_drawdown,
            'sharpe_ratio': sharpe_ratio,

            # APR metrics
            'simple_apr': simple_apr,
            'capital_efficient_apr': capital_efficient_apr,

            # Capital efficiency
            'avg_positions_held': avg_positions,
            'max_positions_held': max_positions,
            'capital_utilization_pct': capital_utilization,
            'avg_position_size_eth': avg_position_size_eth,
            'avg_position_size_pct': avg_position_size_pct,

            # Time metrics
            'trading_days': trading_days,
            'trades_per_day': len(completed_trades) / trading_days if trading_days > 0 else 0,

            # Cost metrics
            'total_premium_paid_eth': sum([t.premium_cost_eth for t in completed_trades]),
            'avg_premium_cost_pct': np.mean([t.premium_cost_pct for t in completed_trades])
        }

    def _empty_statistics(self) -> Dict[str, Any]:
        """Return empty statistics when no trades"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate_pct': 0,
            'total_return_eth': 0,
            'total_return_pct': 0,
            'final_capital_eth': self.portfolio_config.initial_capital_eth,
            'avg_win_pct': 0,
            'avg_loss_pct': 0,
            'profit_factor': 0,
            'max_drawdown_pct': 0,
            'sharpe_ratio': 0,
            'simple_apr': 0,
            'capital_efficient_apr': 0,
            'avg_positions_held': 0,
            'max_positions_held': 0,
            'capital_utilization_pct': 0,
            'avg_position_size_eth': 0,
            'avg_position_size_pct': 0,
            'trading_days': 0,
            'trades_per_day': 0,
            'total_premium_paid_eth': 0,
            'avg_premium_cost_pct': 0
        }


# ==================== STRATEGY GENERATOR ====================
def generate_test_strategy() -> Dict[str, Any]:
    """Generate a test strategy with portfolio management hints"""
    return {
        "strategy_logic_dsl": {
            "dsl_version": "2.1",
            "description": "Portfolio-aware strategy for ETH",
            "constants": {
                "rsi_oversold": 30,
                "rsi_overbought": 70,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "sma_short_period": 10,
                "sma_long_period": 30,
                "atr_period": 14,
                "atr_threshold": 50,
                "high_vol_threshold": 3.0
            },
            "indicators": [
                {
                    "name": "rsi_main",
                    "type": "rsi",
                    "params": {"length": 14, "column": "close"},
                    "outputs": {"primary_output_column": "rsi_value"}
                },
                {
                    "name": "macd_main",
                    "type": "macd",
                    "params": {
                        "fast": "@macd_fast",
                        "slow": "@macd_slow",
                        "signal": "@macd_signal",
                        "column": "close"
                    },
                    "outputs": {
                        "primary_output_column": "macd_line",
                        "component_output_map": {
                            "MACD_12_26_9": "macd_line",
                            "MACDs_12_26_9": "macd_signal",
                            "MACDh_12_26_9": "macd_hist"
                        }
                    }
                },
                {
                    "name": "sma_short",
                    "type": "sma",
                    "params": {"length": "@sma_short_period", "column": "close"},
                    "outputs": {"primary_output_column": "sma_short"}
                },
                {
                    "name": "sma_long",
                    "type": "sma",
                    "params": {"length": "@sma_long_period", "column": "close"},
                    "outputs": {"primary_output_column": "sma_long"}
                },
                {
                    "name": "atr",
                    "type": "atr",
                    "params": {"length": "@atr_period"},
                    "outputs": {"primary_output_column": "atr_value"}
                }
            ],
            "signal_rules": [
                {
                    "rule_name": "strong_bearish_signal",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {"series1": "close", "operator": "crosses_below", "series2_or_value": "sma_short"},
                            {"series1": "sma_short", "operator": "<", "series2_or_value": "sma_long"},
                            {"series1": "macd_hist", "operator": "<", "series2_or_value": 0},
                            {"series1": "rsi_value", "operator": "<", "series2_or_value": 40}
                        ]
                    },
                    "action_on_true": {
                        "signal_type": "PUT",
                        "strength": -7
                    },
                    "instrument_selection": {
                        "time_horizon_days": 7,
                        "volatility_threshold": "@high_vol_threshold"
                    }
                },
                {
                    "rule_name": "oversold_bounce",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {"series1": "rsi_value", "operator": "<", "series2_or_value": "@rsi_oversold"},
                            {"series1": "macd_line", "operator": "crosses_above", "series2_or_value": "macd_signal"}
                        ]
                    },
                    "action_on_true": {
                        "signal_type": "CALL",
                        "strength": 3
                    },
                    "instrument_selection": {
                        "time_horizon_days": 3,
                        "volatility_threshold": "@high_vol_threshold"
                    }
                }
            ],
            "default_action_on_no_match": {
                "signal_type": "NEUTRAL",
                "strength": 0,
                "instrument_type": "3D_5PCT"
            }
        },
        "name": "Portfolio_Aware_Strategy",
        "description": "Strategy with portfolio management"
    }


# ==================== MAIN EXECUTION ====================
def load_market_data(filepath: str) -> pd.DataFrame:
    """Load market data"""
    with open(filepath, 'r') as f:
        data = json.load(f)

    df = pd.DataFrame(data['ohlcv'])
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    df.columns = [col.lower() for col in df.columns]

    return df


def print_trade_logs(trade_logs: List[Dict[str, Any]]):
    """Print detailed trade logs"""
    print("\n" + "=" * 120)
    print("INDIVIDUAL TRADE LOGS")
    print("=" * 120)

    for i, trade in enumerate(trade_logs, 1):
        print(f"\nTrade #{i} [{trade['trade_id']}]:")
        print(f"  Entry: {trade['entry_time']} @ ${trade['entry_price']:.2f}")
        if trade['exit_time']:
            print(f"  Exit:  {trade['exit_time']} @ ${trade['exit_price']:.2f}")
        print(f"  Type: {trade['instrument_type']} | Signal: {trade['signal_strength']}")
        print(f"  Position: {trade['position_size_eth']:.4f} ETH ({trade['position_size_pct']:.1f}% of initial)")
        print(f"  Premium: {trade['premium_cost_eth']:.4f} ETH ({trade['premium_cost_pct']:.1f}%)")
        if trade['pnl_eth'] is not None:
            status = "WIN" if trade['win'] else "LOSS"
            print(f"  P&L: {trade['pnl_eth']:.4f} ETH ({trade['pnl_pct']:.2f}%) - {status}")
            print(f"  Capital: {trade['capital_before']:.2f} → {trade['capital_after']:.2f} ETH")
        print(f"  Concurrent Positions: {trade['concurrent_positions']}")
        if trade['exit_reason']:
            print(f"  Exit Reason: {trade['exit_reason']}")


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("PORTFOLIO-ENHANCED LAA-EVA SYSTEM")
    logger.info("=" * 80)

    # Load market data
    try:
        ohlcv_df = load_market_data('/Users/ivanhmac/github/pokpok/Archive/pokpok_agents/ivan/eth_30min_30days.json')
        logger.info(f"Loaded {len(ohlcv_df)} data points")
        logger.info(f"Date range: {ohlcv_df.index[0]} to {ohlcv_df.index[-1]}")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return

    # Test different portfolio configurations
    configurations = [
        {
            "name": "Conservative (5% position, 50% max DD)",
            "config": PortfolioConfig(
                initial_capital_eth=10.0,
                position_size_pct=5.0,
                max_concurrent_positions=5,
                max_drawdown_pct=50.0
            )
        },
        {
            "name": "Moderate (10% position, 40% max DD)",
            "config": PortfolioConfig(
                initial_capital_eth=10.0,
                position_size_pct=10.0,
                max_concurrent_positions=3,
                max_drawdown_pct=40.0
            )
        },
        {
            "name": "Aggressive (15% position, 60% max DD)",
            "config": PortfolioConfig(
                initial_capital_eth=10.0,
                position_size_pct=15.0,
                max_concurrent_positions=3,
                max_drawdown_pct=60.0
            )
        }
    ]

    # Generate test strategy
    strategy = generate_test_strategy()

    for cfg in configurations:
        logger.info("\n" + "=" * 80)
        logger.info(f"Testing: {cfg['name']}")
        logger.info("=" * 80)

        # Execute strategy
        executor = PortfolioAwareDslExecutor(
            strategy['strategy_logic_dsl'],
            str(uuid.uuid4())
        )
        signals = executor.generate_signals(ohlcv_df)

        # Run backtest with portfolio management
        backtester = PortfolioBacktester(cfg['config'])
        results = backtester.run_backtest(signals, ohlcv_df)

        # Display results
        stats = results['statistics']

        print(f"\n📊 PERFORMANCE METRICS:")
        print(f"  Returns:")
        print(f"    - Total Return: {stats['total_return_eth']:.4f} ETH ({stats['total_return_pct']:.2f}%)")
        print(f"    - Final Capital: {stats['final_capital_eth']:.2f} ETH")
        print(f"    - Simple APR: {stats['simple_apr']:.2f}%")
        print(f"    - Capital-Efficient APR: {stats['capital_efficient_apr']:.2f}%")

        print(f"\n  Trading Performance:")
        print(f"    - Total Trades: {stats['total_trades']}")
        print(f"    - Win Rate: {stats['win_rate_pct']:.1f}%")
        print(f"    - Avg Win: {stats['avg_win_pct']:.2f}%")
        print(f"    - Avg Loss: {stats['avg_loss_pct']:.2f}%")
        print(f"    - Profit Factor: {stats['profit_factor']:.2f}")

        print(f"\n  Risk Metrics:")
        print(f"    - Max Drawdown: {stats['max_drawdown_pct']:.1f}%")
        print(f"    - Sharpe Ratio: {stats['sharpe_ratio']:.2f}")

        print(f"\n  Capital Efficiency:")
        print(f"    - Avg Positions: {stats['avg_positions_held']:.1f}")
        print(f"    - Max Positions: {stats['max_positions_held']}")
        print(f"    - Capital Utilization: {stats['capital_utilization_pct']:.1f}%")
        print(f"    - Avg Position Size: {stats['avg_position_size_eth']:.3f} ETH ({stats['avg_position_size_pct']:.1f}%)")

        print(f"\n  Costs:")
        print(f"    - Total Premium: {stats['total_premium_paid_eth']:.3f} ETH")
        print(f"    - Avg Premium: {stats['avg_premium_cost_pct']:.2f}%")

        # Print trade logs for first configuration only
        if cfg == configurations[0]:
            print_trade_logs(results['trade_logs'])

        # Save results
        output_file = f"portfolio_results_{cfg['name'].replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'pct').replace(',', '')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                'configuration': {
                    'name': cfg['name'],
                    'position_size_pct': cfg['config'].position_size_pct,
                    'max_concurrent_positions': cfg['config'].max_concurrent_positions,
                    'max_drawdown_pct': cfg['config'].max_drawdown_pct
                },
                'statistics': stats,
                'trade_logs': results['trade_logs'][:10]  # Save first 10 trades
            }, f, indent=2, default=str)

        logger.info(f"Results saved to {output_file}")


if __name__ == "__main__":
    main()