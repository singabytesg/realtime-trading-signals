"""
Test the CORRECTED portfolio system with the winning 77% win rate strategy
"""

import json
import sys
import os
import logging
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from portfolio_corrected_options import *
from portfolio_enhanced_laa_eva import PortfolioAwareDslExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run the winning strategy with CORRECTED option mechanics"""

    logger.info("=" * 80)
    logger.info("TESTING WINNING STRATEGY WITH CORRECTED OPTION MECHANICS")
    logger.info("=" * 80)

    # Load market data
    try:
        with open('/Users/ivanhmac/github/pokpok/Archive/pokpok_agents/ivan/eth_30min_30days.json', 'r') as f:
            data = json.load(f)
        # Extract the ohlcv array from the JSON
        ohlcv_data = data['ohlcv'] if 'ohlcv' in data else data
        ohlcv_df = pd.DataFrame(ohlcv_data)

        # Rename columns to match expected format
        ohlcv_df = ohlcv_df.rename(columns={
            'Date': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        ohlcv_df['timestamp'] = pd.to_datetime(ohlcv_df['timestamp'])
        logger.info(f"Loaded {len(ohlcv_df)} data points")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        import traceback
        traceback.print_exc()
        return

    # Use the EXACT winning parameters from enhanced_strategy_results.json
    winning_strategy = {
        "strategy_logic_dsl": {
            "dsl_version": "2.0",
            "description": "Enhanced BEAR_TREND_LOW_VOL strategy with dynamic instrument selection",
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

    # Generate signals using the existing DSL executor
    logger.info("\nGenerating signals from winning strategy...")
    executor = PortfolioAwareDslExecutor(
        winning_strategy['strategy_logic_dsl'],
        str(uuid.uuid4())
    )
    signals_raw = executor.generate_signals(ohlcv_df)

    # Convert to corrected Signal format
    signals = []
    for sig in signals_raw:
        if sig.signal != 0:  # Skip neutral signals
            # Map signal value to strength (signal is -1 or 1, we need strength -10 to 10)
            strength = sig.signal * 7  # Default to 7 for strong signals

            # Convert timestamp properly - it's likely a pandas Timestamp object
            if hasattr(sig.timestamp, 'isoformat'):
                timestamp_str = sig.timestamp.isoformat()
            elif hasattr(sig.timestamp, 'strftime'):
                timestamp_str = sig.timestamp.strftime('%Y-%m-%dT%H:%M:%S')
            else:
                # It might be a nanosecond timestamp
                timestamp_str = pd.Timestamp(sig.timestamp).isoformat()

            signals.append(Signal(
                timestamp=timestamp_str,
                signal=sig.signal,
                strength=strength,
                instrument=sig.instrument_type,  # Use instrument_type from EnhancedOptionsSignal
                reason=sig.rule_triggered,  # Use rule_triggered as reason
                entry_price=sig.last_close  # Use last_close as entry price
            ))

    logger.info(f"Generated {len(signals)} active signals")

    # Debug: show first few signals
    if signals:
        logger.info(f"First signal: timestamp={signals[0].timestamp}, instrument={signals[0].instrument}, signal={signals[0].signal}")
        logger.info(f"Last signal: timestamp={signals[-1].timestamp}, instrument={signals[-1].instrument}, signal={signals[-1].signal}")

    # Test with different portfolio configurations
    configurations = [
        {
            "name": "Conservative (2% premium per trade)",
            "config": PortfolioConfig(
                initial_capital_eth=10.0,
                premium_per_trade_pct=2.0,  # 2% risk per trade
                max_daily_premium_pct=10.0,
                max_total_premium_pct=20.0,
                max_concurrent_positions=10
            )
        },
        {
            "name": "Moderate (5% premium per trade)",
            "config": PortfolioConfig(
                initial_capital_eth=10.0,
                premium_per_trade_pct=5.0,  # 5% risk per trade
                max_daily_premium_pct=20.0,
                max_total_premium_pct=40.0,
                max_concurrent_positions=8
            )
        },
        {
            "name": "Aggressive (10% premium per trade)",
            "config": PortfolioConfig(
                initial_capital_eth=10.0,
                premium_per_trade_pct=10.0,  # 10% risk per trade
                max_daily_premium_pct=30.0,
                max_total_premium_pct=60.0,
                max_concurrent_positions=6
            )
        }
    ]

    all_results = []

    for cfg in configurations:
        logger.info("\n" + "=" * 80)
        logger.info(f"Testing: {cfg['name']}")
        logger.info("=" * 80)

        # Run backtest with corrected mechanics
        backtester = CorrectedPortfolioBacktester(cfg['config'])
        results = backtester.run_backtest(signals, ohlcv_df)

        # Store for comparison
        all_results.append({
            'name': cfg['name'],
            'config': cfg['config'],
            'results': results
        })

        # Display results
        stats = results['statistics']

        print(f"\n📊 PERFORMANCE METRICS for {cfg['name']}:")
        print(f"  Premium Allocation:")
        print(f"    - Premium per Trade: {cfg['config'].premium_per_trade_pct}% of capital")
        print(f"    - Max Daily Premium: {cfg['config'].max_daily_premium_pct}%")
        print(f"    - Max Total Premium: {cfg['config'].max_total_premium_pct}%")

        print(f"\n  Returns (CORRECTED):")
        print(f"    - Total Net P&L: {stats['total_net_pnl_eth']:.4f} ETH")
        print(f"    - Total Return: {stats['total_return_pct']:.2f}%")
        print(f"    - Simple APR: {stats['simple_apr']:.2f}% (on total capital)")
        print(f"    - Premium-Efficient APR: {stats['premium_efficient_apr']:.2f}% (on premium deployed)")

        print(f"\n  Trading Performance:")
        print(f"    - Total Trades: {stats['total_trades']}")
        print(f"    - Win Rate: {stats['win_rate_pct']:.1f}%")
        print(f"    - Wins: {stats['winning_trades']} / Losses: {stats['losing_trades']}")

        print(f"\n  Premium Metrics (KEY DIFFERENCE):")
        print(f"    - Total Premium Paid: {stats['total_premium_paid_eth']:.4f} ETH")
        print(f"    - Total Payout Received: {stats['total_payout_received_eth']:.4f} ETH")
        print(f"    - Return on Premium: {stats['return_on_premium_pct']:.1f}%")
        print(f"    - Avg Premium Deployed: {stats['avg_premium_deployed_pct']:.1f}% of capital")
        print(f"    - Max Premium Deployed: {stats['max_premium_deployed_pct']:.1f}% of capital")

        print(f"\n  Exposure Metrics:")
        print(f"    - Avg Nominal Exposure: {stats['avg_nominal_exposure_eth']:.2f} ETH")
        print(f"    - This is {stats['avg_nominal_exposure_eth']/cfg['config'].initial_capital_eth*100:.1f}% of capital in NOMINAL (not at risk)")

        print(f"\n  Risk Metrics:")
        print(f"    - Max Drawdown: {stats['max_drawdown_pct']:.1f}%")
        print(f"    - Sharpe Ratio: {stats['sharpe_ratio']:.2f}")

        # Show first few trades for the moderate config
        if cfg['name'].startswith("Moderate") and results['trade_logs']:
            print("\n📝 FIRST 3 TRADES (Corrected Mechanics):")
            for i, trade in enumerate(results['trade_logs'][:3], 1):
                print(f"\nTrade #{i}:")
                print(f"  Instrument: {trade['instrument']} {trade['type']}")
                print(f"  Entry: {trade['entry_time'][:10]} @ ${trade['entry_price']:.2f}")
                print(f"  Nominal Exposure: {trade['nominal_eth']:.3f} ETH")
                print(f"  Premium Paid: {trade['premium_paid_eth']:.4f} ETH ({trade['premium_paid_pct']:.2f}% of capital)")
                if trade['exit_time']:
                    print(f"  Exit: {trade['exit_time'][:10]} @ ${trade['exit_price']:.2f}")
                    print(f"  Price Move: {trade['price_move_pct']:.2f}% (capped at {trade['capped_move_pct']:.2f}%)")
                    print(f"  Payout: {trade['payout_eth']:.4f} ETH")
                    print(f"  Net P&L: {trade['net_pnl_eth']:.4f} ETH")
                    print(f"  Return on Premium: {trade['return_on_premium_pct']:.1f}%")
                    print(f"  Result: {'WIN' if trade['win'] else 'LOSS'}")

    # Summary comparison
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY - OLD VS CORRECTED MECHANICS")
    print("=" * 80)

    print("\n🔍 KEY INSIGHTS:")
    print("\n1. CAPITAL AT RISK:")
    print("   OLD: Confused nominal with position size")
    print("   CORRECTED: Only premium is at risk (2.2-2.8% per trade)")

    print("\n2. LEVERAGE:")
    print("   OLD: Thought 5% position = 5% of capital")
    print("   CORRECTED: 5% premium budget = ~180% nominal exposure (5%/2.8%)")

    print("\n3. APR CALCULATION:")
    print("   OLD: Incorrectly calculated based on mixed concepts")
    print("   CORRECTED: Two clear metrics:")
    print("     - Simple APR: Return on total capital")
    print("     - Premium-Efficient APR: Return on premium deployed")

    print("\n4. RISK MANAGEMENT:")
    print("   OLD: Limited positions due to capital confusion")
    print("   CORRECTED: Can have many positions with small premium each")

    # Show instrument statistics
    print("\n📊 INSTRUMENT USAGE (Moderate Config):")
    moderate_stats = all_results[1]['results']['statistics']['instrument_stats']
    for instrument, stats in moderate_stats.items():
        print(f"\n  {instrument}:")
        print(f"    - Trades: {stats['count']}")
        print(f"    - Win Rate: {stats['win_rate']:.1f}%")
        print(f"    - Total Premium: {stats['total_premium_eth']:.4f} ETH")
        print(f"    - Total P&L: {stats['total_pnl_eth']:.4f} ETH")
        print(f"    - Avg Return on Premium: {stats['avg_return_on_premium']:.1f}%")


if __name__ == "__main__":
    main()