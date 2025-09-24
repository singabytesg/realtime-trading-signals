#!/usr/bin/env python3
"""
Simple DPA Setup: Get Last 30 Days ETH Data (30min timeframe)
This bypasses the AI and calls the market data provider directly
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath('.'))

try:
    from src.quant.market_data import get_ohlcv
    from src.core.enums import Asset, Timeframe

    def fetch_eth_data():
        print("🔄 Fetching ETH data (30min timeframe, last 30 days)...")
        print("=" * 60)

        try:
            # Direct call to get_ohlcv (bypasses AI)
            df = get_ohlcv(
                asset="eth",  # lowercase for the market data function
                timeframe="30m",
                duration_in_days=30
            )

            if df.empty:
                print("❌ No data returned")
                return None

            print(f"✅ Successfully fetched {len(df)} records")
            print(f"📅 Date range: {df.index.min()} to {df.index.max()}")

            # Show sample data
            print(f"\n📊 Sample Data (First 5 records):")
            print("-" * 60)
            print(df.head().to_string())

            # Show summary stats
            print(f"\n📈 Price Summary:")
            print(f"  First Close: ${df['Close'].iloc[0]:,.2f}")
            print(f"  Last Close:  ${df['Close'].iloc[-1]:,.2f}")
            price_change = df['Close'].iloc[-1] - df['Close'].iloc[0]
            price_change_pct = (price_change / df['Close'].iloc[0]) * 100
            print(f"  30-day Change: ${price_change:+,.2f} ({price_change_pct:+.2f}%)")
            print(f"  Highest: ${df['High'].max():,.2f}")
            print(f"  Lowest:  ${df['Low'].min():,.2f}")
            print(f"  Avg Volume: {df['Volume'].mean():,.0f}")

            # Save to CSV
            csv_file = "eth_30min_30days.csv"
            df.to_csv(csv_file)
            print(f"\n💾 Data saved to: {csv_file}")

            # Convert to DPA format (list of dicts)
            records = df.reset_index().to_dict(orient='records')

            # Show DPA format sample
            print(f"\n🤖 DPA Format (First 2 records):")
            print("-" * 60)
            import json
            print(json.dumps(records[:2], indent=2, default=str))

            return df, records

        except Exception as e:
            print(f"❌ Error fetching data: {e}")
            return None, None

    if __name__ == "__main__":
        df, records = fetch_eth_data()

        if df is not None:
            print(f"\n🎉 Success! You now have:")
            print(f"  • {len(records)} ETH 30-min candles")
            print(f"  • Last 30 days of real market data")
            print(f"  • Data from Deribit public API")
            print(f"  • CSV file: eth_30min_30days.csv")

            print(f"\n💡 Next steps:")
            print(f"  • Use the DataFrame for analysis: df")
            print(f"  • Use the records for DPA format: records")
            print(f"  • No API keys were needed!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"\n💡 Dependencies needed:")
    print(f"  pip3 install pandas requests python-dotenv")
    print(f"\n📁 Make sure you're in the project root directory:")
    print(f"  cd /Users/ivanhmac/github/pokpok/Archive/pokpok_agents")

except Exception as e:
    print(f"❌ Error: {e}")
    print(f"\n💡 Try running from project root with:")
    print(f"  PYTHONPATH=. python3 setup_dpa_eth.py")