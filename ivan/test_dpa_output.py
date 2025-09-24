#!/usr/bin/env python3
"""
Simple test script to demonstrate DPA output format
This shows what the DPA agent would return when fetching OHLCV data
"""

from datetime import datetime, timedelta
import json

# Mock OHLCV data structure that DPA would return
def generate_mock_dpa_output():
    """Generate sample OHLCV data matching DPA's output format"""

    # Simulate 30 days of ETH daily data
    base_date = datetime.now() - timedelta(days=30)
    base_price = 2200.0

    ohlcv_records = []

    for i in range(30):
        # Simple mock price movement
        date = base_date + timedelta(days=i)

        # Add some realistic price variation
        open_price = base_price + (i * 10) + (i % 3 * 15)
        high_price = open_price + (20 + i % 50)
        low_price = open_price - (15 + i % 40)
        close_price = open_price + (i % 7 - 3) * 25
        volume = 150000 + (i * 1000) + (i % 5 * 20000)

        record = {
            "Date": date.isoformat() + "Z",
            "Open": round(open_price, 2),
            "High": round(high_price, 2),
            "Low": round(low_price, 2),
            "Close": round(close_price, 2),
            "Volume": round(volume, 2)
        }

        ohlcv_records.append(record)

    # Full DPA response structure
    dpa_response = {
        "ohlcv": ohlcv_records,
        "asset": "ETH",
        "timeframe": "DAY_1",
        "start_dt": None,
        "end_dt": None,
        "lookback_days": 30
    }

    return dpa_response

def print_dpa_analysis():
    """Print DPA output with analysis"""

    print("=" * 70)
    print("DPA (Data Provisioning Agent) Output Example")
    print("=" * 70)

    # Generate mock data
    response = generate_mock_dpa_output()

    print(f"\n📊 Market Data Request:")
    print(f"   Asset: {response['asset']}")
    print(f"   Timeframe: {response['timeframe']}")
    print(f"   Lookback: {response['lookback_days']} days")
    print(f"   Total Records: {len(response['ohlcv'])}")

    print(f"\n💾 Storage Location:")
    print(f"   Team Session: agent.team_session_state['ohlcv_data']")
    print(f"   SQLite DB: tmp/agent.db")

    print(f"\n🔄 Data Flow:")
    print(f"   DPA → team_session_state → MRCA/EVA/LAA agents")

    print(f"\n📋 Sample OHLCV Records (First 5):")
    print("-" * 70)

    for i, record in enumerate(response['ohlcv'][:5]):
        print(f"Record {i+1}:")
        print(f"  Date: {record['Date']}")
        print(f"  Open: ${record['Open']:,.2f}")
        print(f"  High: ${record['High']:,.2f}")
        print(f"  Low: ${record['Low']:,.2f}")
        print(f"  Close: ${record['Close']:,.2f}")
        print(f"  Volume: {record['Volume']:,.2f}")
        print()

    print(f"📈 Price Analysis:")
    first_close = response['ohlcv'][0]['Close']
    last_close = response['ohlcv'][-1]['Close']
    change = last_close - first_close
    change_pct = (change / first_close) * 100

    print(f"   30-day Price Change: ${change:+,.2f} ({change_pct:+.2f}%)")
    print(f"   First Close: ${first_close:,.2f}")
    print(f"   Last Close: ${last_close:,.2f}")

    # Show volume stats
    volumes = [r['Volume'] for r in response['ohlcv']]
    avg_volume = sum(volumes) / len(volumes)
    print(f"   Average Volume: {avg_volume:,.0f}")

    print(f"\n🤖 Who Uses This Data:")
    print(f"   • MRCA - Technical analysis (RSI, MACD, Bollinger Bands)")
    print(f"   • EVA - Strategy backtesting and evaluation")
    print(f"   • LAA - Learning and adapting strategies")
    print(f"   • MST - Market strategy development")
    print(f"   • MAT - Market analysis and regime detection")

    print(f"\n📋 JSON Output Sample:")
    print("-" * 70)
    # Show abbreviated JSON for readability
    sample_response = {
        "ohlcv": response['ohlcv'][:2],  # Just first 2 records
        "asset": response['asset'],
        "timeframe": response['timeframe'],
        "lookback_days": response['lookback_days']
    }
    print(json.dumps(sample_response, indent=2))
    print(f"... ({len(response['ohlcv'])-2} more records)")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    print_dpa_analysis()