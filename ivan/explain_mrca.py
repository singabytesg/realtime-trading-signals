#!/usr/bin/env python3
"""
How MRCA (Market Regime Classification Agent) Works
Detailed explanation with examples and demonstrations
"""

import json
from datetime import datetime

def explain_mrca():
    print("=" * 80)
    print("🏛️ MRCA (Market Regime Classification Agent) - How It Works")
    print("=" * 80)

    print(f"\n🎯 MRCA's Purpose:")
    print(f"MRCA is the 'Market Analyst' that determines what kind of market we're in:")
    print(f"• Bull market? Bear market? Sideways?")
    print(f"• High volatility or low volatility?")
    print(f"• Is it trending or ranging?")

    print(f"\n" + "=" * 80)
    print("📊 MARKET REGIMES MRCA CAN DETECT")
    print("=" * 80)

    regimes = [
        ("BULL_TREND_HIGH_VOL", "🚀 Strong uptrend with high volatility - momentum plays"),
        ("BULL_TREND_LOW_VOL", "📈 Steady uptrend with low volatility - gradual growth"),
        ("BEAR_TREND_HIGH_VOL", "💥 Sharp downtrend with high volatility - panic selling"),
        ("BEAR_TREND_LOW_VOL", "📉 Steady downtrend with low volatility - slow decline"),
        ("RANGE_HIGH_VOL", "⚡ Sideways market with high volatility - choppy/whipsaw"),
        ("RANGE_LOW_VOL", "😴 Sideways market with low volatility - boring/stable")
    ]

    for regime, description in regimes:
        print(f"  • {regime:<25} {description}")

    print(f"\n" + "=" * 80)
    print("🧠 HOW MRCA WORKS - STEP BY STEP")
    print("=" * 80)

    steps = [
        ("1. Gets Data", [
            "Receives OHLCV data from DPA (same data you fetched)",
            "Accesses via: agent.team_session_state['ohlcv_data']",
            "Usually analyzes 30-150 days of historical data"
        ]),

        ("2. AI Analysis", [
            "AI decides which technical indicators to use",
            "Chooses optimal parameters (RSI length, SMA periods, etc.)",
            "Analyzes current market conditions vs historical patterns"
        ]),

        ("3. Calculates Indicators", [
            "RSI (Relative Strength Index) - measures momentum",
            "SMA/EMA (Moving Averages) - identifies trend direction",
            "MACD - detects trend changes and momentum",
            "Bollinger Bands - measures volatility and support/resistance"
        ]),

        ("4. Pattern Recognition", [
            "Analyzes price patterns and trends",
            "Identifies support/resistance levels",
            "Measures volatility characteristics",
            "Detects market structure changes"
        ]),

        ("5. Regime Classification", [
            "Combines all indicators using AI reasoning",
            "Assigns confidence scores (0.0 to 1.0)",
            "Provides explanation for the classification",
            "Returns structured MarketRegimeAnalysisResponse"
        ])
    ]

    for step, details in steps:
        print(f"\n{step}")
        print("-" * 60)
        for detail in details:
            print(f"  • {detail}")

    print(f"\n" + "=" * 80)
    print("🔧 TECHNICAL TOOLS MRCA USES")
    print("=" * 80)

    tools = [
        ("calculate_rsi()", "Momentum oscillator (0-100) - overbought/oversold levels"),
        ("calculate_sma()", "Simple Moving Average - trend direction and strength"),
        ("calculate_ema()", "Exponential Moving Average - responsive to recent prices"),
        ("calculate_macd()", "MACD indicator - trend changes and momentum shifts"),
        ("calculate_bollinger_bands()", "Volatility bands - price expansion/contraction"),
        ("add_indicators_to_dataframe()", "Combines multiple indicators for analysis")
    ]

    for tool, description in tools:
        print(f"  • {tool:<30} {description}")

    print(f"\n" + "=" * 80)
    print("📝 MRCA OUTPUT STRUCTURE")
    print("=" * 80)

    # Sample MRCA response
    sample_response = {
        "asset": "ETH",
        "analysis_type_requested": "current_snapshot",
        "assessments": [
            {
                "timestamp_iso": "2025-09-24T16:30:00Z",
                "regime": "BEAR_TREND_LOW_VOL",
                "confidence": 0.78,
                "supporting_indicators": {
                    "rsi_14": 45.3,
                    "sma_20": 4167.73,
                    "sma_50": 4177.33,
                    "current_price": 4175.90,
                    "volatility_20d": 0.15
                },
                "reasoning": "Price below 50-day SMA with RSI in neutral territory, low volatility suggests controlled decline"
            }
        ],
        "agent_summary_notes": "ETH showing bearish bias with controlled decline. Low volatility suggests institutional distribution rather than panic selling.",
        "completed_successfully": True,
        "error_message": None
    }

    print("JSON Response Structure:")
    print("-" * 40)
    print(json.dumps(sample_response, indent=2))

    print(f"\n" + "=" * 80)
    print("🔄 MRCA IN ACTION - EXAMPLE WORKFLOW")
    print("=" * 80)

    workflow = [
        ("Input", "Human: 'Analyze current ETH market regime'"),
        ("AI Planning", "AI decides to use RSI(14), SMA(20,50), MACD for analysis"),
        ("Data Access", "Fetches OHLCV from team_session_state (DPA data)"),
        ("Indicator Calc", "calculate_rsi(14), calculate_sma(20), calculate_sma(50)"),
        ("Pattern Analysis", "Price: $4,175.90, SMA20: $4,167.73, SMA50: $4,177.33"),
        ("AI Reasoning", "Price below SMA50, RSI neutral → bearish but not panicked"),
        ("Classification", "BEAR_TREND_LOW_VOL with 78% confidence"),
        ("Output", "Structured JSON response with reasoning and indicators")
    ]

    for i, (stage, description) in enumerate(workflow, 1):
        print(f"{i}. {stage:<15} {description}")

    print(f"\n" + "=" * 80)
    print("💡 WHY MRCA IS CRUCIAL")
    print("=" * 80)

    benefits = [
        ("🎯 Strategy Selection", "Different strategies work in different market regimes"),
        ("⚖️ Risk Management", "Adjust position sizes based on volatility regime"),
        ("📈 Signal Filtering", "Filter out signals that don't match current regime"),
        ("🔄 Dynamic Adaptation", "Switch strategies as market conditions change"),
        ("📊 Context Awareness", "Provide market context to other agents (EVA, LAA, MST)")
    ]

    for benefit, description in benefits:
        print(f"  {benefit:<25} {description}")

    print(f"\n" + "=" * 80)
    print("🔗 HOW MRCA CONNECTS WITH OTHER AGENTS")
    print("=" * 80)

    connections = [
        ("DPA → MRCA", "DPA provides OHLCV data, MRCA analyzes regime"),
        ("MRCA → EVA", "EVA uses regime info to evaluate strategy fitness"),
        ("MRCA → LAA", "LAA adapts strategies based on regime changes"),
        ("MRCA → MST", "MST develops strategies suitable for current regime"),
        ("MRCA → Trading", "Trading signals filtered by regime appropriateness")
    ]

    for connection, description in connections:
        print(f"  • {connection:<15} {description}")

    print(f"\n" + "=" * 80)
    print("🎮 USING YOUR ETH DATA WITH MRCA")
    print("=" * 80)

    print("Based on your ETH data analysis:")
    print("• Current Price: $4,175.90")
    print("• 30-day Change: -9.21%")
    print("• RSI: 45.3 (Neutral)")
    print("• Above SMA20, Below SMA50")

    print(f"\nMRCA would likely classify this as:")
    print(f"📊 BEAR_TREND_LOW_VOL or RANGE_LOW_VOL")
    print(f"   Reasoning: Controlled decline, neutral RSI, low volatility")

    print(f"\n✨ Key Insight: MRCA turns raw price data into actionable market context!")
    print(f"Instead of just knowing ETH dropped 9%, you know it's a 'controlled bear trend'")

if __name__ == "__main__":
    explain_mrca()