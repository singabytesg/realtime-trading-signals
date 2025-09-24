"""
Example usage of Deribit Data Fetcher for Strategy Testing
"""

from deribit_data_fetcher import DeribitDataFetcher
import pandas as pd
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fetch_single_dataset():
    """
    Example: Fetch a single dataset
    """
    print("=" * 60)
    print("FETCHING SINGLE DATASET")
    print("=" * 60)

    fetcher = DeribitDataFetcher()

    # Fetch 30-minute candles for last 30 days
    df = fetcher.get_ohlcv_data(
        instrument="ETH-PERPETUAL",
        timeframe="30m",
        lookback_days=30
    )

    print(f"Fetched {len(df)} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print("\nFirst 5 rows:")
    print(df.head())

    return df


def fetch_multiple_datasets_custom():
    """
    Example: Fetch multiple datasets with custom configuration
    """
    print("\n" + "=" * 60)
    print("FETCHING MULTIPLE DATASETS - CUSTOM CONFIG")
    print("=" * 60)

    fetcher = DeribitDataFetcher()

    # Custom configurations for specific testing needs
    custom_configs = [
        # Short-term scalping data
        {"timeframe": "5m", "lookback_days": 7, "name": "5min_7days"},
        {"timeframe": "15m", "lookback_days": 14, "name": "15min_14days"},

        # Medium-term swing trading
        {"timeframe": "1h", "lookback_days": 45, "name": "1hour_45days"},
        {"timeframe": "4h", "lookback_days": 60, "name": "4hour_60days"},

        # Long-term position trading
        {"timeframe": "1D", "lookback_days": 120, "name": "1day_120days"},
    ]

    datasets = fetcher.fetch_multiple_datasets(
        instrument="ETH-PERPETUAL",
        configurations=custom_configs
    )

    # Display summary
    print(f"\nFetched {len(datasets)} datasets:")
    for name, df in datasets.items():
        print(f"  {name}: {len(df)} candles")

    return datasets


def fetch_and_save_all():
    """
    Example: Fetch comprehensive datasets and save to files
    """
    print("\n" + "=" * 60)
    print("FETCHING AND SAVING COMPREHENSIVE DATASETS")
    print("=" * 60)

    fetcher = DeribitDataFetcher()

    # Comprehensive configuration for strategy development
    comprehensive_configs = [
        # 30-day datasets for short-term strategies
        {"timeframe": "15m", "lookback_days": 30, "name": "15min_30days"},
        {"timeframe": "30m", "lookback_days": 30, "name": "30min_30days"},
        {"timeframe": "1h", "lookback_days": 30, "name": "1hour_30days"},

        # 60-day datasets for medium-term strategies
        {"timeframe": "30m", "lookback_days": 60, "name": "30min_60days"},
        {"timeframe": "1h", "lookback_days": 60, "name": "1hour_60days"},
        {"timeframe": "4h", "lookback_days": 60, "name": "4hour_60days"},

        # 90-day datasets for longer-term strategies
        {"timeframe": "4h", "lookback_days": 90, "name": "4hour_90days"},
        {"timeframe": "12h", "lookback_days": 90, "name": "12hour_90days"},
        {"timeframe": "1D", "lookback_days": 90, "name": "1day_90days"},
    ]

    # Fetch all datasets
    datasets = fetcher.fetch_multiple_datasets(
        instrument="ETH-PERPETUAL",
        configurations=comprehensive_configs
    )

    # Save to JSON files
    saved_files = fetcher.save_datasets_to_json(datasets, output_dir="../data")

    print(f"\n✅ Saved {len(saved_files)} files to ../data/")

    return saved_files


def test_data_quality():
    """
    Example: Test data quality and completeness
    """
    print("\n" + "=" * 60)
    print("TESTING DATA QUALITY")
    print("=" * 60)

    fetcher = DeribitDataFetcher()

    # Fetch sample data
    df = fetcher.get_ohlcv_data(
        instrument="ETH-PERPETUAL",
        timeframe="1h",
        lookback_days=7
    )

    # Quality checks
    print("Data Quality Report:")
    print(f"  Total records: {len(df)}")
    print(f"  Missing values: {df.isnull().sum().sum()}")
    print(f"  Duplicate timestamps: {df['timestamp'].duplicated().sum()}")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Price range: ${df['low'].min():.2f} to ${df['high'].max():.2f}")
    print(f"  Average volume: {df['volume'].mean():.2f}")

    # Check for anomalies
    price_changes = df['close'].pct_change().abs()
    large_moves = price_changes > 0.05  # More than 5% move
    print(f"  Large price moves (>5%): {large_moves.sum()}")

    if large_moves.any():
        print("  Largest moves:")
        large_move_indices = df[large_moves].index
        for idx in large_move_indices[:3]:  # Show first 3
            prev_close = df.loc[idx-1, 'close'] if idx > 0 else df.loc[idx, 'open']
            curr_close = df.loc[idx, 'close']
            change_pct = ((curr_close - prev_close) / prev_close) * 100
            timestamp = df.loc[idx, 'timestamp']
            print(f"    {timestamp}: {change_pct:+.2f}% (${prev_close:.2f} → ${curr_close:.2f})")


def load_and_test_saved_data():
    """
    Example: Load saved data and verify it works with strategy system
    """
    print("\n" + "=" * 60)
    print("LOADING AND TESTING SAVED DATA")
    print("=" * 60)

    try:
        # Load saved data (assuming it exists)
        with open("../data/eth_1hour_30days.json", 'r') as f:
            data = json.load(f)

        # Convert to DataFrame (same format as strategy system)
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

        print(f"✅ Successfully loaded {len(df)} records")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print("\nSample data:")
        print(df.head(3))

        # This data is now ready for strategy testing!
        print("\n🎯 Data is ready for strategy backtesting!")

    except FileNotFoundError:
        print("❌ No saved data found. Run fetch_and_save_all() first.")
    except Exception as e:
        print(f"❌ Error loading data: {e}")


if __name__ == "__main__":
    """
    Run all examples
    """
    print("🚀 Deribit Data Fetcher Examples")
    print("=" * 60)

    # Example 1: Single dataset
    try:
        fetch_single_dataset()
    except Exception as e:
        logger.error(f"Single dataset fetch failed: {e}")

    # Example 2: Multiple custom datasets
    try:
        fetch_multiple_datasets_custom()
    except Exception as e:
        logger.error(f"Multiple dataset fetch failed: {e}")

    # Example 3: Comprehensive fetch and save
    try:
        saved_files = fetch_and_save_all()
        print(f"\n📁 Files created:")
        for file in saved_files:
            print(f"   - {file}")
    except Exception as e:
        logger.error(f"Comprehensive fetch failed: {e}")

    # Example 4: Data quality testing
    try:
        test_data_quality()
    except Exception as e:
        logger.error(f"Data quality test failed: {e}")

    # Example 5: Load and test saved data
    try:
        load_and_test_saved_data()
    except Exception as e:
        logger.error(f"Saved data test failed: {e}")

    print("\n🎉 Examples complete!")
    print("\nNext steps:")
    print("1. Use the saved JSON files with your strategy system")
    print("2. Load them using the format shown in load_and_test_saved_data()")
    print("3. Run backtests with portfolio_corrected_options.py")