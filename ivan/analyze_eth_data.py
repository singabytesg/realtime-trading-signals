#!/usr/bin/env python3
"""
Quick ETH Data Analysis
Shows what you can do with the fetched DPA data
"""

import json
from datetime import datetime
from typing import List, Dict, Any

def load_eth_data() -> Dict[str, Any]:
    """Load the ETH data from JSON file"""
    with open('eth_30min_30days.json', 'r') as f:
        return json.load(f)

def calculate_technical_indicators(records: List[Dict[str, Any]]):
    """Calculate basic technical indicators"""

    closes = [r['Close'] for r in records]

    # Simple Moving Averages
    def sma(data, period):
        if len(data) < period:
            return None
        return sum(data[-period:]) / period

    # Calculate SMAs
    sma_20 = sma(closes, 20)  # 20-period (10 hours)
    sma_50 = sma(closes, 50)  # 50-period (25 hours)
    sma_100 = sma(closes, 100) # 100-period (50 hours)

    # RSI calculation (simplified)
    def calculate_rsi(prices, period=14):
        if len(prices) < period + 1:
            return None

        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        if len(gains) < period:
            return None

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    rsi = calculate_rsi(closes)

    return {
        'sma_20': sma_20,
        'sma_50': sma_50,
        'sma_100': sma_100,
        'rsi': rsi,
        'current_price': closes[-1]
    }

def find_price_extremes(records: List[Dict[str, Any]]):
    """Find significant price movements"""

    # Find biggest moves
    price_changes = []
    for i in range(1, len(records)):
        prev_close = records[i-1]['Close']
        curr_close = records[i]['Close']
        change_pct = ((curr_close - prev_close) / prev_close) * 100

        price_changes.append({
            'date': records[i]['Date'],
            'price': curr_close,
            'change_pct': change_pct
        })

    # Sort by absolute change
    price_changes.sort(key=lambda x: abs(x['change_pct']), reverse=True)

    return price_changes[:10]  # Top 10 moves

def volume_analysis(records: List[Dict[str, Any]]):
    """Analyze volume patterns"""

    volumes = [r['Volume'] for r in records]
    avg_volume = sum(volumes) / len(volumes)

    # Find high volume periods
    high_volume_periods = []
    for record in records:
        if record['Volume'] > avg_volume * 2:  # 2x average volume
            high_volume_periods.append({
                'date': record['Date'],
                'volume': record['Volume'],
                'price': record['Close'],
                'multiplier': record['Volume'] / avg_volume
            })

    return {
        'avg_volume': avg_volume,
        'max_volume': max(volumes),
        'min_volume': min(volumes),
        'high_volume_periods': high_volume_periods[:10]  # Top 10
    }

def main():
    print("📊 ETH Data Analysis")
    print("=" * 70)

    # Load data
    data = load_eth_data()
    records = data['ohlcv']

    print(f"📈 Dataset Info:")
    print(f"  Records: {len(records)}")
    print(f"  Timeframe: {data['timeframe']}")
    print(f"  Period: {data['lookback_days']} days")
    print(f"  Data Source: {data['data_source']}")

    # Technical indicators
    print(f"\n🔢 Technical Indicators:")
    print("-" * 40)
    indicators = calculate_technical_indicators(records)

    current_price = indicators['current_price']
    print(f"Current Price: ${current_price:,.2f}")

    if indicators['sma_20']:
        print(f"SMA 20 (10h): ${indicators['sma_20']:,.2f}")
        trend_20 = "Above" if current_price > indicators['sma_20'] else "Below"
        print(f"  → Price is {trend_20} SMA 20")

    if indicators['sma_50']:
        print(f"SMA 50 (25h): ${indicators['sma_50']:,.2f}")
        trend_50 = "Above" if current_price > indicators['sma_50'] else "Below"
        print(f"  → Price is {trend_50} SMA 50")

    if indicators['rsi']:
        rsi_level = "Overbought" if indicators['rsi'] > 70 else "Oversold" if indicators['rsi'] < 30 else "Neutral"
        print(f"RSI (14): {indicators['rsi']:.1f} ({rsi_level})")

    # Price extremes
    print(f"\n📈 Biggest Price Movements:")
    print("-" * 40)
    extremes = find_price_extremes(records)

    for i, move in enumerate(extremes[:5]):
        date_str = datetime.fromisoformat(move['date'].replace('Z', '+00:00')).strftime('%m/%d %H:%M')
        print(f"{i+1}. {date_str}: ${move['price']:,.2f} ({move['change_pct']:+.2f}%)")

    # Volume analysis
    print(f"\n📊 Volume Analysis:")
    print("-" * 40)
    vol_analysis = volume_analysis(records)

    print(f"Average Volume: {vol_analysis['avg_volume']:,.0f}")
    print(f"Max Volume: {vol_analysis['max_volume']:,.0f}")
    print(f"Min Volume: {vol_analysis['min_volume']:,.0f}")

    if vol_analysis['high_volume_periods']:
        print(f"\nHigh Volume Periods (>2x avg):")
        for period in vol_analysis['high_volume_periods'][:3]:
            date_str = datetime.fromisoformat(period['date'].replace('Z', '+00:00')).strftime('%m/%d %H:%M')
            print(f"  {date_str}: {period['volume']:,.0f} ({period['multiplier']:.1f}x avg)")

    # Recent price action
    print(f"\n📅 Recent Price Action (Last 24 Hours):")
    print("-" * 40)

    # Last 48 records (24 hours of 30min data)
    recent_records = records[-48:]
    recent_high = max(r['High'] for r in recent_records)
    recent_low = min(r['Low'] for r in recent_records)
    start_price = recent_records[0]['Close']
    end_price = recent_records[-1]['Close']

    change_24h = end_price - start_price
    change_24h_pct = (change_24h / start_price) * 100

    print(f"24h High: ${recent_high:,.2f}")
    print(f"24h Low: ${recent_low:,.2f}")
    print(f"24h Range: ${recent_high - recent_low:,.2f}")
    print(f"24h Change: ${change_24h:+,.2f} ({change_24h_pct:+.2f}%)")

    print(f"\n✅ This is exactly what DPA provides to other agents!")
    print(f"💡 MRCA would use this data for regime analysis")
    print(f"💡 EVA would use this for strategy backtesting")
    print(f"💡 LAA would use this for learning patterns")

if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError:
        print("❌ eth_30min_30days.json not found")
        print("💡 Run simple_eth_fetch.py first to get the data")
    except Exception as e:
        print(f"❌ Error: {e}")