#!/usr/bin/env python3
"""
Simple ETH Data Fetcher - No Dependencies
Fetches real ETH data directly from Deribit public API
"""

import requests
import json
import datetime
from typing import List, Dict, Any

def fetch_eth_30min_data():
    """Fetch last 30 days of ETH 30-minute data from Deribit"""

    print("🔄 Fetching ETH data from Deribit public API...")
    print("📊 Asset: ETH | Timeframe: 30min | Period: Last 30 days")
    print("=" * 70)

    # Calculate timestamps
    end_time = datetime.datetime.now(datetime.timezone.utc)
    start_time = end_time - datetime.timedelta(days=30)

    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)

    print(f"📅 Date Range: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')} UTC")

    # Deribit public API call
    instrument = "ETH-PERPETUAL"
    resolution = "30"  # 30 minutes
    url = f"https://www.deribit.com/api/v2/public/get_tradingview_chart_data"

    params = {
        'instrument_name': instrument,
        'resolution': resolution,
        'start_timestamp': start_ms,
        'end_timestamp': end_ms
    }

    try:
        print(f"🌐 Calling Deribit API...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        if 'result' not in data:
            print(f"❌ API Error: {data}")
            return None

        result = data['result']
        required_keys = ['ticks', 'open', 'high', 'low', 'close', 'volume']

        if not all(key in result for key in required_keys):
            print(f"❌ Missing data in API response")
            return None

        # Parse data
        timestamps = result['ticks']
        opens = result['open']
        highs = result['high']
        lows = result['low']
        closes = result['close']
        volumes = result['volume']

        if not timestamps:
            print(f"❌ No data returned from API")
            return None

        print(f"✅ Received {len(timestamps)} data points")

        # Convert to OHLCV records
        records = []
        for i in range(len(timestamps)):
            dt = datetime.datetime.fromtimestamp(timestamps[i] / 1000, tz=datetime.timezone.utc)
            record = {
                "Date": dt.isoformat(),
                "Open": float(opens[i]),
                "High": float(highs[i]),
                "Low": float(lows[i]),
                "Close": float(closes[i]),
                "Volume": float(volumes[i])
            }
            records.append(record)

        return records

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def analyze_data(records: List[Dict[str, Any]]):
    """Analyze the OHLCV data"""

    if not records:
        return

    print(f"\n📊 DATA ANALYSIS")
    print("=" * 70)

    first_record = records[0]
    last_record = records[-1]

    # Price analysis
    first_close = first_record['Close']
    last_close = last_record['Close']
    price_change = last_close - first_close
    price_change_pct = (price_change / first_close) * 100

    # Find highs/lows
    all_highs = [r['High'] for r in records]
    all_lows = [r['Low'] for r in records]
    all_volumes = [r['Volume'] for r in records]

    highest_price = max(all_highs)
    lowest_price = min(all_lows)
    avg_volume = sum(all_volumes) / len(all_volumes)

    print(f"📈 Price Summary:")
    print(f"  First Close: ${first_close:,.2f}")
    print(f"  Last Close:  ${last_close:,.2f}")
    print(f"  30-day Change: ${price_change:+,.2f} ({price_change_pct:+.2f}%)")
    print(f"  Highest: ${highest_price:,.2f}")
    print(f"  Lowest:  ${lowest_price:,.2f}")
    print(f"  Average Volume: {avg_volume:,.0f}")

    print(f"\n📅 Time Range:")
    print(f"  Start: {first_record['Date']}")
    print(f"  End:   {last_record['Date']}")

def save_data(records: List[Dict[str, Any]]):
    """Save data to JSON file"""

    filename = "eth_30min_30days.json"

    # Create DPA format
    dpa_response = {
        "ohlcv": records,
        "asset": "ETH",
        "timeframe": "30m",
        "lookback_days": 30,
        "total_records": len(records),
        "data_source": "Deribit Public API",
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    with open(filename, 'w') as f:
        json.dump(dpa_response, f, indent=2)

    print(f"\n💾 Data saved to: {filename}")
    return filename

def show_sample_data(records: List[Dict[str, Any]], count: int = 3):
    """Show sample records"""

    print(f"\n📋 Sample Data (First {count} records):")
    print("-" * 70)

    for i, record in enumerate(records[:count]):
        print(f"Record {i+1}:")
        print(f"  Date: {record['Date']}")
        print(f"  Open: ${record['Open']:,.2f}")
        print(f"  High: ${record['High']:,.2f}")
        print(f"  Low:  ${record['Low']:,.2f}")
        print(f"  Close: ${record['Close']:,.2f}")
        print(f"  Volume: {record['Volume']:,.0f}")
        print()

if __name__ == "__main__":
    print("🚀 ETH 30-Min Data Fetcher")
    print("=" * 70)

    # Fetch data
    records = fetch_eth_30min_data()

    if records:
        # Show analysis
        analyze_data(records)

        # Show sample
        show_sample_data(records)

        # Save data
        filename = save_data(records)

        print(f"\n🎉 SUCCESS!")
        print("=" * 70)
        print(f"✅ Fetched {len(records)} ETH 30-minute candles")
        print(f"✅ Last 30 days of real market data")
        print(f"✅ No API keys required (public data)")
        print(f"✅ Data saved to: {filename}")

        print(f"\n💡 This is exactly what DPA would provide!")
        print(f"📁 You can now use this data for:")
        print(f"   • Technical analysis")
        print(f"   • Strategy backtesting")
        print(f"   • Price trend analysis")
        print(f"   • Volume analysis")

    else:
        print(f"\n❌ Failed to fetch data")
        print(f"💡 Check your internet connection and try again")