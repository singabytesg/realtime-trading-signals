"""
Quick test on a single timeframe to debug the multi-timeframe tester
"""

import json
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from portfolio_corrected_options import *
from portfolio_enhanced_laa_eva import PortfolioAwareDslExecutor
import uuid


def load_data(filename: str) -> pd.DataFrame:
    """Load dataset from JSON file"""
    with open(f"../data/{filename}", 'r') as f:
        data = json.load(f)

    df = pd.DataFrame(data['ohlcv'])
    df = df.rename(columns={
        'Date': 'timestamp', 'Open': 'open', 'High': 'high',
        'Low': 'low', 'Close': 'close', 'Volume': 'volume'
    })
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def get_winning_strategy():
    """Return the winning strategy"""
    return {
        "strategy_logic_dsl": {
            "dsl_version": "2.0",
            "constants": {
                "rsi_oversold": 30,
                "rsi_overbought": 75,
                "macd_fast": 12,
                "macd_slow": 21,
                "macd_signal": 7,
                "sma_short_period": 15,
                "sma_long_period": 20,
                "atr_period": 10,
                "atr_threshold": 70,
                "high_vol_threshold": 3.5
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
                            "MACD_12_21_7": "macd_line",
                            "MACDs_12_21_7": "macd_signal",
                            "MACDh_12_21_7": "macd_hist"
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


def main():
    print("🧪 Testing Single Timeframe")
    print("="*50)

    # Load 30min data
    df = load_data("eth_30min_30days.json")
    print(f"✅ Loaded {len(df)} candles")

    # Get strategy
    strategy = get_winning_strategy()

    try:
        # Generate signals
        print("📊 Generating signals...")
        executor = PortfolioAwareDslExecutor(
            strategy['strategy_logic_dsl'],
            str(uuid.uuid4())
        )
        signals_raw = executor.generate_signals(df)
        print(f"✅ Generated {len(signals_raw)} raw signals")

        # Convert signals
        signals = []
        for sig in signals_raw:
            if sig.signal != 0:
                signals.append(Signal(
                    timestamp=sig.timestamp.isoformat() if hasattr(sig.timestamp, 'isoformat') else str(sig.timestamp),
                    signal=sig.signal,
                    strength=sig.signal * 7,
                    instrument=sig.instrument_type,
                    reason=sig.rule_triggered,
                    entry_price=sig.last_close
                ))

        print(f"✅ Converted {len(signals)} active signals")

        if signals:
            # Quick backtest
            config = PortfolioConfig(
                initial_capital_eth=10.0,
                premium_per_trade_pct=5.0,
                max_daily_premium_pct=20.0,
                max_total_premium_pct=40.0
            )

            backtester = CorrectedPortfolioBacktester(config)
            results = backtester.run_backtest(signals, df)

            stats = results['statistics']
            print(f"\n📈 RESULTS:")
            print(f"   Trades: {stats['total_trades']}")
            print(f"   Win Rate: {stats['win_rate_pct']:.1f}%")
            print(f"   Total Return: {stats['total_return_pct']:.2f}%")
            print(f"   APR: {stats['simple_apr']:.1f}%")
            print(f"   Max DD: {stats['max_drawdown_pct']:.1f}%")

            print("\n🎉 Single timeframe test successful!")
        else:
            print("ℹ️  No active signals generated")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()