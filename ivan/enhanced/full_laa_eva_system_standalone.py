"""
Complete LAA-EVA Replication System with Full DSL Capabilities
Standalone version with manual indicator implementations
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== DSL MODELS ====================
@dataclass
class OptionsSignal:
    """Options trading signal"""
    strategy_id: uuid.UUID
    signal: int  # -7, -3, 0, 3, 7
    profit_cap_pct: float
    last_close: float
    timestamp: datetime
    rule_triggered: str


class StrategyDefinition:
    """Full strategy definition with DSL"""
    def __init__(self, strategy_logic_dsl: Dict[str, Any], **kwargs):
        self.id = str(uuid.uuid4())
        self.name = kwargs.get('name', 'Generated_Strategy')
        self.description = kwargs.get('description', '')
        self.version = kwargs.get('version', 1)
        self.asset_compatibility = kwargs.get('asset_compatibility', ['ETH'])
        self.regime_suitability = kwargs.get('regime_suitability', ['BEAR_TREND_LOW_VOL'])
        self.timeframe_suitability = kwargs.get('timeframe_suitability', ['30m'])
        self.tags = kwargs.get('tags', [])
        self.strategy_logic_dsl = strategy_logic_dsl


# ==================== TECHNICAL INDICATORS ====================
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
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                   k_period: int = 14, d_period: int = 3) -> pd.DataFrame:
        """Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d = k.rolling(window=d_period).mean()

        return pd.DataFrame({
            f'STOCHk_{k_period}_{d_period}': k,
            f'STOCHd_{k_period}_{d_period}': d
        })

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On-Balance Volume"""
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        return obv


# ==================== ADVANCED DSL EXECUTOR ====================
class AdvancedDslExecutor:
    """
    Full DSL Executor with ALL advanced capabilities
    """

    SUPPORTED_OPERATORS = [
        ">", "<", ">=", "<=", "==", "!=",
        "crosses_above", "crosses_below",
        "is_rising", "is_falling",
        "is_between", "is_not_between"
    ]

    def __init__(self, strategy_definition_dsl: Dict[str, Any], strategy_id: str):
        self.dsl = strategy_definition_dsl
        self.strategy_id = strategy_id
        self.constants = self.dsl.get('constants', {})
        self.indicator_outputs = {}
        self.indicators = TechnicalIndicators()
        logger.info(f"AdvancedDslExecutor initialized for strategy {strategy_id}")

    def _resolve_value(self, value_or_ref: Any) -> Any:
        """Resolve constant references like @rsi_oversold"""
        if isinstance(value_or_ref, str) and value_or_ref.startswith("@"):
            const_name = value_or_ref[1:]
            if const_name in self.constants:
                return self.constants[const_name]
            else:
                raise ValueError(f"Undefined constant: {value_or_ref}")
        return value_or_ref

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all indicators with multi-component support"""
        df_with_indicators = df.copy()

        for indicator in self.dsl.get('indicators', []):
            indicator_type = indicator['type'].lower()
            params = indicator['params']
            outputs = indicator['outputs']

            # Resolve constant references in parameters
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

                    # Handle multi-component output
                    if outputs.get('component_output_map'):
                        for ta_col, user_col in outputs['component_output_map'].items():
                            if ta_col in macd_result.columns:
                                df_with_indicators[user_col] = macd_result[ta_col]
                                self.indicator_outputs[user_col] = macd_result[ta_col]
                    else:
                        primary_col = outputs['primary_output_column']
                        if not macd_result.empty:
                            df_with_indicators[primary_col] = macd_result.iloc[:, 0]
                            self.indicator_outputs[primary_col] = macd_result.iloc[:, 0]

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

                elif indicator_type == 'bbands':
                    length = resolved_params.get('length', 20)
                    std = resolved_params.get('std', 2.0)
                    bb_result = self.indicators.bollinger_bands(df['close'], length, std)

                    if outputs.get('component_output_map'):
                        for ta_col, user_col in outputs['component_output_map'].items():
                            if ta_col in bb_result.columns:
                                df_with_indicators[user_col] = bb_result[ta_col]
                                self.indicator_outputs[user_col] = bb_result[ta_col]
                    else:
                        primary_col = outputs['primary_output_column']
                        if not bb_result.empty:
                            df_with_indicators[primary_col] = bb_result.iloc[:, 1]  # Middle band
                            self.indicator_outputs[primary_col] = bb_result.iloc[:, 1]

                elif indicator_type == 'atr':
                    length = resolved_params.get('length', 14)
                    atr_result = self.indicators.atr(df['high'], df['low'], df['close'], length)
                    primary_col = outputs['primary_output_column']
                    df_with_indicators[primary_col] = atr_result
                    self.indicator_outputs[primary_col] = atr_result

                elif indicator_type == 'stoch':
                    k = resolved_params.get('k', 14)
                    d = resolved_params.get('d', 3)
                    stoch_result = self.indicators.stochastic(df['high'], df['low'], df['close'], k, d)

                    if outputs.get('component_output_map'):
                        for ta_col, user_col in outputs['component_output_map'].items():
                            if ta_col in stoch_result.columns:
                                df_with_indicators[user_col] = stoch_result[ta_col]
                                self.indicator_outputs[user_col] = stoch_result[ta_col]
                    else:
                        primary_col = outputs['primary_output_column']
                        if not stoch_result.empty:
                            df_with_indicators[primary_col] = stoch_result.iloc[:, 0]  # %K
                            self.indicator_outputs[primary_col] = stoch_result.iloc[:, 0]

                elif indicator_type == 'obv':
                    obv_result = self.indicators.obv(df['close'], df['volume'])
                    primary_col = outputs['primary_output_column']
                    df_with_indicators[primary_col] = obv_result
                    self.indicator_outputs[primary_col] = obv_result

            except Exception as e:
                logger.warning(f"Error calculating {indicator_type}: {e}")
                primary_col = outputs['primary_output_column']
                df_with_indicators[primary_col] = np.nan

        return df_with_indicators

    def _evaluate_condition(self, condition: Dict[str, Any], row: pd.Series,
                           df: pd.DataFrame, idx: int) -> bool:
        """Evaluate a single condition with advanced operators"""
        series1 = condition['series1']
        operator = condition['operator'].lower()
        series2_or_value = condition['series2_or_value']

        # Get values
        val1 = self._get_value(series1, row)
        val2 = self._get_value(series2_or_value, row)

        if pd.isna(val1) or pd.isna(val2):
            return False

        # Basic comparison operators
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

        # Advanced crossing operators
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

        # Trend operators
        elif operator in ['is_rising', 'is_falling']:
            if idx < 1:
                return False
            prev_row = df.iloc[idx - 1]
            prev_val1 = self._get_value(series1, prev_row)

            if pd.isna(prev_val1):
                return False

            if operator == 'is_rising':
                return val1 > prev_val1
            elif operator == 'is_falling':
                return val1 < prev_val1

        # Range operators
        elif operator == 'is_between':
            lower = condition.get('lower_bound', val2 - 10)
            upper = condition.get('upper_bound', val2 + 10)
            return lower <= val1 <= upper
        elif operator == 'is_not_between':
            lower = condition.get('lower_bound', val2 - 10)
            upper = condition.get('upper_bound', val2 + 10)
            return not (lower <= val1 <= upper)

        return False

    def _get_value(self, series_or_value: Any, row: pd.Series) -> Any:
        """Get value from series or resolve constant reference"""
        if isinstance(series_or_value, str):
            if series_or_value.startswith('@'):
                return self._resolve_value(series_or_value)
            elif series_or_value in row.index:
                return row[series_or_value]
            else:
                logger.warning(f"Unknown series: {series_or_value}")
                return np.nan
        else:
            return series_or_value

    def _evaluate_condition_group(self, group: Dict[str, Any], row: pd.Series,
                                 df: pd.DataFrame, idx: int) -> bool:
        """Evaluate a group of conditions with AND/OR logic"""
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

    def generate_signals(self, df: pd.DataFrame) -> List[OptionsSignal]:
        """Generate trading signals from OHLCV data"""
        # Normalize column names
        df = df.copy()
        df.columns = [col.lower() for col in df.columns]

        # Calculate indicators
        df_with_indicators = self._calculate_indicators(df)

        signals = []
        default_action = self.dsl.get('default_action_on_no_match', {
            'signal_type': 'NEUTRAL',
            'strength': 0,
            'profit_cap_pct': 5
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
                    signals.append(OptionsSignal(
                        strategy_id=uuid.UUID(self.strategy_id),
                        signal=action['strength'],
                        profit_cap_pct=action['profit_cap_pct'],
                        last_close=last_close,
                        timestamp=timestamp,
                        rule_triggered=rule['rule_name']
                    ))
                    signal_generated = True
                    break

            # Apply default action if no rule triggered
            if not signal_generated:
                signals.append(OptionsSignal(
                    strategy_id=uuid.UUID(self.strategy_id),
                    signal=default_action['strength'],
                    profit_cap_pct=default_action['profit_cap_pct'],
                    last_close=last_close,
                    timestamp=timestamp,
                    rule_triggered='DEFAULT'
                ))

        return signals


# ==================== LAA AGENT SIMULATOR ====================
class LAAAgentSimulator:
    """
    Learning & Adaptation Agent simulator
    """

    def __init__(self):
        self.regime_strategies = {
            'BEAR_TREND_LOW_VOL': self._generate_bear_low_vol_strategy,
            'BULL_TREND_HIGH_VOL': self._generate_bull_high_vol_strategy,
            'SIDEWAYS': self._generate_sideways_strategy
        }

    def generate_strategy(self, market_regime: str, params: Optional[Dict] = None) -> StrategyDefinition:
        """Generate a strategy optimized for the given market regime"""
        if market_regime in self.regime_strategies:
            return self.regime_strategies[market_regime](params or {})
        else:
            return self._generate_default_strategy(params or {})

    def _generate_bear_low_vol_strategy(self, params: Dict) -> StrategyDefinition:
        """Generate strategy for bear market with low volatility"""
        # Extract parameters with defaults
        rsi_oversold = params.get('rsi_oversold', 30)
        rsi_overbought = params.get('rsi_overbought', 70)
        macd_fast = params.get('macd_fast', 12)
        macd_slow = params.get('macd_slow', 26)
        macd_signal = params.get('macd_signal', 9)
        sma_short = params.get('sma_short', 10)
        sma_long = params.get('sma_long', 30)
        atr_period = params.get('atr_period', 14)
        atr_threshold = params.get('atr_threshold', 50)

        dsl = {
            "dsl_version": "1.0",
            "description": "Bear market low volatility strategy with crossover detection",
            "constants": {
                "rsi_oversold": rsi_oversold,
                "rsi_overbought": rsi_overbought,
                "macd_fast": macd_fast,
                "macd_slow": macd_slow,
                "macd_signal": macd_signal,
                "sma_short_period": sma_short,
                "sma_long_period": sma_long,
                "atr_period": atr_period,
                "atr_threshold": atr_threshold
            },
            "indicators": [
                {
                    "name": "rsi_main",
                    "type": "rsi",
                    "params": {
                        "length": 14,
                        "column": "close"
                    },
                    "outputs": {
                        "primary_output_column": "rsi_value"
                    }
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
                    "params": {
                        "length": "@sma_short_period",
                        "column": "close"
                    },
                    "outputs": {
                        "primary_output_column": "sma_short"
                    }
                },
                {
                    "name": "sma_long",
                    "type": "sma",
                    "params": {
                        "length": "@sma_long_period",
                        "column": "close"
                    },
                    "outputs": {
                        "primary_output_column": "sma_long"
                    }
                },
                {
                    "name": "atr",
                    "type": "atr",
                    "params": {
                        "length": "@atr_period"
                    },
                    "outputs": {
                        "primary_output_column": "atr_value"
                    }
                }
            ],
            "signal_rules": [
                {
                    "rule_name": "bear_breakdown_signal",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {
                                "series1": "close",
                                "operator": "crosses_below",
                                "series2_or_value": "sma_short",
                                "description": "Price crosses below short SMA"
                            },
                            {
                                "series1": "sma_short",
                                "operator": "<",
                                "series2_or_value": "sma_long",
                                "description": "Short SMA below long SMA"
                            },
                            {
                                "series1": "macd_hist",
                                "operator": "<",
                                "series2_or_value": 0,
                                "description": "MACD histogram negative"
                            },
                            {
                                "series1": "atr_value",
                                "operator": "<",
                                "series2_or_value": "@atr_threshold",
                                "description": "Low volatility"
                            }
                        ]
                    },
                    "action_on_true": {
                        "signal_type": "PUT",
                        "strength": -3,
                        "profit_cap_pct": 5,
                        "description": "Conservative PUT"
                    },
                    "time_filter": None,
                    "description": "Bear market breakdown"
                },
                {
                    "rule_name": "oversold_bounce",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {
                                "series1": "rsi_value",
                                "operator": "<",
                                "series2_or_value": "@rsi_oversold",
                                "description": "RSI oversold"
                            },
                            {
                                "series1": "macd_line",
                                "operator": "crosses_above",
                                "series2_or_value": "macd_signal",
                                "description": "MACD bullish crossover"
                            }
                        ]
                    },
                    "action_on_true": {
                        "signal_type": "CALL",
                        "strength": 3,
                        "profit_cap_pct": 5,
                        "description": "Counter-trend bounce"
                    },
                    "time_filter": None,
                    "description": "Oversold bounce"
                },
                {
                    "rule_name": "strong_bear_continuation",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {
                                "series1": "rsi_value",
                                "operator": ">",
                                "series2_or_value": "@rsi_overbought",
                                "description": "RSI overbought"
                            },
                            {
                                "series1": "macd_line",
                                "operator": "crosses_below",
                                "series2_or_value": "macd_signal",
                                "description": "MACD bearish crossover"
                            },
                            {
                                "series1": "close",
                                "operator": "<",
                                "series2_or_value": "sma_long",
                                "description": "Price below long SMA"
                            }
                        ]
                    },
                    "action_on_true": {
                        "signal_type": "PUT",
                        "strength": -7,
                        "profit_cap_pct": 10,
                        "description": "Strong PUT"
                    },
                    "time_filter": None,
                    "description": "Strong bearish continuation"
                }
            ],
            "default_action_on_no_match": {
                "signal_type": "NEUTRAL",
                "strength": 0,
                "profit_cap_pct": 5,
                "description": "No clear signal"
            }
        }

        return StrategyDefinition(
            strategy_logic_dsl=dsl,
            name="Bear_LowVol_Advanced_Strategy",
            description="Advanced bear market strategy with crossing detection",
            regime_suitability=["BEAR_TREND_LOW_VOL"],
            tags=["bear", "low_volatility", "crossover", "macd", "rsi", "sma"]
        )

    def _generate_bull_high_vol_strategy(self, params: Dict) -> StrategyDefinition:
        """Generate strategy for bull market with high volatility"""
        rsi_oversold = params.get('rsi_oversold', 35)
        rsi_overbought = params.get('rsi_overbought', 65)

        dsl = {
            "dsl_version": "1.0",
            "description": "Bull market high volatility momentum strategy",
            "constants": {
                "rsi_oversold": rsi_oversold,
                "rsi_overbought": rsi_overbought
            },
            "indicators": [
                {
                    "name": "rsi_momentum",
                    "type": "rsi",
                    "params": {"length": 14, "column": "close"},
                    "outputs": {"primary_output_column": "rsi_value"}
                },
                {
                    "name": "ema_fast",
                    "type": "ema",
                    "params": {"length": 8, "column": "close"},
                    "outputs": {"primary_output_column": "ema_fast"}
                },
                {
                    "name": "ema_slow",
                    "type": "ema",
                    "params": {"length": 21, "column": "close"},
                    "outputs": {"primary_output_column": "ema_slow"}
                }
            ],
            "signal_rules": [
                {
                    "rule_name": "bull_momentum_entry",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {
                                "series1": "ema_fast",
                                "operator": "crosses_above",
                                "series2_or_value": "ema_slow",
                                "description": "Fast EMA crosses above slow"
                            },
                            {
                                "series1": "rsi_value",
                                "operator": ">",
                                "series2_or_value": 50,
                                "description": "RSI above neutral"
                            }
                        ]
                    },
                    "action_on_true": {
                        "signal_type": "CALL",
                        "strength": 7,
                        "profit_cap_pct": 10,
                        "description": "Strong bull momentum"
                    },
                    "time_filter": None,
                    "description": "Bull momentum entry"
                }
            ],
            "default_action_on_no_match": {
                "signal_type": "NEUTRAL",
                "strength": 0,
                "profit_cap_pct": 5
            }
        }

        return StrategyDefinition(
            strategy_logic_dsl=dsl,
            name="Bull_HighVol_Momentum_Strategy",
            description="Bull market high volatility momentum strategy",
            regime_suitability=["BULL_TREND_HIGH_VOL"],
            tags=["bull", "high_volatility", "momentum"]
        )

    def _generate_sideways_strategy(self, params: Dict) -> StrategyDefinition:
        """Generate strategy for sideways market"""
        bb_period = params.get('bb_period', 20)
        bb_std = params.get('bb_std', 2.0)

        dsl = {
            "dsl_version": "1.0",
            "description": "Sideways market mean reversion",
            "constants": {
                "bb_period": bb_period,
                "bb_std": bb_std,
                "rsi_oversold": params.get('rsi_oversold', 30),
                "rsi_overbought": params.get('rsi_overbought', 70)
            },
            "indicators": [
                {
                    "name": "bollinger",
                    "type": "bbands",
                    "params": {
                        "length": "@bb_period",
                        "std": "@bb_std",
                        "column": "close"
                    },
                    "outputs": {
                        "primary_output_column": "bb_middle",
                        "component_output_map": {
                            f"BBL_{bb_period}_{bb_std}": "bb_lower",
                            f"BBM_{bb_period}_{bb_std}": "bb_middle",
                            f"BBU_{bb_period}_{bb_std}": "bb_upper"
                        }
                    }
                },
                {
                    "name": "rsi",
                    "type": "rsi",
                    "params": {"length": 14, "column": "close"},
                    "outputs": {"primary_output_column": "rsi_value"}
                }
            ],
            "signal_rules": [
                {
                    "rule_name": "lower_band_bounce",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {
                                "series1": "close",
                                "operator": "crosses_above",
                                "series2_or_value": "bb_lower",
                                "description": "Price crosses above lower band"
                            },
                            {
                                "series1": "rsi_value",
                                "operator": "<",
                                "series2_or_value": "@rsi_oversold",
                                "description": "RSI oversold"
                            }
                        ]
                    },
                    "action_on_true": {
                        "signal_type": "CALL",
                        "strength": 3,
                        "profit_cap_pct": 5,
                        "description": "Mean reversion long"
                    },
                    "time_filter": None,
                    "description": "Lower band bounce"
                },
                {
                    "rule_name": "upper_band_reversal",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {
                                "series1": "close",
                                "operator": "crosses_below",
                                "series2_or_value": "bb_upper",
                                "description": "Price crosses below upper band"
                            },
                            {
                                "series1": "rsi_value",
                                "operator": ">",
                                "series2_or_value": "@rsi_overbought",
                                "description": "RSI overbought"
                            }
                        ]
                    },
                    "action_on_true": {
                        "signal_type": "PUT",
                        "strength": -3,
                        "profit_cap_pct": 5,
                        "description": "Mean reversion short"
                    },
                    "time_filter": None,
                    "description": "Upper band reversal"
                }
            ],
            "default_action_on_no_match": {
                "signal_type": "NEUTRAL",
                "strength": 0,
                "profit_cap_pct": 5
            }
        }

        return StrategyDefinition(
            strategy_logic_dsl=dsl,
            name="Sideways_MeanReversion_Strategy",
            description="Sideways market mean reversion",
            regime_suitability=["SIDEWAYS"],
            tags=["sideways", "mean_reversion", "bollinger_bands"]
        )

    def _generate_default_strategy(self, params: Dict) -> StrategyDefinition:
        """Generate default strategy"""
        return self._generate_bear_low_vol_strategy(params)


# ==================== EVA AGENT SIMULATOR ====================
class EVAAgentSimulator:
    """
    Evaluation Agent simulator with comprehensive backtesting
    """

    def __init__(self):
        self.premium_cost = 0.035  # 3.5% premium cost
        self.transaction_cost = 0.001  # 0.1% transaction cost
        self.slippage = 0.0005  # 0.05% slippage

    def evaluate_strategy(self, strategy: StrategyDefinition, signals: List[OptionsSignal],
                          ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
        """Evaluate strategy performance"""
        backtest_results = self._run_backtest(signals, ohlcv_df)
        fitness_score = self._calculate_fitness(backtest_results)

        return {
            'strategy_id': strategy.id,
            'strategy_name': strategy.name,
            'backtest_results': backtest_results,
            'fitness_score': fitness_score['score'],
            'fitness_reasoning': fitness_score['reasoning'],
            'evaluation_timestamp': datetime.now().isoformat()
        }

    def _run_backtest(self, signals: List[OptionsSignal], ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
        """Run comprehensive backtest"""
        trades = []
        initial_capital = 10000
        capital = initial_capital
        position = None

        # Create signal lookup
        signal_dict = {s.timestamp: s for s in signals}

        for idx in range(len(ohlcv_df)):
            timestamp = pd.to_datetime(ohlcv_df.index[idx])
            current_price = ohlcv_df.iloc[idx]['close']

            # Check for position expiry (3-day holding)
            if position and (timestamp - position['entry_time']).days >= 3:
                # Close position
                exit_price = current_price
                pnl_pct = self._calculate_option_pnl(
                    position['signal_strength'],
                    position['entry_price'],
                    exit_price,
                    position['profit_cap']
                )

                # Apply premium cost
                net_pnl_pct = pnl_pct - self.premium_cost - self.transaction_cost
                pnl_amount = position['size'] * net_pnl_pct
                capital += pnl_amount

                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': timestamp,
                    'signal_strength': position['signal_strength'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'pnl_pct': net_pnl_pct,
                    'pnl_amount': pnl_amount,
                    'capital_after': capital,
                    'win': net_pnl_pct > 0
                })
                position = None

            # Check for new signal
            if timestamp in signal_dict:
                signal = signal_dict[timestamp]

                if signal.signal != 0 and position is None:
                    # Open new position
                    position = {
                        'entry_time': timestamp,
                        'entry_price': current_price,
                        'signal_strength': signal.signal,
                        'profit_cap': signal.profit_cap_pct / 100,
                        'size': capital * 0.1  # 10% position sizing
                    }

        # Calculate statistics
        if trades:
            winning_trades = [t for t in trades if t['win']]
            losing_trades = [t for t in trades if not t['win']]

            total_return = (capital - initial_capital) / initial_capital
            win_rate = len(winning_trades) / len(trades) if trades else 0

            # Calculate Sharpe ratio
            returns = [t['pnl_pct'] for t in trades]
            sharpe_ratio = self._calculate_sharpe_ratio(returns) if returns else 0

            # Calculate max drawdown
            capital_curve = [initial_capital]
            for t in trades:
                capital_curve.append(t['capital_after'])
            max_drawdown = self._calculate_max_drawdown(capital_curve)

            # APR calculation
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
                'max_drawdown_pct': max_drawdown * 100,
                'final_capital': capital,
                'avg_win': np.mean([t['pnl_pct'] for t in winning_trades]) * 100 if winning_trades else 0,
                'avg_loss': np.mean([t['pnl_pct'] for t in losing_trades]) * 100 if losing_trades else 0
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
                'avg_loss': 0
            }

        return {
            'trades': trades,
            'statistics': stats
        }

    def _calculate_option_pnl(self, signal_strength: int, entry_price: float,
                             exit_price: float, profit_cap: float) -> float:
        """Calculate P&L for options position"""
        price_change = (exit_price - entry_price) / entry_price

        if signal_strength > 0:  # CALL option
            raw_pnl = max(0, price_change)
        else:  # PUT option
            raw_pnl = max(0, -price_change)

        # Apply profit cap
        capped_pnl = min(raw_pnl, profit_cap)

        return capped_pnl

    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio"""
        if not returns or len(returns) < 2:
            return 0

        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0

        # Annualized Sharpe
        return (avg_return / std_return) * np.sqrt(48 * 252) if std_return > 0 else 0

    def _calculate_max_drawdown(self, capital_curve: List[float]) -> float:
        """Calculate maximum drawdown"""
        if not capital_curve:
            return 0

        peak = capital_curve[0]
        max_dd = 0

        for capital in capital_curve:
            if capital > peak:
                peak = capital
            drawdown = (peak - capital) / peak if peak > 0 else 0
            max_dd = max(max_dd, drawdown)

        return max_dd

    def _calculate_fitness(self, backtest_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate fitness score using PokPok's framework
        """
        stats = backtest_results['statistics']

        apr = stats.get('apr', -100)
        win_rate_pct = stats.get('win_rate_pct', 0)
        sharpe_ratio = stats.get('sharpe_ratio', -10)
        max_drawdown_pct = stats.get('max_drawdown_pct', 100)

        # Zero tolerance policies
        if apr < 0:
            return {
                'score': 0.15,
                'reasoning': f"Negative APR ({apr:.1f}%) triggers zero tolerance"
            }

        if win_rate_pct < 40:
            return {
                'score': 0.25,
                'reasoning': f"Win rate ({win_rate_pct:.1f}%) below 40% threshold"
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

        # Cap at 1.0
        fitness = min(fitness, 1.0)

        # Generate reasoning
        reasoning = f"Fitness {fitness:.3f}: APR={apr:.1f}% (n={norm_apr:.2f}), "
        reasoning += f"WR={win_rate_pct:.1f}% (n={norm_win_rate:.2f}), "
        reasoning += f"SR={sharpe_ratio:.2f} (n={norm_sharpe:.2f}), "
        reasoning += f"DD={max_drawdown_pct:.1f}% (s={drawdown_score:.2f})"

        return {
            'score': fitness,
            'reasoning': reasoning
        }


# ==================== PARAMETER OPTIMIZER ====================
class ParameterOptimizer:
    """
    Systematic parameter optimization
    """

    def __init__(self, laa_agent: LAAAgentSimulator, eva_agent: EVAAgentSimulator):
        self.laa = laa_agent
        self.eva = eva_agent
        self.optimization_history = []

    def optimize_strategy(self, market_regime: str, ohlcv_df: pd.DataFrame,
                          max_iterations: int = 50) -> Optional[Dict[str, Any]]:
        """
        Optimize strategy parameters
        """
        logger.info(f"Starting optimization for {market_regime}")

        # Define parameter search space
        param_space = {
            'rsi_oversold': [25, 30, 35],
            'rsi_overbought': [65, 70, 75],
            'macd_fast': [8, 12],
            'macd_slow': [21, 26],
            'macd_signal': [7, 9],
            'sma_short': [8, 10, 15],
            'sma_long': [20, 30, 40],
            'atr_period': [10, 14],
            'atr_threshold': [30, 50, 70]
        }

        # Generate parameter combinations
        param_combinations = self._generate_param_combinations(param_space, max_iterations)

        best_result = None
        best_fitness = 0

        for i, params in enumerate(param_combinations):
            logger.info(f"Testing combination {i+1}/{len(param_combinations)}")

            # Generate strategy
            strategy = self.laa.generate_strategy(market_regime, params)

            # Execute strategy
            executor = AdvancedDslExecutor(
                strategy.strategy_logic_dsl,
                strategy.id
            )
            signals = executor.generate_signals(ohlcv_df)

            # Evaluate performance
            evaluation = self.eva.evaluate_strategy(strategy, signals, ohlcv_df)

            # Track history
            self.optimization_history.append({
                'iteration': i + 1,
                'params': params,
                'fitness': evaluation['fitness_score'],
                'win_rate': evaluation['backtest_results']['statistics']['win_rate_pct'],
                'total_return': evaluation['backtest_results']['statistics']['total_return_pct']
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

                # Early termination
                if best_fitness >= 0.6:
                    logger.info(f"Target achieved! Fitness: {best_fitness:.3f}")
                    return best_result

        logger.info(f"Optimization complete. Best fitness: {best_fitness:.3f}")
        return best_result

    def _generate_param_combinations(self, param_space: Dict, max_combinations: int) -> List[Dict]:
        """Generate parameter combinations"""
        import random

        all_combinations = []
        keys = list(param_space.keys())
        values = [param_space[k] for k in keys]

        # Generate all combinations
        for combo in product(*values):
            param_dict = dict(zip(keys, combo))
            all_combinations.append(param_dict)

        # Limit to max
        if len(all_combinations) > max_combinations:
            random.shuffle(all_combinations)
            all_combinations = all_combinations[:max_combinations]

        return all_combinations


# ==================== MAIN EXECUTION ====================
def load_market_data(filepath: str) -> pd.DataFrame:
    """Load market data"""
    with open(filepath, 'r') as f:
        data = json.load(f)

    df = pd.DataFrame(data['ohlcv'])
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)

    # Ensure lowercase columns
    df.columns = [col.lower() for col in df.columns]

    return df


def main():
    """Main execution"""
    logger.info("=" * 80)
    logger.info("FULL LAA-EVA SYSTEM WITH ADVANCED DSL CAPABILITIES")
    logger.info("=" * 80)

    # Load market data
    try:
        ohlcv_df = load_market_data('/Users/ivanhmac/github/pokpok/Archive/pokpok_agents/ivan/eth_30min_30days.json')
        logger.info(f"Loaded {len(ohlcv_df)} data points")
        logger.info(f"Date range: {ohlcv_df.index[0]} to {ohlcv_df.index[-1]}")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return

    # Initialize agents
    laa_agent = LAAAgentSimulator()
    eva_agent = EVAAgentSimulator()
    optimizer = ParameterOptimizer(laa_agent, eva_agent)

    # Run optimization
    logger.info("\n" + "=" * 60)
    logger.info("STARTING STRATEGY OPTIMIZATION FOR BEAR_TREND_LOW_VOL")
    logger.info("=" * 60)

    result = optimizer.optimize_strategy(
        market_regime='BEAR_TREND_LOW_VOL',
        ohlcv_df=ohlcv_df,
        max_iterations=30
    )

    # Display results
    if result:
        logger.info("\n" + "=" * 60)
        logger.info("🎯 PROFITABLE STRATEGY FOUND!")
        logger.info("=" * 60)

        eval_data = result['evaluation']
        stats = eval_data['backtest_results']['statistics']

        logger.info(f"\nStrategy: {result['strategy'].name}")
        logger.info(f"Fitness Score: {eval_data['fitness_score']:.3f}")
        logger.info(f"Fitness Reasoning: {eval_data['fitness_reasoning']}")

        logger.info(f"\n📊 PERFORMANCE METRICS:")
        logger.info(f"  - Win Rate: {stats['win_rate_pct']:.1f}%")
        logger.info(f"  - Total Return: {stats['total_return_pct']:.1f}%")
        logger.info(f"  - APR: {stats['apr']:.1f}%")
        logger.info(f"  - Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
        logger.info(f"  - Max Drawdown: {stats['max_drawdown_pct']:.1f}%")
        logger.info(f"  - Total Trades: {stats['total_trades']}")

        logger.info(f"\n🔧 OPTIMAL PARAMETERS:")
        for key, value in result['parameters'].items():
            logger.info(f"  - {key}: {value}")

        # Save results
        output_file = 'profitable_strategy_results.json'
        with open(output_file, 'w') as f:
            json.dump({
                'strategy_name': result['strategy'].name,
                'fitness_score': eval_data['fitness_score'],
                'parameters': result['parameters'],
                'statistics': stats,
                'dsl': result['strategy'].strategy_logic_dsl
            }, f, indent=2, default=str)
        logger.info(f"\n✅ Results saved to {output_file}")

    else:
        logger.info("\n" + "=" * 60)
        logger.info("❌ NO PROFITABLE STRATEGY FOUND")
        logger.info("=" * 60)

    # Display history
    logger.info("\n" + "=" * 60)
    logger.info("OPTIMIZATION HISTORY")
    logger.info("=" * 60)

    for entry in optimizer.optimization_history[-5:]:
        logger.info(f"Iteration {entry['iteration']}: Fitness={entry['fitness']:.3f}, "
                   f"WinRate={entry['win_rate']:.1f}%, Return={entry['total_return']:.1f}%")


if __name__ == "__main__":
    main()