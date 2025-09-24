# LAA-EVA Strategy Generation & Backtesting System

## Overview

This system generates and backtests quantitative trading strategies for options using a Domain Specific Language (DSL). It achieved **77.8% win rate** and **181% APR** on 30-day ETH data using proper option mechanics.

## Core Components

### 1. Strategy DSL Structure

```python
strategy = {
    "strategy_logic_dsl": {
        "dsl_version": "2.1",
        "description": "Strategy description",
        "constants": {
            # Tunable parameters with @variable references
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
            # Technical indicators with parameter mapping
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
            }
        ],
        "signal_rules": [
            # Signal generation rules
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
                    "strength": -7
                },
                "instrument_selection": {
                    "time_horizon_days": 7,
                    "volatility_threshold": "@high_vol_threshold"
                }
            }
        ],
        "default_action_on_no_match": {
            "signal_type": "NEUTRAL",
            "strength": 0,
            "instrument_type": "3D_5PCT"
        }
    }
}
```

### 2. Advanced DSL Operators

```python
SUPPORTED_OPERATORS = [
    # Basic comparisons
    ">", "<", ">=", "<=", "==", "!=",

    # Advanced crossing detection
    "crosses_above",     # val1 was <= val2, now val1 > val2
    "crosses_below",     # val1 was >= val2, now val1 < val2

    # Trend analysis
    "is_rising",         # Values trending upward
    "is_falling",        # Values trending downward
    "is_between",        # Value within range
    "is_not_between"     # Value outside range
]
```

### 3. Option Instrument Types

```python
OPTION_INSTRUMENTS = {
    "3D_5PCT": {
        "duration_days": 3,
        "profit_cap_pct": 5.0,
        "premium_cost_pct": 2.2    # Cheapest option
    },
    "3D_10PCT": {
        "duration_days": 3,
        "profit_cap_pct": 10.0,
        "premium_cost_pct": 2.6
    },
    "7D_5PCT": {
        "duration_days": 7,
        "profit_cap_pct": 5.0,
        "premium_cost_pct": 2.8
    },
    "7D_10PCT": {
        "duration_days": 7,
        "profit_cap_pct": 10.0,
        "premium_cost_pct": 2.8    # Best risk/reward for strong signals
    }
}
```

## Strategy Generation Templates

### Template 1: Mean Reversion Strategy

```python
def generate_mean_reversion_strategy(rsi_oversold=30, rsi_overbought=70, bb_std=2.0):
    return {
        "strategy_logic_dsl": {
            "constants": {
                "rsi_oversold": rsi_oversold,
                "rsi_overbought": rsi_overbought,
                "bb_period": 20,
                "bb_std": bb_std
            },
            "indicators": [
                {"name": "rsi", "type": "rsi", "params": {"length": 14}},
                {"name": "bb", "type": "bollinger_bands", "params": {"length": "@bb_period", "std": "@bb_std"}}
            ],
            "signal_rules": [
                {
                    "rule_name": "oversold_bounce",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {"series1": "rsi_value", "operator": "<", "series2_or_value": "@rsi_oversold"},
                            {"series1": "close", "operator": "<", "series2_or_value": "bb_lower"}
                        ]
                    },
                    "action_on_true": {"signal_type": "CALL", "strength": 5},
                    "instrument_selection": {"time_horizon_days": 3}
                },
                {
                    "rule_name": "overbought_decline",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {"series1": "rsi_value", "operator": ">", "series2_or_value": "@rsi_overbought"},
                            {"series1": "close", "operator": ">", "series2_or_value": "bb_upper"}
                        ]
                    },
                    "action_on_true": {"signal_type": "PUT", "strength": -5},
                    "instrument_selection": {"time_horizon_days": 3}
                }
            ]
        }
    }
```

### Template 2: Trend Following Strategy

```python
def generate_trend_following_strategy(ema_fast=12, ema_slow=26, atr_mult=2.0):
    return {
        "strategy_logic_dsl": {
            "constants": {
                "ema_fast": ema_fast,
                "ema_slow": ema_slow,
                "atr_mult": atr_mult
            },
            "indicators": [
                {"name": "ema_fast", "type": "ema", "params": {"length": "@ema_fast"}},
                {"name": "ema_slow", "type": "ema", "params": {"length": "@ema_slow"}},
                {"name": "atr", "type": "atr", "params": {"length": 14}}
            ],
            "signal_rules": [
                {
                    "rule_name": "bullish_breakout",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {"series1": "ema_fast", "operator": "crosses_above", "series2_or_value": "ema_slow"},
                            {"series1": "close", "operator": ">", "series2_or_value": "ema_fast"}
                        ]
                    },
                    "action_on_true": {"signal_type": "CALL", "strength": 7},
                    "instrument_selection": {"time_horizon_days": 7}
                }
            ]
        }
    }
```

### Template 3: Breakout Strategy

```python
def generate_breakout_strategy(lookback_days=20, breakout_threshold=2.0):
    return {
        "strategy_logic_dsl": {
            "constants": {
                "lookback_period": lookback_days,
                "breakout_mult": breakout_threshold
            },
            "indicators": [
                {"name": "highest", "type": "highest", "params": {"length": "@lookback_period"}},
                {"name": "lowest", "type": "lowest", "params": {"length": "@lookback_period"}},
                {"name": "atr", "type": "atr", "params": {"length": 14}}
            ],
            "signal_rules": [
                {
                    "rule_name": "upside_breakout",
                    "conditions_group": {
                        "operator": "AND",
                        "conditions": [
                            {"series1": "close", "operator": ">", "series2_or_value": "highest"},
                            {"series1": "atr_value", "operator": ">", "series2_or_value": 50}
                        ]
                    },
                    "action_on_true": {"signal_type": "CALL", "strength": 8},
                    "instrument_selection": {"time_horizon_days": 7}
                }
            ]
        }
    }
```

## Portfolio Configuration Templates

### Conservative Profile (2% risk per trade)
```python
conservative_config = PortfolioConfig(
    initial_capital_eth=10.0,
    premium_per_trade_pct=2.0,        # Risk 2% premium per trade
    max_daily_premium_pct=8.0,        # Max 8% daily
    max_total_premium_pct=15.0,       # Max 15% total exposure
    max_concurrent_positions=10,
    max_drawdown_pct=15.0
)
```

### Moderate Profile (5% risk per trade)
```python
moderate_config = PortfolioConfig(
    initial_capital_eth=10.0,
    premium_per_trade_pct=5.0,        # Risk 5% premium per trade
    max_daily_premium_pct=20.0,       # Max 20% daily
    max_total_premium_pct=40.0,       # Max 40% total exposure
    max_concurrent_positions=8,
    max_drawdown_pct=25.0
)
```

### Aggressive Profile (10% risk per trade)
```python
aggressive_config = PortfolioConfig(
    initial_capital_eth=10.0,
    premium_per_trade_pct=10.0,       # Risk 10% premium per trade
    max_daily_premium_pct=30.0,       # Max 30% daily
    max_total_premium_pct=60.0,       # Max 60% total exposure
    max_concurrent_positions=6,
    max_drawdown_pct=35.0
)
```

## Usage Examples

### 1. Generate and Test Multiple Strategies

```python
# Strategy variations
strategies_to_test = [
    generate_mean_reversion_strategy(rsi_oversold=25, rsi_overbought=75),
    generate_mean_reversion_strategy(rsi_oversold=30, rsi_overbought=70),
    generate_mean_reversion_strategy(rsi_oversold=35, rsi_overbought=65),

    generate_trend_following_strategy(ema_fast=8, ema_slow=21),
    generate_trend_following_strategy(ema_fast=12, ema_slow=26),
    generate_trend_following_strategy(ema_fast=21, ema_slow=55),

    generate_breakout_strategy(lookback_days=10, breakout_threshold=1.5),
    generate_breakout_strategy(lookback_days=20, breakout_threshold=2.0),
    generate_breakout_strategy(lookback_days=30, breakout_threshold=2.5)
]

# Test each strategy
results = []
for i, strategy in enumerate(strategies_to_test):
    print(f"Testing Strategy {i+1}...")

    # Generate signals
    executor = PortfolioAwareDslExecutor(strategy['strategy_logic_dsl'], f"strategy_{i}")
    signals = executor.generate_signals(ohlcv_df)

    # Backtest with different configs
    for config_name, config in [("Conservative", conservative_config), ("Aggressive", aggressive_config)]:
        backtester = CorrectedPortfolioBacktester(config)
        result = backtester.run_backtest(signals, ohlcv_df)

        results.append({
            'strategy_id': i,
            'config': config_name,
            'win_rate': result['statistics']['win_rate_pct'],
            'total_return': result['statistics']['total_return_pct'],
            'apr': result['statistics']['simple_apr'],
            'max_drawdown': result['statistics']['max_drawdown_pct'],
            'trades': result['statistics']['total_trades']
        })

# Find best performers
best_strategies = sorted(results, key=lambda x: x['apr'], reverse=True)[:5]
```

### 2. Test Different Data Timeframes

```python
# Load different datasets
datasets = {
    "30min_30days": load_data("eth_30min_30days.json"),
    "1hour_60days": load_data("eth_1hour_60days.json"),
    "4hour_90days": load_data("eth_4hour_90days.json"),
    "1day_180days": load_data("eth_1day_180days.json")
}

# Test winning strategy across all timeframes
winning_strategy = {...}  # Your best strategy

for timeframe, data in datasets.items():
    print(f"\n=== Testing on {timeframe} ===")

    executor = PortfolioAwareDslExecutor(winning_strategy['strategy_logic_dsl'], f"test_{timeframe}")
    signals = executor.generate_signals(data)

    backtester = CorrectedPortfolioBacktester(moderate_config)
    result = backtester.run_backtest(signals, data)

    stats = result['statistics']
    print(f"Win Rate: {stats['win_rate_pct']:.1f}%")
    print(f"APR: {stats['simple_apr']:.1f}%")
    print(f"Max DD: {stats['max_drawdown_pct']:.1f}%")
    print(f"Trades: {stats['total_trades']}")
```

### 3. Parameter Optimization

```python
def optimize_strategy_parameters():
    # Parameter ranges to test
    rsi_oversold_range = [20, 25, 30, 35]
    rsi_overbought_range = [65, 70, 75, 80]
    macd_fast_range = [8, 12, 16, 20]
    macd_slow_range = [21, 26, 30, 35]

    best_fitness = -999
    best_params = None

    for rsi_os in rsi_oversold_range:
        for rsi_ob in rsi_overbought_range:
            for macd_f in macd_fast_range:
                for macd_s in macd_slow_range:
                    if macd_f >= macd_s:  # Skip invalid combinations
                        continue

                    # Create strategy with these parameters
                    strategy = generate_mean_reversion_strategy(
                        rsi_oversold=rsi_os,
                        rsi_overbought=rsi_ob
                    )
                    strategy['strategy_logic_dsl']['constants']['macd_fast'] = macd_f
                    strategy['strategy_logic_dsl']['constants']['macd_slow'] = macd_s

                    # Test strategy
                    executor = PortfolioAwareDslExecutor(strategy['strategy_logic_dsl'], "optimizer")
                    signals = executor.generate_signals(ohlcv_df)

                    backtester = CorrectedPortfolioBacktester(moderate_config)
                    result = backtester.run_backtest(signals, ohlcv_df)

                    # Calculate fitness score
                    stats = result['statistics']
                    fitness = (
                        stats['simple_apr'] * 0.4 +
                        stats['win_rate_pct'] * 0.3 +
                        (stats['sharpe_ratio'] * 10) * 0.2 -
                        stats['max_drawdown_pct'] * 0.1
                    )

                    if fitness > best_fitness:
                        best_fitness = fitness
                        best_params = {
                            'rsi_oversold': rsi_os,
                            'rsi_overbought': rsi_ob,
                            'macd_fast': macd_f,
                            'macd_slow': macd_s,
                            'fitness': fitness,
                            'stats': stats
                        }

    return best_params
```

## Key Files to Use

1. **portfolio_corrected_options.py** - Core backtesting engine with proper option mechanics
2. **portfolio_enhanced_laa_eva.py** - DSL executor for signal generation
3. **enhanced_laa_eva_with_instruments.py** - Template for instrument selection logic
4. **save_corrected_results.py** - Result saving and analysis

## Success Metrics

- **Win Rate**: Target >65% for options trading
- **APR**: Annualized return on capital
- **Premium-Efficient APR**: Return on premium deployed (shows true efficiency)
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Risk management effectiveness
- **Profit Factor**: Gross profit / Gross loss

## Quick Start

1. Load your market data (OHLCV format)
2. Choose/generate a strategy using templates above
3. Configure portfolio risk parameters
4. Run backtest and analyze results
5. Optimize parameters for better performance
6. Test across different timeframes and market conditions

The system achieved **77.8% win rate** and **181% APR** with proper implementation. Focus on high-quality signals over quantity for best results.