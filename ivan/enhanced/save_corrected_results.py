"""
Save the corrected trading results to JSON files for analysis
"""

import json
import sys
import os
import logging
import pandas as pd
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from portfolio_corrected_options import *
from portfolio_enhanced_laa_eva import PortfolioAwareDslExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def save_results_to_json(results: Dict[str, Any], config_name: str, config: PortfolioConfig):
    """Save results to a JSON file with all trade details"""

    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"corrected_results_{config_name.lower().replace(' ', '_')}_{timestamp}.json"

    # Convert numpy types to Python types for JSON serialization
    def convert_numpy(obj):
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, dict):
            return {key: convert_numpy(val) for key, val in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(val) for val in obj]
        else:
            return obj

    # Prepare output data
    output = {
        "configuration": {
            "name": config_name,
            "initial_capital_eth": config.initial_capital_eth,
            "premium_per_trade_pct": config.premium_per_trade_pct,
            "max_daily_premium_pct": config.max_daily_premium_pct,
            "max_total_premium_pct": config.max_total_premium_pct,
            "max_concurrent_positions": config.max_concurrent_positions,
            "max_drawdown_pct": config.max_drawdown_pct
        },
        "summary_statistics": convert_numpy(results['statistics']),
        "trade_logs": convert_numpy(results['trade_logs']),
        "capital_curve": convert_numpy(results.get('capital_curve', []))
    }

    # Save to file
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    logger.info(f"Results saved to {filename}")
    return filename


def main():
    """Run the winning strategy and save all results"""

    logger.info("=" * 80)
    logger.info("RUNNING CORRECTED SYSTEM AND SAVING RESULTS")
    logger.info("=" * 80)

    # Load market data
    try:
        with open('/Users/ivanhmac/github/pokpok/Archive/pokpok_agents/ivan/eth_30min_30days.json', 'r') as f:
            data = json.load(f)
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
        return

    # Use the EXACT winning parameters
    winning_strategy = {
        "strategy_logic_dsl": {
            "dsl_version": "2.0",
            "description": "Enhanced BEAR_TREND_LOW_VOL strategy",
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

    # Generate signals
    logger.info("\nGenerating signals...")
    executor = PortfolioAwareDslExecutor(
        winning_strategy['strategy_logic_dsl'],
        str(uuid.uuid4())
    )
    signals_raw = executor.generate_signals(ohlcv_df)

    # Convert to corrected Signal format
    signals = []
    for sig in signals_raw:
        if sig.signal != 0:
            strength = sig.signal * 7

            if hasattr(sig.timestamp, 'isoformat'):
                timestamp_str = sig.timestamp.isoformat()
            elif hasattr(sig.timestamp, 'strftime'):
                timestamp_str = sig.timestamp.strftime('%Y-%m-%dT%H:%M:%S')
            else:
                timestamp_str = pd.Timestamp(sig.timestamp).isoformat()

            signals.append(Signal(
                timestamp=timestamp_str,
                signal=sig.signal,
                strength=strength,
                instrument=sig.instrument_type,
                reason=sig.rule_triggered,
                entry_price=sig.last_close
            ))

    logger.info(f"Generated {len(signals)} active signals")

    # Test configurations and save results
    configurations = [
        {
            "name": "Conservative_2pct",
            "config": PortfolioConfig(
                initial_capital_eth=10.0,
                premium_per_trade_pct=2.0,
                max_daily_premium_pct=10.0,
                max_total_premium_pct=20.0,
                max_concurrent_positions=10
            )
        },
        {
            "name": "Moderate_5pct",
            "config": PortfolioConfig(
                initial_capital_eth=10.0,
                premium_per_trade_pct=5.0,
                max_daily_premium_pct=20.0,
                max_total_premium_pct=40.0,
                max_concurrent_positions=8
            )
        },
        {
            "name": "Aggressive_10pct",
            "config": PortfolioConfig(
                initial_capital_eth=10.0,
                premium_per_trade_pct=10.0,
                max_daily_premium_pct=30.0,
                max_total_premium_pct=60.0,
                max_concurrent_positions=6
            )
        }
    ]

    saved_files = []

    for cfg in configurations:
        logger.info(f"\nRunning backtest for {cfg['name']}...")

        # Run backtest
        backtester = CorrectedPortfolioBacktester(cfg['config'])
        results = backtester.run_backtest(signals, ohlcv_df)

        # Save results
        filename = save_results_to_json(results, cfg['name'], cfg['config'])
        saved_files.append(filename)

        # Display summary
        stats = results['statistics']
        logger.info(f"  Total Trades: {stats['total_trades']}")
        logger.info(f"  Win Rate: {stats['win_rate_pct']:.1f}%")
        logger.info(f"  Total Return: {stats['total_return_pct']:.2f}%")
        logger.info(f"  Simple APR: {stats['simple_apr']:.2f}%")
        logger.info(f"  Premium-Efficient APR: {stats['premium_efficient_apr']:.2f}%")

    # Create a master summary file
    # Get the date range properly
    if 'timestamp' in ohlcv_df.columns:
        start_date = pd.to_datetime(ohlcv_df['timestamp'].iloc[0])
        end_date = pd.to_datetime(ohlcv_df['timestamp'].iloc[-1])
    else:
        # Timestamp might be in index
        start_date = pd.to_datetime(ohlcv_df.index[0])
        end_date = pd.to_datetime(ohlcv_df.index[-1])

    master_summary = {
        "generated_at": datetime.now().isoformat(),
        "market_data": {
            "start_date": start_date.isoformat() if hasattr(start_date, 'isoformat') else str(start_date),
            "end_date": end_date.isoformat() if hasattr(end_date, 'isoformat') else str(end_date),
            "total_periods": len(ohlcv_df),
            "asset": "ETH"
        },
        "strategy": {
            "name": "Winning_77pct_Strategy",
            "signals_generated": len(signals)
        },
        "result_files": saved_files
    }

    with open("corrected_results_master_summary.json", 'w') as f:
        json.dump(master_summary, f, indent=2)

    logger.info("\n" + "=" * 80)
    logger.info("ALL RESULTS SAVED")
    logger.info("=" * 80)
    logger.info(f"Individual results: {', '.join(saved_files)}")
    logger.info("Master summary: corrected_results_master_summary.json")


if __name__ == "__main__":
    main()