"""
Enhanced LAA-EVA System with Multiple Option Instruments
Includes intelligent selection of option types based on market conditions
"""

import json
import uuid
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union, Literal, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from itertools import product
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== OPTION INSTRUMENTS ====================
class OptionInstruments:
    """
    Define available option instruments with their costs and characteristics
    """
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
        """Get instrument details by type"""
        return cls.INSTRUMENTS.get(instrument_type, cls.INSTRUMENTS["3D_5PCT"])

    @classmethod
    def select_optimal_instrument(cls, expected_move_pct: float, volatility: float,
                                 time_horizon: int) -> str:
        """
        Intelligently select the best instrument based on market conditions

        Args:
            expected_move_pct: Expected price movement percentage
            volatility: Current market volatility (ATR or similar)
            time_horizon: Expected time to reach target (in days)

        Returns:
            Optimal instrument type
        """
        # High expected move -> Higher profit cap
        # Longer time horizon -> 7D options
        # Balance premium cost vs potential profit

        if time_horizon <= 3:
            if expected_move_pct > 7:
                return "3D_10PCT"  # Higher cap for larger moves
            else:
                return "3D_5PCT"   # Lower cost for smaller moves
        else:
            if expected_move_pct > 7:
                return "7D_10PCT"  # Same cost as 7D_5PCT but higher cap
            else:
                return "7D_5PCT"   # Longer duration for sustained moves


# ==================== ENHANCED DSL MODELS ====================
@dataclass
class EnhancedOptionsSignal:
    """Enhanced options trading signal with instrument selection"""
    strategy_id: uuid.UUID
    signal: int  # -7, -3, 0, 3, 7
    instrument_type: str  # "3D_5PCT", "3D_10PCT", "7D_5PCT", "7D_10PCT"
    profit_cap_pct: float
    premium_cost_pct: float
    duration_days: int
    last_close: float
    timestamp: datetime
    rule_triggered: str
    expected_move_pct: float  # For instrument selection
    volatility: float  # For instrument selection


class TechnicalIndicators:
    """Manual implementation of technical indicators"""

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return series.rolling(window=period).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """MACD indicator"""
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
    def bollinger_bands(series: pd.Series, period: int = 20, std: float = 2.0) -> pd.DataFrame:
        """Bollinger Bands"""
        sma = series.rolling(window=period).mean()
        std_dev = series.rolling(window=period).std()

        return pd.DataFrame({
            f'BBU_{period}_{std}': sma + (std_dev * std),
            f'BBM_{period}_{std}': sma,
            f'BBL_{period}_{std}': sma - (std_dev * std)
        })

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        high_low = high - low
        high_close = (high - close.shift()).abs()
        low_close = (low - close.shift()).abs()

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr

    @staticmethod
    def expected_move(close: pd.Series, atr: pd.Series, rsi: pd.Series,
                     macd_hist: pd.Series) -> pd.Series:
        """
        Calculate expected move percentage based on momentum and volatility
        """
        # Normalize indicators
        rsi_momentum = (rsi - 50) / 50  # -1 to 1
        macd_momentum = np.tanh(macd_hist / close * 100)  # Normalized MACD

        # Combine signals
        momentum_factor = (rsi_momentum + macd_momentum) / 2

        # Expected move = ATR-based volatility * momentum factor
        expected_move_pct = (atr / close) * 100 * (1 + momentum_factor)

        return expected_move_pct


# ==================== ENHANCED DSL EXECUTOR ====================
class EnhancedDslExecutor:
    """
    Enhanced DSL Executor with instrument selection capabilities
    """

    def __init__(self, strategy_definition_dsl: Dict[str, Any], strategy_id: str):
        self.dsl = strategy_definition_dsl
        self.strategy_id = strategy_id
        self.constants = self.dsl.get('constants', {})
        self.indicator_outputs = {}
        self.indicators = TechnicalIndicators()
        self.option_instruments = OptionInstruments()
        logger.info(f"EnhancedDslExecutor initialized for strategy {strategy_id}")

    def _resolve_value(self, value_or_ref: Any) -> Any:
        """Resolve constant references"""
        if isinstance(value_or_ref, str) and value_or_ref.startswith("@"):
            const_name = value_or_ref[1:]
            if const_name in self.constants:
                return self.constants[const_name]
            else:
                raise ValueError(f"Undefined constant: {value_or_ref}")
        return value_or_ref

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all indicators including expected move"""
        df_with_indicators = df.copy()

        # Calculate standard indicators
        for indicator in self.dsl.get('indicators', []):
            indicator_type = indicator['type'].lower()
            params = indicator['params']
            outputs = indicator['outputs']

            # Resolve parameters
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

                elif indicator_type == 'bbands':
                    length = resolved_params.get('length', 20)
                    std = resolved_params.get('std', 2.0)
                    bb_result = self.indicators.bollinger_bands(df['close'], length, std)

                    if outputs.get('component_output_map'):
                        for ta_col, user_col in outputs['component_output_map'].items():
                            if ta_col in bb_result.columns:
                                df_with_indicators[user_col] = bb_result[ta_col]
                                self.indicator_outputs[user_col] = bb_result[ta_col]

            except Exception as e:
                logger.warning(f"Error calculating {indicator_type}: {e}")
                primary_col = outputs['primary_output_column']
                df_with_indicators[primary_col] = np.nan

        # Calculate expected move if we have the necessary indicators
        if 'rsi_value' in df_with_indicators.columns and 'macd_hist' in df_with_indicators.columns and 'atr_value' in df_with_indicators.columns:
            df_with_indicators['expected_move_pct'] = self.indicators.expected_move(
                df['close'],
                df_with_indicators['atr_value'],
                df_with_indicators['rsi_value'],
                df_with_indicators['macd_hist']
            )
        else:
            # Fallback: simple ATR-based expected move
            if 'atr_value' in df_with_indicators.columns:
                df_with_indicators['expected_move_pct'] = (df_with_indicators['atr_value'] / df['close']) * 100
            else:
                df_with_indicators['expected_move_pct'] = 2.0  # Default 2% expected move

        return df_with_indicators

    def _evaluate_condition(self, condition: Dict[str, Any], row: pd.Series,
                           df: pd.DataFrame, idx: int) -> bool:
        """Evaluate a single condition"""
        series1 = condition['series1']
        operator = condition['operator'].lower()
        series2_or_value = condition['series2_or_value']

        # Get values
        val1 = self._get_value(series1, row)
        val2 = self._get_value(series2_or_value, row)

        if pd.isna(val1) or pd.isna(val2):
            return False

        # Basic comparison
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

        # Crossing operators
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
        """Get value from series or resolve constant"""
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
        """Evaluate condition group"""
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
        """
        Select optimal instrument based on rule and market conditions
        """
        # Get expected move and volatility
        expected_move = float(row.get('expected_move_pct', 2.0))
        volatility = float(row.get('atr_value', 50) / row.get('close', 1) * 100)

        # Check if rule has instrument selection hints
        rule_metadata = rule.get('instrument_selection', {})

        # Time horizon from rule or default
        time_horizon = rule_metadata.get('time_horizon_days', 3)

        # Volatility threshold for instrument selection - resolve if it's a reference
        vol_threshold_raw = rule_metadata.get('volatility_threshold', 3.0)
        if isinstance(vol_threshold_raw, str) and vol_threshold_raw.startswith('@'):
            # Resolve constant reference
            volatility_threshold = float(self._resolve_value(vol_threshold_raw))
        else:
            volatility_threshold = float(vol_threshold_raw)

        # Strong signals (|7|) get higher caps, weak signals (|3|) get lower caps
        signal_strength = abs(rule['action_on_true']['strength'])

        if signal_strength >= 7:
            # Strong signal - use higher profit cap
            if volatility > volatility_threshold:
                # High volatility - shorter duration
                instrument_type = "3D_10PCT" if expected_move > 7 else "3D_5PCT"
            else:
                # Low volatility - can use longer duration
                instrument_type = "7D_10PCT" if expected_move > 5 else "7D_5PCT"
        else:
            # Weak signal - conservative approach
            if volatility > volatility_threshold:
                # High volatility - stick to shorter, cheaper options
                instrument_type = "3D_5PCT"
            else:
                # Low volatility - still conservative
                instrument_type = "7D_5PCT" if expected_move < 5 else "3D_5PCT"

        # Override with DSL-specified instrument if provided
        if 'instrument_type' in rule['action_on_true']:
            instrument_type = rule['action_on_true']['instrument_type']

        return self.option_instruments.get_instrument(instrument_type)

    def generate_signals(self, df: pd.DataFrame) -> List[EnhancedOptionsSignal]:
        """Generate enhanced trading signals with instrument selection"""
        # Normalize columns
        df = df.copy()
        df.columns = [col.lower() for col in df.columns]

        # Calculate indicators
        df_with_indicators = self._calculate_indicators(df)

        signals = []
        default_action = self.dsl.get('default_action_on_no_match', {
            'signal_type': 'NEUTRAL',
            'strength': 0,
            'instrument_type': '3D_5PCT'
        })

        for idx in range(len(df_with_indicators)):
            row = df_with_indicators.iloc[idx]
            timestamp = pd.to_datetime(df_with_indicators.index[idx])
            last_close = row.get('close', np.nan)

            signal_generated = False

            # Check each signal rule
            for rule in self.dsl.get('signal_rules', []):
                conditions_group = rule['conditions_group']

                if self._evaluate_condition_group(conditions_group, row, df_with_indicators, idx):
                    action = rule['action_on_true']

                    # Select optimal instrument
                    instrument = self._select_instrument(rule, row)

                    signals.append(EnhancedOptionsSignal(
                        strategy_id=uuid.UUID(self.strategy_id),
                        signal=action['strength'],
                        instrument_type=list(self.option_instruments.INSTRUMENTS.keys())[
                            list(self.option_instruments.INSTRUMENTS.values()).index(instrument)
                        ],
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

            # Default action if no rule triggered
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


# ==================== ENHANCED LAA AGENT ====================
class EnhancedLAAAgent:
    """
    Enhanced LAA that generates strategies with instrument selection logic
    """

    def generate_strategy(self, market_regime: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate strategy with instrument selection rules"""
        params = params or {}

        # Extract parameters
        rsi_oversold = params.get('rsi_oversold', 30)
        rsi_overbought = params.get('rsi_overbought', 70)
        macd_fast = params.get('macd_fast', 12)
        macd_slow = params.get('macd_slow', 26)
        macd_signal = params.get('macd_signal', 9)
        sma_short = params.get('sma_short', 10)
        sma_long = params.get('sma_long', 30)
        atr_period = params.get('atr_period', 14)
        atr_threshold = params.get('atr_threshold', 50)

        # Volatility-based instrument selection thresholds
        high_vol_threshold = params.get('high_vol_threshold', 3.0)
        expected_move_threshold = params.get('expected_move_threshold', 5.0)

        dsl = {
            "dsl_version": "2.0",  # Version 2.0 with instrument selection
            "description": f"Enhanced {market_regime} strategy with dynamic instrument selection",
            "constants": {
                "rsi_oversold": rsi_oversold,
                "rsi_overbought": rsi_overbought,
                "macd_fast": macd_fast,
                "macd_slow": macd_slow,
                "macd_signal": macd_signal,
                "sma_short_period": sma_short,
                "sma_long_period": sma_long,
                "atr_period": atr_period,
                "atr_threshold": atr_threshold,
                "high_vol_threshold": high_vol_threshold,
                "expected_move_threshold": expected_move_threshold
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
                            f"MACD_{macd_fast}_{macd_slow}_{macd_signal}": "macd_line",
                            f"MACDs_{macd_fast}_{macd_slow}_{macd_signal}": "macd_signal",
                            f"MACDh_{macd_fast}_{macd_slow}_{macd_signal}": "macd_hist"
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
            "signal_rules": []
        }

        # Add regime-specific rules with instrument selection
        if market_regime == "BEAR_TREND_LOW_VOL":
            dsl["signal_rules"] = [
                {
                    "rule_name": "strong_bear_breakdown",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {"series1": "close", "operator": "crosses_below", "series2_or_value": "sma_short"},
                            {"series1": "sma_short", "operator": "<", "series2_or_value": "sma_long"},
                            {"series1": "macd_hist", "operator": "<", "series2_or_value": -0.5},
                            {"series1": "rsi_value", "operator": "<", "series2_or_value": 40}
                        ]
                    },
                    "action_on_true": {
                        "signal_type": "PUT",
                        "strength": -7,
                        # Instrument will be selected dynamically based on volatility
                        # But we can provide hints
                    },
                    "instrument_selection": {
                        "time_horizon_days": 7,  # Expect sustained move
                        "volatility_threshold": "@high_vol_threshold"
                    },
                    "description": "Strong bearish breakdown with optimal instrument"
                },
                {
                    "rule_name": "moderate_bear_signal",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {"series1": "macd_line", "operator": "crosses_below", "series2_or_value": "macd_signal"},
                            {"series1": "close", "operator": "<", "series2_or_value": "sma_long"},
                            {"series1": "atr_value", "operator": "<", "series2_or_value": "@atr_threshold"}
                        ]
                    },
                    "action_on_true": {
                        "signal_type": "PUT",
                        "strength": -3,
                    },
                    "instrument_selection": {
                        "time_horizon_days": 3,  # Shorter move expected
                        "volatility_threshold": "@high_vol_threshold"
                    },
                    "description": "Moderate bear signal with conservative instrument"
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
                        "strength": 3,
                    },
                    "instrument_selection": {
                        "time_horizon_days": 3,  # Quick bounce
                        "volatility_threshold": "@high_vol_threshold"
                    },
                    "description": "Oversold bounce with appropriate instrument"
                }
            ]

        elif market_regime == "BULL_TREND_HIGH_VOL":
            dsl["signal_rules"] = [
                {
                    "rule_name": "strong_bull_breakout",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {"series1": "close", "operator": "crosses_above", "series2_or_value": "sma_short"},
                            {"series1": "sma_short", "operator": ">", "series2_or_value": "sma_long"},
                            {"series1": "macd_hist", "operator": ">", "series2_or_value": 0.5},
                            {"series1": "rsi_value", "operator": ">", "series2_or_value": 60}
                        ]
                    },
                    "action_on_true": {
                        "signal_type": "CALL",
                        "strength": 7,
                    },
                    "instrument_selection": {
                        "time_horizon_days": 3,  # High vol = shorter duration
                        "volatility_threshold": "@high_vol_threshold"
                    },
                    "description": "Strong bull breakout in high volatility"
                },
                {
                    "rule_name": "pullback_entry",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {"series1": "rsi_value", "operator": "<", "series2_or_value": 45},
                            {"series1": "close", "operator": ">", "series2_or_value": "sma_long"},
                            {"series1": "macd_line", "operator": "crosses_above", "series2_or_value": "macd_signal"}
                        ]
                    },
                    "action_on_true": {
                        "signal_type": "CALL",
                        "strength": 3,
                    },
                    "instrument_selection": {
                        "time_horizon_days": 7,  # Trend continuation
                        "volatility_threshold": "@high_vol_threshold"
                    },
                    "description": "Pullback in uptrend"
                }
            ]

        dsl["default_action_on_no_match"] = {
            "signal_type": "NEUTRAL",
            "strength": 0,
            "instrument_type": "3D_5PCT"  # Most conservative default
        }

        return {
            "strategy_logic_dsl": dsl,
            "name": f"Enhanced_{market_regime}_InstrumentOptimized",
            "description": f"Strategy with dynamic instrument selection for {market_regime}",
            "regime_suitability": [market_regime]
        }


# ==================== ENHANCED EVA AGENT ====================
class EnhancedEVAAgent:
    """
    Enhanced EVA that evaluates strategies with multiple instrument types
    """

    def evaluate_strategy(self, strategy: Dict[str, Any], signals: List[EnhancedOptionsSignal],
                          ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
        """Evaluate strategy with instrument-specific costs"""
        backtest_results = self._run_backtest(signals, ohlcv_df)
        fitness_score = self._calculate_fitness(backtest_results)

        # Analyze instrument usage
        instrument_stats = self._analyze_instrument_usage(signals, backtest_results)

        return {
            'strategy_name': strategy['name'],
            'backtest_results': backtest_results,
            'fitness_score': fitness_score['score'],
            'fitness_reasoning': fitness_score['reasoning'],
            'instrument_stats': instrument_stats,
            'evaluation_timestamp': datetime.now().isoformat()
        }

    def _run_backtest(self, signals: List[EnhancedOptionsSignal], ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
        """Run backtest with instrument-specific costs and durations"""
        trades = []
        initial_capital = 10000
        capital = initial_capital
        active_positions = []  # Can have multiple positions with different durations

        # Create signal lookup
        signal_dict = {s.timestamp: s for s in signals}

        for idx in range(len(ohlcv_df)):
            timestamp = pd.to_datetime(ohlcv_df.index[idx])
            current_price = ohlcv_df.iloc[idx]['close']

            # Check for position expiries
            expired_positions = []
            for pos in active_positions:
                days_held = (timestamp - pos['entry_time']).days
                if days_held >= pos['duration_days']:
                    # Close position
                    exit_price = current_price

                    # Calculate P&L
                    price_change = (exit_price - pos['entry_price']) / pos['entry_price']

                    if pos['signal_strength'] > 0:  # CALL
                        raw_pnl = max(0, price_change)
                    else:  # PUT
                        raw_pnl = max(0, -price_change)

                    # Apply profit cap
                    capped_pnl = min(raw_pnl, pos['profit_cap'])

                    # Apply costs (premium already paid at entry)
                    net_pnl_pct = capped_pnl - pos['premium_cost']
                    pnl_amount = pos['size'] * net_pnl_pct
                    capital += pnl_amount

                    trades.append({
                        'entry_time': pos['entry_time'],
                        'exit_time': timestamp,
                        'signal_strength': pos['signal_strength'],
                        'instrument_type': pos['instrument_type'],
                        'entry_price': pos['entry_price'],
                        'exit_price': exit_price,
                        'pnl_pct': net_pnl_pct * 100,
                        'pnl_amount': pnl_amount,
                        'capital_after': capital,
                        'premium_cost_pct': pos['premium_cost'] * 100,
                        'profit_cap_pct': pos['profit_cap'] * 100,
                        'win': net_pnl_pct > 0
                    })
                    expired_positions.append(pos)

            # Remove expired positions
            for pos in expired_positions:
                active_positions.remove(pos)

            # Check for new signals
            if timestamp in signal_dict:
                signal = signal_dict[timestamp]

                if signal.signal != 0:
                    # Position sizing: 10% of capital per position
                    # Limit to max 3 concurrent positions
                    if len(active_positions) < 3:
                        position = {
                            'entry_time': timestamp,
                            'entry_price': current_price,
                            'signal_strength': signal.signal,
                            'instrument_type': signal.instrument_type,
                            'profit_cap': signal.profit_cap_pct / 100,
                            'premium_cost': signal.premium_cost_pct / 100,
                            'duration_days': signal.duration_days,
                            'size': capital * 0.1
                        }
                        active_positions.append(position)

        # Calculate statistics
        if trades:
            winning_trades = [t for t in trades if t['win']]
            losing_trades = [t for t in trades if not t['win']]

            total_return = (capital - initial_capital) / initial_capital
            win_rate = len(winning_trades) / len(trades) if trades else 0

            # Sharpe ratio
            returns = [t['pnl_pct'] / 100 for t in trades]
            avg_return = np.mean(returns)
            std_return = np.std(returns) if len(returns) > 1 else 0
            sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0

            # Max drawdown
            capital_curve = [initial_capital]
            for t in trades:
                capital_curve.append(t['capital_after'])

            peak = capital_curve[0]
            max_dd = 0
            for c in capital_curve:
                if c > peak:
                    peak = c
                dd = (peak - c) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)

            # APR
            days_traded = (trades[-1]['exit_time'] - trades[0]['entry_time']).days if len(trades) > 1 else 1
            apr = (total_return * 365 / days_traded) if days_traded > 0 else 0

            stats = {
                'total_trades': len(trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate_pct': win_rate * 100,
                'total_return_pct': total_return * 100,
                'apr': apr * 100,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown_pct': max_dd * 100,
                'final_capital': capital,
                'avg_win': np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0,
                'avg_loss': np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0,
                'avg_premium_cost': np.mean([t['premium_cost_pct'] for t in trades])
            }
        else:
            stats = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate_pct': 0,
                'total_return_pct': 0,
                'apr': 0,
                'sharpe_ratio': 0,
                'max_drawdown_pct': 0,
                'final_capital': initial_capital,
                'avg_win': 0,
                'avg_loss': 0,
                'avg_premium_cost': 0
            }

        return {
            'trades': trades,
            'statistics': stats
        }

    def _calculate_fitness(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate fitness score"""
        stats = backtest_results['statistics']

        apr = stats.get('apr', -100)
        win_rate_pct = stats.get('win_rate_pct', 0)
        sharpe_ratio = stats.get('sharpe_ratio', -10)
        max_drawdown_pct = stats.get('max_drawdown_pct', 100)

        # Adjusted thresholds for lower premium costs
        if apr < -5:  # More lenient than before
            return {
                'score': 0.15,
                'reasoning': f"APR ({apr:.1f}%) below minimum threshold"
            }

        if win_rate_pct < 35:  # Slightly more lenient
            return {
                'score': 0.25,
                'reasoning': f"Win rate ({win_rate_pct:.1f}%) below minimum threshold"
            }

        # Normalize components
        norm_apr = min(max((apr + 50) / 100, 0), 1)
        norm_win_rate = min(win_rate_pct / 100, 1)
        norm_sharpe = min(max((sharpe_ratio + 2) / 4, 0), 1)
        drawdown_score = max(1 - (max_drawdown_pct / 50), 0)

        # Weighted calculation
        fitness = (
            norm_apr * 0.4 +
            norm_win_rate * 0.3 +
            norm_sharpe * 0.2 +
            drawdown_score * 0.1
        )

        fitness = min(fitness, 1.0)

        reasoning = f"Fitness {fitness:.3f}: APR={apr:.1f}%, WR={win_rate_pct:.1f}%, SR={sharpe_ratio:.2f}, DD={max_drawdown_pct:.1f}%"

        return {
            'score': fitness,
            'reasoning': reasoning
        }

    def _analyze_instrument_usage(self, signals: List[EnhancedOptionsSignal],
                                  backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze which instruments were most effective"""
        instrument_performance = {}

        for trade in backtest_results.get('trades', []):
            inst_type = trade['instrument_type']
            if inst_type not in instrument_performance:
                instrument_performance[inst_type] = {
                    'count': 0,
                    'wins': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0
                }

            instrument_performance[inst_type]['count'] += 1
            if trade['win']:
                instrument_performance[inst_type]['wins'] += 1
            instrument_performance[inst_type]['total_pnl'] += trade['pnl_pct']

        # Calculate averages
        for inst_type in instrument_performance:
            stats = instrument_performance[inst_type]
            stats['win_rate'] = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            stats['avg_pnl'] = stats['total_pnl'] / stats['count'] if stats['count'] > 0 else 0

        return instrument_performance


# ==================== OPTIMIZER ====================
class EnhancedOptimizer:
    """
    Optimizer that tests different parameter combinations including instrument preferences
    """

    def __init__(self):
        self.laa = EnhancedLAAAgent()
        self.eva = EnhancedEVAAgent()
        self.optimization_history = []

    def optimize_strategy(self, market_regime: str, ohlcv_df: pd.DataFrame,
                          max_iterations: int = 50) -> Optional[Dict[str, Any]]:
        """Optimize strategy including instrument selection parameters"""
        logger.info(f"Starting enhanced optimization for {market_regime}")

        # Extended parameter space including instrument selection params
        param_space = {
            'rsi_oversold': [25, 30, 35],
            'rsi_overbought': [65, 70, 75],
            'macd_fast': [8, 12],
            'macd_slow': [21, 26],
            'macd_signal': [7, 9],
            'sma_short': [8, 10, 15],
            'sma_long': [20, 30, 40],
            'atr_period': [10, 14],
            'atr_threshold': [30, 50, 70],
            'high_vol_threshold': [2.5, 3.0, 3.5],  # New: volatility threshold for instrument selection
            'expected_move_threshold': [4.0, 5.0, 6.0]  # New: expected move threshold
        }

        # Generate combinations
        param_combinations = self._generate_param_combinations(param_space, max_iterations)

        best_result = None
        best_fitness = 0

        for i, params in enumerate(param_combinations):
            logger.info(f"Testing combination {i+1}/{len(param_combinations)}")

            # Generate strategy with instrument selection
            strategy = self.laa.generate_strategy(market_regime, params)

            # Execute strategy
            executor = EnhancedDslExecutor(
                strategy['strategy_logic_dsl'],
                str(uuid.uuid4())
            )
            signals = executor.generate_signals(ohlcv_df)

            # Evaluate
            evaluation = self.eva.evaluate_strategy(strategy, signals, ohlcv_df)

            # Track history
            self.optimization_history.append({
                'iteration': i + 1,
                'params': params,
                'fitness': evaluation['fitness_score'],
                'stats': evaluation['backtest_results']['statistics'],
                'instrument_stats': evaluation['instrument_stats']
            })

            # Check if best
            if evaluation['fitness_score'] > best_fitness:
                best_fitness = evaluation['fitness_score']
                best_result = {
                    'strategy': strategy,
                    'signals': signals,
                    'evaluation': evaluation,
                    'parameters': params
                }

                logger.info(f"New best fitness: {best_fitness:.3f}")

                # Log instrument usage
                logger.info("Instrument usage:")
                for inst_type, stats in evaluation['instrument_stats'].items():
                    logger.info(f"  {inst_type}: {stats['count']} trades, "
                              f"{stats['win_rate']:.1f}% win rate, "
                              f"{stats['avg_pnl']:.2f}% avg P&L")

                # Early termination
                if best_fitness >= 0.6:
                    logger.info(f"Target achieved! Fitness: {best_fitness:.3f}")
                    return best_result

        logger.info(f"Optimization complete. Best fitness: {best_fitness:.3f}")
        return best_result

    def _generate_param_combinations(self, param_space: Dict, max_combinations: int) -> List[Dict]:
        """Generate parameter combinations"""
        all_combinations = []
        keys = list(param_space.keys())
        values = [param_space[k] for k in keys]

        for combo in product(*values):
            param_dict = dict(zip(keys, combo))
            all_combinations.append(param_dict)

        if len(all_combinations) > max_combinations:
            random.shuffle(all_combinations)
            all_combinations = all_combinations[:max_combinations]

        return all_combinations


# ==================== MAIN ====================
def load_market_data(filepath: str) -> pd.DataFrame:
    """Load market data"""
    with open(filepath, 'r') as f:
        data = json.load(f)

    df = pd.DataFrame(data['ohlcv'])
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    df.columns = [col.lower() for col in df.columns]

    return df


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("ENHANCED LAA-EVA WITH DYNAMIC INSTRUMENT SELECTION")
    logger.info("=" * 80)

    # Load data
    try:
        ohlcv_df = load_market_data('/Users/ivanhmac/github/pokpok/Archive/pokpok_agents/ivan/eth_30min_30days.json')
        logger.info(f"Loaded {len(ohlcv_df)} data points")

        # Display instrument options
        logger.info("\nAvailable Option Instruments:")
        for inst_type, details in OptionInstruments.INSTRUMENTS.items():
            logger.info(f"  {inst_type}: {details['duration_days']}D duration, "
                       f"{details['profit_cap_pct']}% cap, {details['premium_cost_pct']}% cost")

    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return

    # Initialize optimizer
    optimizer = EnhancedOptimizer()

    # Run optimization
    logger.info("\n" + "=" * 60)
    logger.info("STARTING ENHANCED OPTIMIZATION")
    logger.info("=" * 60)

    result = optimizer.optimize_strategy(
        market_regime='BEAR_TREND_LOW_VOL',
        ohlcv_df=ohlcv_df,
        max_iterations=30
    )

    # Display results
    if result:
        logger.info("\n" + "=" * 60)
        logger.info("🎯 OPTIMIZATION COMPLETE!")
        logger.info("=" * 60)

        eval_data = result['evaluation']
        stats = eval_data['backtest_results']['statistics']

        logger.info(f"\nStrategy: {result['strategy']['name']}")
        logger.info(f"Fitness Score: {eval_data['fitness_score']:.3f}")
        logger.info(f"Fitness Reasoning: {eval_data['fitness_reasoning']}")

        logger.info(f"\n📊 PERFORMANCE METRICS:")
        logger.info(f"  - Win Rate: {stats['win_rate_pct']:.1f}%")
        logger.info(f"  - Total Return: {stats['total_return_pct']:.1f}%")
        logger.info(f"  - APR: {stats['apr']:.1f}%")
        logger.info(f"  - Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
        logger.info(f"  - Max Drawdown: {stats['max_drawdown_pct']:.1f}%")
        logger.info(f"  - Avg Premium Cost: {stats['avg_premium_cost']:.2f}%")

        logger.info(f"\n📈 INSTRUMENT USAGE:")
        for inst_type, inst_stats in eval_data['instrument_stats'].items():
            logger.info(f"  {inst_type}:")
            logger.info(f"    - Trades: {inst_stats['count']}")
            logger.info(f"    - Win Rate: {inst_stats['win_rate']:.1f}%")
            logger.info(f"    - Avg P&L: {inst_stats['avg_pnl']:.2f}%")

        logger.info(f"\n🔧 OPTIMAL PARAMETERS:")
        for key, value in result['parameters'].items():
            logger.info(f"  - {key}: {value}")

        # Save results
        output_file = 'enhanced_strategy_results.json'
        with open(output_file, 'w') as f:
            save_data = {
                'strategy_name': result['strategy']['name'],
                'fitness_score': eval_data['fitness_score'],
                'parameters': result['parameters'],
                'statistics': stats,
                'instrument_stats': eval_data['instrument_stats'],
                'dsl': result['strategy']['strategy_logic_dsl']
            }
            json.dump(save_data, f, indent=2, default=str)

        logger.info(f"\n✅ Results saved to {output_file}")


if __name__ == "__main__":
    main()