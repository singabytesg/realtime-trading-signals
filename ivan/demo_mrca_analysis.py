#!/usr/bin/env python3
"""
MRCA Demo: Analyze Your Real ETH Data
Shows how MRCA would classify the market regime using your actual data
"""

import json
from datetime import datetime
import math

def load_eth_data():
    """Load your real ETH data"""
    with open('eth_30min_30days.json', 'r') as f:
        data = json.load(f)
    return data['ohlcv']

def calculate_technical_indicators(records):
    """Calculate technical indicators like MRCA would"""

    closes = [r['Close'] for r in records]
    highs = [r['High'] for r in records]
    lows = [r['Low'] for r in records]
    volumes = [r['Volume'] for r in records]

    # Simple Moving Averages
    def sma(data, period):
        if len(data) < period:
            return None
        return sum(data[-period:]) / period

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

    # Volatility calculation
    def calculate_volatility(prices, period=20):
        if len(prices) < period:
            return None

        recent_prices = prices[-period:]
        returns = []
        for i in range(1, len(recent_prices)):
            ret = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
            returns.append(ret)

        if not returns:
            return None

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance)
        return volatility

    # Calculate all indicators
    indicators = {
        'current_price': closes[-1],
        'sma_10': sma(closes, 10),
        'sma_20': sma(closes, 20),
        'sma_50': sma(closes, 50),
        'sma_100': sma(closes, 100),
        'rsi_14': calculate_rsi(closes),
        'volatility_20d': calculate_volatility(closes),
        'avg_volume': sum(volumes[-48:]) / 48 if len(volumes) >= 48 else sum(volumes) / len(volumes),  # Last 24h avg
        'volume_trend': volumes[-1] / (sum(volumes[-10:]) / 10) if len(volumes) >= 10 else 1.0
    }

    return indicators

def classify_market_regime(indicators):
    """Simulate MRCA's AI reasoning to classify market regime"""

    current_price = indicators['current_price']
    sma_20 = indicators['sma_20']
    sma_50 = indicators['sma_50']
    rsi = indicators['rsi_14']
    volatility = indicators['volatility_20d']

    # Trend analysis
    trend_direction = "neutral"
    trend_strength = 0.5

    if sma_20 and sma_50:
        if current_price > sma_50 and sma_20 > sma_50:
            trend_direction = "bullish"
            trend_strength = min(1.0, (current_price - sma_50) / sma_50 * 20)
        elif current_price < sma_50 and sma_20 < sma_50:
            trend_direction = "bearish"
            trend_strength = min(1.0, (sma_50 - current_price) / sma_50 * 20)

    # Volatility analysis
    vol_level = "low"
    if volatility and volatility > 0.03:  # 3% daily volatility
        vol_level = "high"

    # Regime classification logic
    regime = "UNDEFINED"
    confidence = 0.5
    reasoning = "Insufficient data for classification"

    if trend_direction == "bullish":
        if vol_level == "high":
            regime = "BULL_TREND_HIGH_VOL"
            reasoning = f"Bullish trend with price above SMA50 (${sma_50:.2f}) and high volatility ({volatility:.3f})"
        else:
            regime = "BULL_TREND_LOW_VOL"
            reasoning = f"Steady bullish trend with price above SMA50 (${sma_50:.2f}) and low volatility"
    elif trend_direction == "bearish":
        if vol_level == "high":
            regime = "BEAR_TREND_HIGH_VOL"
            reasoning = f"Bearish trend with price below SMA50 (${sma_50:.2f}) and high volatility ({volatility:.3f})"
        else:
            regime = "BEAR_TREND_LOW_VOL"
            reasoning = f"Controlled bearish trend with price below SMA50 (${sma_50:.2f}) and low volatility"
    else:
        if vol_level == "high":
            regime = "RANGE_HIGH_VOL"
            reasoning = "Sideways price action with high volatility - choppy market"
        else:
            regime = "RANGE_LOW_VOL"
            reasoning = "Sideways price action with low volatility - stable/boring market"

    # Adjust confidence based on indicator alignment
    confidence = 0.6  # Base confidence

    # Increase confidence if indicators align
    if rsi:
        if trend_direction == "bullish" and rsi > 50:
            confidence += 0.1
        elif trend_direction == "bearish" and rsi < 50:
            confidence += 0.1

    if trend_strength > 0.7:
        confidence += 0.15
    elif trend_strength < 0.3:
        confidence -= 0.1

    confidence = max(0.1, min(1.0, confidence))

    return regime, confidence, reasoning

def generate_mrca_response(records):
    """Generate a complete MRCA response like the real agent would"""

    indicators = calculate_technical_indicators(records)
    regime, confidence, reasoning = classify_market_regime(indicators)

    # Create the assessment record
    assessment = {
        "timestamp_iso": datetime.utcnow().isoformat() + "Z",
        "regime": regime,
        "confidence": round(confidence, 2),
        "supporting_indicators": {
            "current_price": round(indicators['current_price'], 2),
            "sma_20": round(indicators['sma_20'], 2) if indicators['sma_20'] else None,
            "sma_50": round(indicators['sma_50'], 2) if indicators['sma_50'] else None,
            "rsi_14": round(indicators['rsi_14'], 1) if indicators['rsi_14'] else None,
            "volatility_20d": round(indicators['volatility_20d'], 4) if indicators['volatility_20d'] else None,
            "avg_volume_24h": round(indicators['avg_volume'], 0)
        },
        "reasoning": reasoning
    }

    # Generate summary notes
    summary_notes = f"ETH market regime analysis: {regime} with {confidence:.0%} confidence. {reasoning}"

    # Complete MRCA response
    mrca_response = {
        "asset": "ETH",
        "analysis_type_requested": "current_snapshot",
        "assessments": [assessment],
        "agent_summary_notes": summary_notes,
        "completed_successfully": True,
        "error_message": None
    }

    return mrca_response, indicators

def main():
    print("🏛️ MRCA Demo: Analyzing Your Real ETH Data")
    print("=" * 70)

    try:
        # Load your data
        records = load_eth_data()
        print(f"✅ Loaded {len(records)} ETH 30-min records")

        # Generate MRCA analysis
        mrca_response, indicators = generate_mrca_response(records)

        print(f"\n📊 Technical Indicators Calculated:")
        print("-" * 50)
        for key, value in indicators.items():
            if value is not None:
                if isinstance(value, float):
                    if 'price' in key or 'sma' in key:
                        print(f"  {key:<20} ${value:,.2f}")
                    elif 'volatility' in key:
                        print(f"  {key:<20} {value:.4f} ({value*100:.2f}%)")
                    elif 'rsi' in key:
                        print(f"  {key:<20} {value:.1f}")
                    else:
                        print(f"  {key:<20} {value:.2f}")
                else:
                    print(f"  {key:<20} {value}")

        print(f"\n🎯 MRCA Classification:")
        print("=" * 70)
        assessment = mrca_response['assessments'][0]

        print(f"📈 Market Regime: {assessment['regime']}")
        print(f"🎲 Confidence: {assessment['confidence']} ({assessment['confidence']*100:.0f}%)")
        print(f"💭 Reasoning: {assessment['reasoning']}")

        print(f"\n📝 Agent Summary:")
        print(f"{mrca_response['agent_summary_notes']}")

        print(f"\n📋 Full MRCA Response (JSON):")
        print("=" * 70)
        print(json.dumps(mrca_response, indent=2))

        # Interpret the results
        print(f"\n💡 What This Means:")
        print("=" * 70)

        regime = assessment['regime']

        interpretations = {
            "BULL_TREND_HIGH_VOL": "🚀 Strong momentum - good for trend-following strategies",
            "BULL_TREND_LOW_VOL": "📈 Steady growth - good for buy-and-hold, covered calls",
            "BEAR_TREND_HIGH_VOL": "💥 Volatile decline - good for put options, short strategies",
            "BEAR_TREND_LOW_VOL": "📉 Controlled decline - good for protective puts, cash positions",
            "RANGE_HIGH_VOL": "⚡ Choppy market - good for straddles, range-bound strategies",
            "RANGE_LOW_VOL": "😴 Stable market - good for theta decay strategies, boring"
        }

        if regime in interpretations:
            print(f"  {interpretations[regime]}")

        print(f"\n🔗 How Other Agents Would Use This:")
        print(f"  • EVA: Evaluate strategies suitable for {regime}")
        print(f"  • LAA: Adapt existing strategies for current regime")
        print(f"  • MST: Develop new strategies optimized for this market")
        print(f"  • Trading: Filter signals that match this regime")

        print(f"\n✨ This is exactly what MRCA provides to the agent ecosystem!")

    except FileNotFoundError:
        print("❌ eth_30min_30days.json not found")
        print("💡 Run simple_eth_fetch.py first to get the data")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()