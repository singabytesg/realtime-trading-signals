"""
Test the winning 77.8% strategy against all available timeframes

This will help identify which timeframes work best for the strategy
and discover optimal market conditions.
"""

import json
import pandas as pd
import sys
import os
from datetime import datetime
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from portfolio_corrected_options import *
from portfolio_enhanced_laa_eva import PortfolioAwareDslExecutor
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MultiTimeframeStrategyTester:
    """Test strategies across multiple timeframes and configurations"""

    def __init__(self):
        self.results = []

        # Portfolio configurations to test
        self.portfolio_configs = {
            "Conservative": PortfolioConfig(
                initial_capital_eth=10.0,
                premium_per_trade_pct=2.0,
                max_daily_premium_pct=10.0,
                max_total_premium_pct=20.0,
                max_concurrent_positions=10,
                max_drawdown_pct=20.0
            ),
            "Moderate": PortfolioConfig(
                initial_capital_eth=10.0,
                premium_per_trade_pct=5.0,
                max_daily_premium_pct=20.0,
                max_total_premium_pct=40.0,
                max_concurrent_positions=8,
                max_drawdown_pct=25.0
            ),
            "Aggressive": PortfolioConfig(
                initial_capital_eth=10.0,
                premium_per_trade_pct=10.0,
                max_daily_premium_pct=30.0,
                max_total_premium_pct=60.0,
                max_concurrent_positions=6,
                max_drawdown_pct=30.0
            )
        }

    def load_data(self, filename: str) -> pd.DataFrame:
        """Load dataset from JSON file"""
        try:
            with open(f"../data/{filename}", 'r') as f:
                data = json.load(f)

            df = pd.DataFrame(data['ohlcv'])
            df = df.rename(columns={
                'Date': 'timestamp', 'Open': 'open', 'High': 'high',
                'Low': 'low', 'Close': 'close', 'Volume': 'volume'
            })
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            logger.info(f"Loaded {filename}: {len(df)} candles, {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
            return df

        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")
            return None

    def get_winning_strategy(self) -> Dict[str, Any]:
        """Return the exact winning strategy parameters"""
        return {
            "strategy_logic_dsl": {
                "dsl_version": "2.0",
                "description": "Enhanced BEAR_TREND_LOW_VOL strategy - 77.8% win rate",
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
                    "high_vol_threshold": 3.5,
                    "expected_move_threshold": 4.0
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
                        },
                        "instrument_selection": {
                            "time_horizon_days": 7,
                            "volatility_threshold": "@high_vol_threshold"
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
                        },
                        "instrument_selection": {
                            "time_horizon_days": 3,
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
            }
        }

    def test_strategy_on_dataset(self, dataset_name: str, strategy: Dict[str, Any],
                                config_name: str, config: PortfolioConfig) -> Dict[str, Any]:
        """Test a strategy on a specific dataset"""

        # Load data
        df = self.load_data(f"eth_{dataset_name}.json")
        if df is None:
            return None

        try:
            # Generate signals
            executor = PortfolioAwareDslExecutor(
                strategy['strategy_logic_dsl'],
                str(uuid.uuid4())
            )
            signals_raw = executor.generate_signals(df)

            # Convert to corrected Signal format
            signals = []
            for sig in signals_raw:
                if sig.signal != 0:
                    strength = sig.signal * 7  # Default strength multiplier

                    signals.append(Signal(
                        timestamp=sig.timestamp.isoformat() if hasattr(sig.timestamp, 'isoformat') else str(sig.timestamp),
                        signal=sig.signal,
                        strength=strength,
                        instrument=sig.instrument_type,
                        reason=sig.rule_triggered,
                        entry_price=sig.last_close
                    ))

            logger.info(f"{dataset_name} - {config_name}: Generated {len(signals)} active signals")

            if not signals:
                # Return empty results if no signals
                return {
                    'dataset': dataset_name,
                    'config': config_name,
                    'data_info': {
                        'candles': len(df),
                        'start_date': df['timestamp'].min().date().isoformat(),
                        'end_date': df['timestamp'].max().date().isoformat(),
                        'trading_days': (df['timestamp'].max() - df['timestamp'].min()).days
                    },
                    'signals_generated': 0,
                    'statistics': {
                        'total_trades': 0,
                        'win_rate_pct': 0,
                        'total_return_pct': 0,
                        'simple_apr': 0,
                        'premium_efficient_apr': 0,
                        'max_drawdown_pct': 0,
                        'sharpe_ratio': 0
                    },
                    'success': False,
                    'reason': 'No signals generated'
                }

            # Run backtest
            backtester = CorrectedPortfolioBacktester(config)
            results = backtester.run_backtest(signals, df)

            stats = results['statistics']

            # Calculate fitness score
            fitness = (
                stats['simple_apr'] * 0.4 +
                stats['win_rate_pct'] * 0.3 +
                (stats['sharpe_ratio'] * 10) * 0.2 -
                stats['max_drawdown_pct'] * 0.1
            )

            return {
                'dataset': dataset_name,
                'config': config_name,
                'data_info': {
                    'candles': len(df),
                    'start_date': df['timestamp'].min().date().isoformat(),
                    'end_date': df['timestamp'].max().date().isoformat(),
                    'trading_days': (df['timestamp'].max() - df['timestamp'].min()).days
                },
                'signals_generated': len(signals),
                'statistics': stats,
                'fitness_score': fitness,
                'success': True,
                'trades': results.get('trade_logs', [])
            }

        except Exception as e:
            logger.error(f"Error testing {dataset_name} - {config_name}: {e}")
            return {
                'dataset': dataset_name,
                'config': config_name,
                'success': False,
                'error': str(e)
            }

    def run_comprehensive_test(self) -> List[Dict[str, Any]]:
        """Run the winning strategy across all timeframes and configurations"""

        # Get available datasets
        try:
            with open('../data/fetch_summary.json', 'r') as f:
                summary = json.load(f)
            datasets = [d['name'] for d in summary['datasets']]
        except:
            # Fallback to known datasets
            datasets = [
                "5min_30days", "15min_30days", "30min_30days",
                "30min_60days", "1hour_60days", "2hour_60days", "6hour_60days",
                "6hour_90days", "12hour_90days", "1day_90days",
                "12hour_180days", "1day_180days"
            ]

        logger.info(f"Testing strategy on {len(datasets)} datasets with {len(self.portfolio_configs)} configurations")

        strategy = self.get_winning_strategy()
        all_results = []

        for dataset_name in datasets:
            logger.info(f"\n{'='*60}")
            logger.info(f"TESTING DATASET: {dataset_name}")
            logger.info(f"{'='*60}")

            for config_name, config in self.portfolio_configs.items():
                logger.info(f"\nTesting with {config_name} configuration...")

                result = self.test_strategy_on_dataset(dataset_name, strategy, config_name, config)
                if result:
                    all_results.append(result)

        self.results = all_results
        return all_results

    def analyze_results(self) -> Dict[str, Any]:
        """Analyze and compare results across all tests"""

        if not self.results:
            return {}

        successful_results = [r for r in self.results if r.get('success', False) and r['statistics']['total_trades'] > 0]

        if not successful_results:
            return {
                'total_tests': len(self.results),
                'successful_tests': 0,
                'message': 'No successful trades found across any timeframes'
            }

        # Overall statistics
        analysis = {
            'total_tests': len(self.results),
            'successful_tests': len(successful_results),
            'success_rate': (len(successful_results) / len(self.results)) * 100
        }

        # Best performers
        best_by_apr = max(successful_results, key=lambda x: x['statistics']['simple_apr'])
        best_by_winrate = max(successful_results, key=lambda x: x['statistics']['win_rate_pct'])
        best_by_fitness = max(successful_results, key=lambda x: x.get('fitness_score', -999))

        analysis['best_performers'] = {
            'highest_apr': {
                'dataset': best_by_apr['dataset'],
                'config': best_by_apr['config'],
                'apr': best_by_apr['statistics']['simple_apr'],
                'win_rate': best_by_apr['statistics']['win_rate_pct'],
                'fitness': best_by_fitness.get('fitness_score', 0)
            },
            'highest_winrate': {
                'dataset': best_by_winrate['dataset'],
                'config': best_by_winrate['config'],
                'apr': best_by_winrate['statistics']['simple_apr'],
                'win_rate': best_by_winrate['statistics']['win_rate_pct'],
                'fitness': best_by_fitness.get('fitness_score', 0)
            },
            'highest_fitness': {
                'dataset': best_by_fitness['dataset'],
                'config': best_by_fitness['config'],
                'apr': best_by_fitness['statistics']['simple_apr'],
                'win_rate': best_by_fitness['statistics']['win_rate_pct'],
                'fitness': best_by_fitness.get('fitness_score', 0)
            }
        }

        # Timeframe analysis
        timeframe_stats = {}
        for result in successful_results:
            timeframe = result['dataset'].split('_')[0]
            if timeframe not in timeframe_stats:
                timeframe_stats[timeframe] = {
                    'tests': 0,
                    'avg_apr': 0,
                    'avg_winrate': 0,
                    'avg_fitness': 0,
                    'best_result': None
                }

            ts = timeframe_stats[timeframe]
            ts['tests'] += 1
            ts['avg_apr'] += result['statistics']['simple_apr']
            ts['avg_winrate'] += result['statistics']['win_rate_pct']
            ts['avg_fitness'] += result.get('fitness_score', 0)

            if ts['best_result'] is None or result.get('fitness_score', 0) > ts['best_result'].get('fitness_score', -999):
                ts['best_result'] = result

        # Calculate averages
        for timeframe, stats in timeframe_stats.items():
            if stats['tests'] > 0:
                stats['avg_apr'] /= stats['tests']
                stats['avg_winrate'] /= stats['tests']
                stats['avg_fitness'] /= stats['tests']

        analysis['timeframe_analysis'] = timeframe_stats

        # Configuration analysis
        config_stats = {}
        for result in successful_results:
            config = result['config']
            if config not in config_stats:
                config_stats[config] = {
                    'tests': 0,
                    'avg_apr': 0,
                    'avg_winrate': 0,
                    'best_result': None
                }

            cs = config_stats[config]
            cs['tests'] += 1
            cs['avg_apr'] += result['statistics']['simple_apr']
            cs['avg_winrate'] += result['statistics']['win_rate_pct']

            if cs['best_result'] is None or result.get('fitness_score', 0) > cs['best_result'].get('fitness_score', -999):
                cs['best_result'] = result

        # Calculate config averages
        for config, stats in config_stats.items():
            if stats['tests'] > 0:
                stats['avg_apr'] /= stats['tests']
                stats['avg_winrate'] /= stats['tests']

        analysis['configuration_analysis'] = config_stats

        return analysis

    def save_results(self, filename: str = "multi_timeframe_results.json"):
        """Save all results to a JSON file"""
        output = {
            'test_completed_at': datetime.now().isoformat(),
            'strategy_tested': 'Winning 77.8% Strategy',
            'results': self.results,
            'analysis': self.analyze_results()
        }

        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)

        logger.info(f"Results saved to {filename}")

    def print_summary(self):
        """Print a comprehensive summary of results"""

        analysis = self.analyze_results()

        if not analysis or 'success_rate' not in analysis:
            print("❌ No results to analyze")
            return

        print("\n" + "="*80)
        print("MULTI-TIMEFRAME STRATEGY TEST RESULTS")
        print("="*80)

        print(f"\n📊 OVERVIEW:")
        print(f"   Total Tests: {analysis['total_tests']}")
        print(f"   Successful Tests: {analysis['successful_tests']}")
        print(f"   Success Rate: {analysis['success_rate']:.1f}%")

        print(f"\n🏆 BEST PERFORMERS:")
        bp = analysis['best_performers']

        print(f"\n   Highest APR:")
        print(f"      Dataset: {bp['highest_apr']['dataset']}")
        print(f"      Config: {bp['highest_apr']['config']}")
        print(f"      APR: {bp['highest_apr']['apr']:.1f}%")
        print(f"      Win Rate: {bp['highest_apr']['win_rate']:.1f}%")

        print(f"\n   Highest Win Rate:")
        print(f"      Dataset: {bp['highest_winrate']['dataset']}")
        print(f"      Config: {bp['highest_winrate']['config']}")
        print(f"      APR: {bp['highest_winrate']['apr']:.1f}%")
        print(f"      Win Rate: {bp['highest_winrate']['win_rate']:.1f}%")

        print(f"\n   Best Overall (Fitness Score):")
        print(f"      Dataset: {bp['highest_fitness']['dataset']}")
        print(f"      Config: {bp['highest_fitness']['config']}")
        print(f"      APR: {bp['highest_fitness']['apr']:.1f}%")
        print(f"      Win Rate: {bp['highest_fitness']['win_rate']:.1f}%")
        print(f"      Fitness: {bp['highest_fitness']['fitness']:.2f}")

        print(f"\n📈 TIMEFRAME ANALYSIS:")
        ta = analysis['timeframe_analysis']

        # Sort by average fitness score
        sorted_timeframes = sorted(ta.items(), key=lambda x: x[1]['avg_fitness'], reverse=True)

        for timeframe, stats in sorted_timeframes:
            print(f"\n   {timeframe.upper()} Timeframe:")
            print(f"      Tests: {stats['tests']}")
            print(f"      Avg APR: {stats['avg_apr']:.1f}%")
            print(f"      Avg Win Rate: {stats['avg_winrate']:.1f}%")
            print(f"      Avg Fitness: {stats['avg_fitness']:.2f}")
            if stats['best_result']:
                best = stats['best_result']
                print(f"      Best: {best['dataset']} ({best['config']}) - {best['statistics']['simple_apr']:.1f}% APR")

        print(f"\n⚙️  CONFIGURATION ANALYSIS:")
        ca = analysis['configuration_analysis']

        for config, stats in ca.items():
            print(f"\n   {config} Configuration:")
            print(f"      Tests: {stats['tests']}")
            print(f"      Avg APR: {stats['avg_apr']:.1f}%")
            print(f"      Avg Win Rate: {stats['avg_winrate']:.1f}%")
            if stats['best_result']:
                best = stats['best_result']
                print(f"      Best: {best['dataset']} - {best['statistics']['simple_apr']:.1f}% APR")


def main():
    """Run the comprehensive multi-timeframe test"""

    print("🚀 Starting Multi-Timeframe Strategy Test")
    print("Strategy: Winning 77.8% Win Rate Strategy")
    print("="*80)

    # Initialize tester
    tester = MultiTimeframeStrategyTester()

    # Run comprehensive test
    logger.info("Starting comprehensive test across all timeframes...")
    results = tester.run_comprehensive_test()

    # Analyze and display results
    tester.print_summary()

    # Save results
    tester.save_results("multi_timeframe_test_results.json")

    print("\n" + "="*80)
    print("🎉 Multi-timeframe testing complete!")
    print("📊 Detailed results saved to: multi_timeframe_test_results.json")
    print("🔍 Check the summary above for optimal timeframes and configurations")


if __name__ == "__main__":
    main()