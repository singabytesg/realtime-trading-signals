"""
Quick test to verify Deribit API connectivity and fetch sample data
"""

import requests
import json
from datetime import datetime, timedelta
import pandas as pd


def test_deribit_connection():
    """Test basic Deribit API connectivity"""
    print("🔗 Testing Deribit API connection...")

    try:
        # Test with a simple chart data request instead
        end_timestamp = int(datetime.now().timestamp() * 1000)
        start_timestamp = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)

        url = "https://www.deribit.com/api/v2/public/get_tradingview_chart_data"
        params = {
            "instrument_name": "ETH-PERPETUAL",
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "resolution": "60"  # 1 hour
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        if "result" in data and data["result"].get("ticks"):
            candles = len(data["result"]["ticks"])
            print(f"✅ API connection successful!")
            print(f"📊 Retrieved {candles} candles for ETH-PERPETUAL")
            return True
        else:
            print("❌ Unexpected API response format")
            print(f"Response: {data}")
            return False

    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False


def test_sample_data_fetch():
    """Fetch a small sample of data to test the format"""
    print("\n📈 Testing sample data fetch...")

    try:
        # Get last 3 days of 1-hour ETH data
        end_timestamp = int(datetime.now().timestamp() * 1000)
        start_timestamp = int((datetime.now() - timedelta(days=3)).timestamp() * 1000)

        url = "https://www.deribit.com/api/v2/public/get_tradingview_chart_data"
        params = {
            "instrument_name": "ETH-PERPETUAL",
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "resolution": "60"  # 1 hour
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        if "result" in data:
            result = data["result"]

            # Convert to DataFrame for analysis
            df = pd.DataFrame({
                "timestamp": pd.to_datetime(result["ticks"], unit="ms"),
                "open": result["open"],
                "high": result["high"],
                "low": result["low"],
                "close": result["close"],
                "volume": result["volume"]
            })

            print(f"✅ Successfully fetched {len(df)} candles")
            print(f"📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            print(f"💰 Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
            print(f"📊 Avg volume: {df['volume'].mean():.0f}")

            print("\n📋 Sample data:")
            print(df.head(3).to_string(index=False))

            return True

        else:
            print("❌ No result in API response")
            print(f"Response: {data}")
            return False

    except Exception as e:
        print(f"❌ Sample data fetch failed: {e}")
        return False


def test_different_timeframes():
    """Test different timeframes to see what's available"""
    print("\n⏰ Testing different timeframes...")

    timeframes = {
        "1m": "1",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "4h": "240",
        "1D": "1D"
    }

    # Get last 2 days for testing
    end_timestamp = int(datetime.now().timestamp() * 1000)
    start_timestamp = int((datetime.now() - timedelta(days=2)).timestamp() * 1000)

    for name, resolution in timeframes.items():
        try:
            url = "https://www.deribit.com/api/v2/public/get_tradingview_chart_data"
            params = {
                "instrument_name": "ETH-PERPETUAL",
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
                "resolution": resolution
            }

            response = requests.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if "result" in data and data["result"]["ticks"]:
                candle_count = len(data["result"]["ticks"])
                print(f"✅ {name:4s}: {candle_count:3d} candles")
            else:
                print(f"❌ {name:4s}: No data")

        except Exception as e:
            print(f"❌ {name:4s}: Error - {e}")


if __name__ == "__main__":
    print("🧪 Deribit API Test Suite")
    print("=" * 50)

    # Run tests
    connection_ok = test_deribit_connection()

    if connection_ok:
        data_ok = test_sample_data_fetch()
        if data_ok:
            test_different_timeframes()

    print("\n" + "=" * 50)
    if connection_ok:
        print("🎉 Deribit API is working!")
        print("\nNext steps:")
        print("1. Run: python deribit_data_fetcher.py")
        print("2. Or run: python fetch_data_example.py")
        print("3. Use the generated JSON files for strategy testing")
    else:
        print("❌ Deribit API test failed. Check internet connection.")