"""
Quick multi-timeframe test - simplified version
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
                        "strength": -3
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


def test_dataset(dataset_name, strategy, config_name, config):
    """Test strategy on a single dataset"""
    try:
        print(f"\n📊 Testing {dataset_name} with {config_name} config...")

        # Load data
        df = load_data(f"eth_{dataset_name}.json")

        # Generate signals
        executor = PortfolioAwareDslExecutor(strategy['strategy_logic_dsl'], str(uuid.uuid4()))
        signals_raw = executor.generate_signals(df)

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

        if not signals:
            print(f"   ⚠️  No signals generated")
            return None

        # Backtest
        backtester = CorrectedPortfolioBacktester(config)
        results = backtester.run_backtest(signals, df)
        stats = results['statistics']

        result = {
            'dataset': dataset_name,
            'config': config_name,
            'candles': len(df),
            'period_days': (df['timestamp'].max() - df['timestamp'].min()).days,
            'signals': len(signals),
            'trades': stats['total_trades'],
            'win_rate': stats['win_rate_pct'],
            'total_return': stats['total_return_pct'],
            'apr': stats['simple_apr'],
            'premium_apr': stats['premium_efficient_apr'],
            'max_dd': stats['max_drawdown_pct'],
            'sharpe': stats['sharpe_ratio']
        }

        print(f"   ✅ {stats['total_trades']} trades, {stats['win_rate_pct']:.1f}% WR, {stats['simple_apr']:.1f}% APR")
        return result

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def main():
    print("🚀 Quick Multi-Timeframe Strategy Test")
    print("="*60)

    # Test datasets (select key ones)
    datasets = [
        "15min_30days",   # High frequency
        "30min_30days",   # Original winning dataset
        "30min_60days",   # Extended period
        "1hour_60days",   # Different timeframe
        "6hour_90days",   # Longer timeframe
        "1day_90days"     # Daily timeframe
    ]

    # Portfolio config
    config = PortfolioConfig(
        initial_capital_eth=10.0,
        premium_per_trade_pct=5.0,
        max_daily_premium_pct=20.0,
        max_total_premium_pct=40.0
    )

    strategy = get_winning_strategy()
    results = []

    print(f"Testing {len(datasets)} datasets...")

    for dataset in datasets:
        result = test_dataset(dataset, strategy, "Moderate", config)
        if result:
            results.append(result)

    # Analysis
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")

    if not results:
        print("❌ No successful tests")
        return

    # Sort by APR
    results.sort(key=lambda x: x['apr'], reverse=True)

    print(f"\n📈 TOP PERFORMERS (by APR):")
    print(f"{'Dataset':<15} {'Candles':<8} {'Days':<5} {'Trades':<6} {'WR%':<6} {'APR%':<8} {'MaxDD%':<7}")
    print("-" * 65)

    for r in results:
        print(f"{r['dataset']:<15} {r['candles']:<8} {r['period_days']:<5} {r['trades']:<6} "
              f"{r['win_rate']:>5.1f} {r['apr']:>7.1f} {r['max_dd']:>6.1f}")

    # Best by different metrics
    if results:
        best_apr = max(results, key=lambda x: x['apr'])
        best_wr = max(results, key=lambda x: x['win_rate'])
        best_sharpe = max(results, key=lambda x: x.get('sharpe', 0))

        print(f"\n🏆 BEST PERFORMERS:")
        print(f"   Best APR: {best_apr['dataset']} ({best_apr['apr']:.1f}% APR, {best_apr['win_rate']:.1f}% WR)")
        print(f"   Best Win Rate: {best_wr['dataset']} ({best_wr['win_rate']:.1f}% WR, {best_wr['apr']:.1f}% APR)")
        print(f"   Best Sharpe: {best_sharpe['dataset']} ({best_sharpe.get('sharpe', 0):.2f} Sharpe)")

    # Timeframe analysis
    timeframe_stats = {}
    for r in results:
        tf = r['dataset'].split('_')[0]
        if tf not in timeframe_stats:
            timeframe_stats[tf] = {'count': 0, 'avg_apr': 0, 'avg_wr': 0}

        timeframe_stats[tf]['count'] += 1
        timeframe_stats[tf]['avg_apr'] += r['apr']
        timeframe_stats[tf]['avg_wr'] += r['win_rate']

    print(f"\n📊 TIMEFRAME ANALYSIS:")
    for tf, stats in timeframe_stats.items():
        if stats['count'] > 0:
            avg_apr = stats['avg_apr'] / stats['count']
            avg_wr = stats['avg_wr'] / stats['count']
            print(f"   {tf.upper():>6}: {avg_apr:>6.1f}% APR, {avg_wr:>5.1f}% WR (n={stats['count']})")

    print(f"\n🎯 INSIGHTS:")
    if results:
        # Find patterns
        short_term = [r for r in results if int(r['period_days']) <= 35]
        long_term = [r for r in results if int(r['period_days']) > 60]

        if short_term and long_term:
            st_avg = sum(r['apr'] for r in short_term) / len(short_term)
            lt_avg = sum(r['apr'] for r in long_term) / len(long_term)

            print(f"   Short-term periods (≤35 days): {st_avg:.1f}% avg APR")
            print(f"   Long-term periods (>60 days): {lt_avg:.1f}% avg APR")

            if st_avg > lt_avg:
                print(f"   → Strategy performs better on shorter time periods")
            else:
                print(f"   → Strategy performs better on longer time periods")


if __name__ == "__main__":
    main()