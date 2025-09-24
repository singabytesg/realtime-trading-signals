"""
Deribit API Data Fetcher for Strategy Testing

Fetches OHLCV data from Deribit API for different timeframes and lookback periods.
Supports: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1D
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeribitDataFetcher:
    """
    Fetches historical OHLCV data from Deribit API
    """

    def __init__(self):
        self.base_url = "https://www.deribit.com/api/v2"
        self.session = requests.Session()

        # Deribit API rate limits: 20 requests per second
        self.request_delay = 0.05  # 50ms between requests

        # Timeframe mapping (Deribit format)
        self.timeframes = {
            "1m": "1",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "2h": "120",
            # "4h": "240",  # Temporarily disabled - API issue
            "6h": "360",
            "12h": "720",
            "1D": "1D"
        }

    def get_ohlcv_data(self,
                       instrument: str = "ETH-PERPETUAL",
                       timeframe: str = "30m",
                       lookback_days: int = 30) -> pd.DataFrame:
        """
        Fetch OHLCV data from Deribit

        Args:
            instrument: Trading instrument (e.g., "ETH-PERPETUAL", "BTC-PERPETUAL")
            timeframe: Timeframe ("1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1D")
            lookback_days: Number of days to look back

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """

        if timeframe not in self.timeframes:
            raise ValueError(f"Unsupported timeframe: {timeframe}. Supported: {list(self.timeframes.keys())}")

        # Calculate timestamps
        end_timestamp = int(datetime.now().timestamp() * 1000)
        start_timestamp = int((datetime.now() - timedelta(days=lookback_days)).timestamp() * 1000)

        logger.info(f"Fetching {instrument} {timeframe} data for {lookback_days} days...")

        # Deribit API endpoint
        url = f"{self.base_url}/public/get_tradingview_chart_data"

        params = {
            "instrument_name": instrument,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "resolution": self.timeframes[timeframe]
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if "result" not in data:
                raise ValueError(f"No result in API response: {data}")

            result = data["result"]

            # Convert to DataFrame
            df = pd.DataFrame({
                "timestamp": pd.to_datetime(result["ticks"], unit="ms"),
                "open": result["open"],
                "high": result["high"],
                "low": result["low"],
                "close": result["close"],
                "volume": result["volume"]
            })

            # Sort by timestamp
            df = df.sort_values("timestamp").reset_index(drop=True)

            logger.info(f"Successfully fetched {len(df)} candles")
            return df

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Data processing failed: {e}")
            raise

        finally:
            # Rate limiting
            time.sleep(self.request_delay)

    def fetch_multiple_datasets(self,
                                 instrument: str = "ETH-PERPETUAL",
                                 configurations: List[Dict] = None) -> Dict[str, pd.DataFrame]:
        """
        Fetch multiple datasets with different timeframes and lookback periods

        Args:
            instrument: Trading instrument
            configurations: List of {"timeframe": str, "lookback_days": int, "name": str}

        Returns:
            Dictionary of {name: DataFrame}
        """

        if configurations is None:
            # Default configurations for strategy testing
            configurations = [
                # 30-day datasets
                {"timeframe": "15m", "lookback_days": 30, "name": "15min_30days"},
                {"timeframe": "30m", "lookback_days": 30, "name": "30min_30days"},
                {"timeframe": "1h", "lookback_days": 30, "name": "1hour_30days"},
                {"timeframe": "6h", "lookback_days": 30, "name": "6hour_30days"},

                # 60-day datasets
                {"timeframe": "30m", "lookback_days": 60, "name": "30min_60days"},
                {"timeframe": "1h", "lookback_days": 60, "name": "1hour_60days"},
                {"timeframe": "6h", "lookback_days": 60, "name": "6hour_60days"},
                {"timeframe": "1D", "lookback_days": 60, "name": "1day_60days"},

                # 90-day datasets
                {"timeframe": "1h", "lookback_days": 90, "name": "1hour_90days"},
                {"timeframe": "6h", "lookback_days": 90, "name": "6hour_90days"},
                {"timeframe": "12h", "lookback_days": 90, "name": "12hour_90days"},
                {"timeframe": "1D", "lookback_days": 90, "name": "1day_90days"},
            ]

        datasets = {}

        for config in configurations:
            try:
                logger.info(f"Fetching {config['name']}...")
                df = self.get_ohlcv_data(
                    instrument=instrument,
                    timeframe=config["timeframe"],
                    lookback_days=config["lookback_days"]
                )
                datasets[config["name"]] = df

                # Progress update
                logger.info(f"✅ {config['name']}: {len(df)} candles")

            except Exception as e:
                logger.error(f"❌ Failed to fetch {config['name']}: {e}")
                continue

        return datasets

    def save_datasets_to_json(self,
                              datasets: Dict[str, pd.DataFrame],
                              output_dir: str = "../data") -> List[str]:
        """
        Save datasets to JSON files in the format expected by the strategy system

        Args:
            datasets: Dictionary of {name: DataFrame}
            output_dir: Output directory

        Returns:
            List of saved file paths
        """

        os.makedirs(output_dir, exist_ok=True)
        saved_files = []

        for name, df in datasets.items():
            # Convert to the format expected by strategy system
            ohlcv_data = []
            for _, row in df.iterrows():
                ohlcv_data.append({
                    "Date": row["timestamp"].isoformat(),
                    "Open": float(row["open"]),
                    "High": float(row["high"]),
                    "Low": float(row["low"]),
                    "Close": float(row["close"]),
                    "Volume": float(row["volume"])
                })

            # Create full dataset structure
            dataset = {
                "ohlcv": ohlcv_data,
                "asset": "ETH",
                "timeframe": name.split("_")[0],
                "lookback_days": int(name.split("_")[1].replace("days", "")),
                "total_records": len(ohlcv_data),
                "data_source": "deribit",
                "fetched_at": datetime.now().isoformat()
            }

            # Save to file
            filename = f"{output_dir}/eth_{name}.json"
            with open(filename, 'w') as f:
                json.dump(dataset, f, indent=2)

            saved_files.append(filename)
            logger.info(f"💾 Saved {len(ohlcv_data)} records to {filename}")

        return saved_files


def main():
    """
    Main function to fetch all datasets for strategy testing
    """

    logger.info("🚀 Starting Deribit data fetching...")

    # Initialize fetcher
    fetcher = DeribitDataFetcher()

    # Custom configurations - you can modify these
    configurations = [
        # High-frequency trading datasets (30 days)
        {"timeframe": "5m", "lookback_days": 30, "name": "5min_30days"},
        {"timeframe": "15m", "lookback_days": 30, "name": "15min_30days"},
        {"timeframe": "30m", "lookback_days": 30, "name": "30min_30days"},

        # Intraday datasets (60 days)
        {"timeframe": "30m", "lookback_days": 60, "name": "30min_60days"},
        {"timeframe": "1h", "lookback_days": 60, "name": "1hour_60days"},
        {"timeframe": "2h", "lookback_days": 60, "name": "2hour_60days"},
        {"timeframe": "6h", "lookback_days": 60, "name": "6hour_60days"},

        # Swing trading datasets (90 days)
        {"timeframe": "6h", "lookback_days": 90, "name": "6hour_90days"},
        {"timeframe": "12h", "lookback_days": 90, "name": "12hour_90days"},
        {"timeframe": "1D", "lookback_days": 90, "name": "1day_90days"},

        # Long-term datasets (180 days)
        {"timeframe": "12h", "lookback_days": 180, "name": "12hour_180days"},
        {"timeframe": "1D", "lookback_days": 180, "name": "1day_180days"},
    ]

    # Fetch all datasets
    datasets = fetcher.fetch_multiple_datasets(
        instrument="ETH-PERPETUAL",
        configurations=configurations
    )

    # Save to JSON files
    saved_files = fetcher.save_datasets_to_json(datasets, output_dir="../data")

    # Summary
    logger.info("🎉 Data fetching complete!")
    logger.info(f"📊 Datasets created: {len(saved_files)}")
    logger.info(f"📁 Files saved in: data/")

    for filename in saved_files:
        file_size = os.path.getsize(filename) / 1024  # KB
        logger.info(f"  - {os.path.basename(filename)} ({file_size:.1f} KB)")

    # Create a summary file
    summary = {
        "fetch_completed_at": datetime.now().isoformat(),
        "total_datasets": len(saved_files),
        "datasets": []
    }

    for name, df in datasets.items():
        summary["datasets"].append({
            "name": name,
            "filename": f"eth_{name}.json",
            "records": len(df),
            "date_range": {
                "start": df["timestamp"].min().isoformat(),
                "end": df["timestamp"].max().isoformat()
            },
            "timeframe": name.split("_")[0],
            "lookback_days": int(name.split("_")[1].replace("days", ""))
        })

    with open("../data/fetch_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info("📋 Summary saved to ../data/fetch_summary.json")


if __name__ == "__main__":
    main()