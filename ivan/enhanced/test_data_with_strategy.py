"""
Quick test to verify the fetched data works with the strategy system
"""

import json
import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from portfolio_enhanced_laa_eva import PortfolioAwareDslExecutor
from portfolio_corrected_options import *
import uuid


def test_data_loading():
    """Test loading the fetched data"""
    print("🔍 Testing data loading...")

    try:
        # Load one of the datasets
        with open('../data/eth_30min_30days.json', 'r') as f:
            data = json.load(f)

        print(f"✅ Loaded dataset: {data['asset']} {data['timeframe']}")
        print(f"   Records: {data['total_records']}")
        print(f"   Source: {data['data_source']}")
        print(f"   Fetched: {data['fetched_at'][:10]}")

        # Convert to DataFrame
        ohlcv_data = data['ohlcv']
        df = pd.DataFrame(ohlcv_data)

        # Rename columns to match strategy system
        df = df.rename(columns={
            'Date': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        print(f"✅ DataFrame created with {len(df)} rows")
        print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"   Price range: ${df['low'].min():.2f} to ${df['high'].max():.2f}")

        return df

    except Exception as e:
        print(f"❌ Data loading failed: {e}")
        return None


def test_strategy_execution():
    """Test running a simple strategy on the fetched data"""
    print("\n🎯 Testing strategy execution...")

    # Load data
    df = test_data_loading()
    if df is None:
        return False

    try:
        # Simple test strategy
        strategy = {
            "strategy_logic_dsl": {
                "dsl_version": "2.0",
                "constants": {
                    "rsi_oversold": 30,
                    "rsi_overbought": 70
                },
                "indicators": [
                    {
                        "name": "rsi_main",
                        "type": "rsi",
                        "params": {"length": 14, "column": "close"},
                        "outputs": {"primary_output_column": "rsi_value"}
                    }
                ],
                "signal_rules": [
                    {
                        "rule_name": "oversold_bounce",
                        "conditions_group": {
                            "operator": "AND",
                            "conditions": [
                                {"series1": "rsi_value", "operator": "<", "series2_or_value": "@rsi_oversold"}
                            ]
                        },
                        "action_on_true": {
                            "signal_type": "CALL",
                            "strength": 5
                        },
                        "instrument_selection": {
                            "time_horizon_days": 3,
                            "volatility_threshold": 3.0
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

        # Generate signals
        executor = PortfolioAwareDslExecutor(
            strategy['strategy_logic_dsl'],
            str(uuid.uuid4())
        )
        signals = executor.generate_signals(df)

        print(f"✅ Generated {len(signals)} signals")

        # Convert to corrected format
        corrected_signals = []
        for sig in signals:
            if sig.signal != 0:
                corrected_signals.append(Signal(
                    timestamp=sig.timestamp.isoformat() if hasattr(sig.timestamp, 'isoformat') else str(sig.timestamp),
                    signal=sig.signal,
                    strength=sig.signal * 5,
                    instrument=sig.instrument_type,
                    reason=sig.rule_triggered,
                    entry_price=sig.last_close
                ))

        print(f"✅ Converted {len(corrected_signals)} active signals")

        # Quick backtest
        if corrected_signals:
            config = PortfolioConfig(
                initial_capital_eth=10.0,
                premium_per_trade_pct=5.0,
                max_daily_premium_pct=20.0,
                max_total_premium_pct=40.0
            )

            backtester = CorrectedPortfolioBacktester(config)
            results = backtester.run_backtest(corrected_signals, df)

            stats = results['statistics']
            print(f"\n📊 QUICK BACKTEST RESULTS:")
            print(f"   Trades: {stats['total_trades']}")
            print(f"   Win Rate: {stats['win_rate_pct']:.1f}%")
            print(f"   Total Return: {stats['total_return_pct']:.2f}%")
            if stats['total_trades'] > 0:
                print(f"   APR: {stats['simple_apr']:.1f}%")

            return True
        else:
            print("ℹ️  No active signals generated (this is normal)")
            return True

    except Exception as e:
        print(f"❌ Strategy execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_available_datasets():
    """Show all available datasets"""
    print("\n📂 Available datasets in /ivan/data:")

    try:
        with open('../data/fetch_summary.json', 'r') as f:
            summary = json.load(f)

        print(f"\n📊 Summary (fetched: {summary['fetch_completed_at'][:10]}):")
        print(f"   Total datasets: {summary['total_datasets']}")

        for dataset in summary['datasets']:
            name = dataset['name']
            records = dataset['records']
            timeframe = dataset['timeframe']
            days = dataset['lookback_days']
            start_date = dataset['date_range']['start'][:10]
            end_date = dataset['date_range']['end'][:10]

            print(f"\n   📈 {name}")
            print(f"      File: eth_{name}.json")
            print(f"      Records: {records:,} candles")
            print(f"      Timeframe: {timeframe}")
            print(f"      Period: {days} days ({start_date} to {end_date})")

        print(f"\n🎯 Usage in strategy system:")
        print(f"   datasets = {{")
        for dataset in summary['datasets']:
            name = dataset['name']
            print(f'      "{name}": load_data("../data/eth_{name}.json"),')
        print(f"   }}")

    except Exception as e:
        print(f"❌ Failed to read summary: {e}")


if __name__ == "__main__":
    print("🧪 Testing Deribit Data Integration")
    print("=" * 50)

    # Test 1: Show available datasets
    show_available_datasets()

    # Test 2: Test data loading and strategy execution
    success = test_strategy_execution()

    print("\n" + "=" * 50)
    if success:
        print("🎉 Data integration test PASSED!")
        print("\nYour data is ready for strategy testing!")
        print("Next steps:")
        print("1. Use the datasets shown above with your strategies")
        print("2. Run backtests across multiple timeframes")
        print("3. Compare results to find optimal strategies")
    else:
        print("❌ Data integration test FAILED!")
        print("Check the error messages above.")