# MRCA (Market Regime Classification Agent) - Complete Guide

## Table of Contents
1. [What is MRCA?](#what-is-mrca)
2. [Market Regimes Detected](#market-regimes-detected)
3. [How MRCA Works](#how-mrca-works)
4. [Real Value Beyond Labeling](#real-value-beyond-labeling)
5. [Technical Implementation](#technical-implementation)
6. [AI vs Pure Code](#ai-vs-pure-code)
7. [Practical Examples](#practical-examples)
8. [Integration with Other Agents](#integration-with-other-agents)
9. [Getting Started](#getting-started)

---

## What is MRCA?

MRCA (Market Regime Classification Agent) is the **"Market Analyst"** in the PokPok trading system that determines what type of market environment we're currently in. Rather than just looking at price movements, MRCA provides **actionable market context** that drives strategy selection, risk management, and trading decisions.

### Purpose
- Classify current market conditions into specific regimes
- Provide confidence scores for regime classifications
- Enable context-aware trading decisions
- Trigger automatic strategy switching based on market changes
- Optimize risk parameters dynamically

---

## Market Regimes Detected

MRCA can identify 6 primary market regimes:

| Regime | Description | Trading Implications |
|--------|-------------|---------------------|
| `BULL_TREND_HIGH_VOL` | 🚀 Strong uptrend with high volatility | Momentum plays, trend following |
| `BULL_TREND_LOW_VOL` | 📈 Steady uptrend with low volatility | Buy-and-hold, covered calls |
| `BEAR_TREND_HIGH_VOL` | 💥 Sharp downtrend with high volatility | Put options, short strategies |
| `BEAR_TREND_LOW_VOL` | 📉 Steady downtrend with low volatility | Protective puts, cash positions |
| `RANGE_HIGH_VOL` | ⚡ Sideways market with high volatility | Straddles, range-bound strategies |
| `RANGE_LOW_VOL` | 😴 Sideways market with low volatility | Theta decay strategies |

---

## How MRCA Works

### Step-by-Step Process

1. **Data Access**
   - Receives OHLCV data from DPA via `agent.team_session_state["ohlcv_data"]`
   - Typically analyzes 30-150 days of historical data
   - Uses same data format as DPA output

2. **AI Analysis** (Optional)
   - AI decides which technical indicators to use
   - Chooses optimal parameters (RSI length, SMA periods, etc.)
   - Analyzes current vs historical market patterns

3. **Technical Indicator Calculation**
   - **RSI** - Momentum oscillator (overbought/oversold)
   - **SMA/EMA** - Trend direction and strength
   - **MACD** - Trend changes and momentum shifts
   - **Bollinger Bands** - Volatility and support/resistance
   - **Volume Analysis** - Market participation levels

4. **Pattern Recognition**
   - Analyzes price patterns and trends
   - Identifies support/resistance levels
   - Measures volatility characteristics
   - Detects market structure changes

5. **Regime Classification**
   - Combines indicators using logic rules or AI reasoning
   - Assigns confidence scores (0.0 to 1.0)
   - Provides explanation for classification
   - Returns structured `MarketRegimeAnalysisResponse`

### Technical Tools Available

```python
# Core MRCA tools
calculate_rsi(agent, length=14)           # RSI calculation
calculate_sma(agent, length=20)           # Simple Moving Average
calculate_ema(agent, length=12)           # Exponential Moving Average
calculate_macd(agent, fast=12, slow=26)   # MACD indicator
calculate_bollinger_bands(agent, length=20) # Volatility bands
add_indicators_to_dataframe(agent, configs) # Bulk indicator calculation
```

---

## Real Value Beyond Labeling

### ❌ What People Think MRCA Does
- Just slaps a label like `BEAR_TREND_LOW_VOL`
- Simple pattern matching
- Could be replaced with basic if/else logic

### ✅ What MRCA Actually Provides

#### 1. 🎯 Context-Aware Decision Making
The **same technical signal** means completely different things in different regimes:

| Signal | Bull Trend | Bear Trend | Range Market |
|--------|------------|------------|--------------|
| RSI Oversold (25) | ✅ Strong buy signal | ❌ Stay away, could go lower | ✅ Mean reversion play |
| Resistance Break | ✅ Momentum continuation | ❌ Likely false breakout | ⚠️ Could go either way |
| Volume Spike | 🚨 Possible regime change | 📈 Potential capitulation | ⚡ Breakout likely |

#### 2. 📊 Dynamic Risk Management
- **High-vol regimes** → Smaller positions, wider stops (3-5%)
- **Low-vol regimes** → Larger positions, tighter stops (1-2%)
- **High confidence** → Aggressive positioning (2-3% risk)
- **Low confidence** → Defensive mode (0.5-1% risk)

#### 3. 🔄 Real-Time Strategy Switching
- **Bull→Bear transition** = Switch from momentum to defensive strategies
- **Low-vol→High-vol** = Immediately reduce position sizes
- **Range→Trend** = Change from mean-reversion to trend-following

#### 4. 🧠 Parameter Optimization
- **Trending markets** = Longer indicator periods (RSI 21, SMA 50)
- **Ranging markets** = Shorter periods (RSI 14, SMA 20)
- **Volatile markets** = Wider stops, smaller positions
- **Stable markets** = Tighter stops, larger positions

---

## Technical Implementation

### Output Structure

```json
{
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
  "completed_successfully": true,
  "error_message": null
}
```

### Example Classification Logic (Pure Python)

```python
def classify_regime(price, sma20, sma50, rsi, volatility):
    """Rule-based regime classification (no AI needed)"""

    # Determine trend direction
    if price > sma50 and sma20 > sma50:
        trend = "bull"
    elif price < sma50 and sma20 < sma50:
        trend = "bear"
    else:
        trend = "range"

    # Determine volatility level
    vol_level = "high" if volatility > 0.03 else "low"

    # Combine for regime classification
    if trend == "bull" and vol_level == "high":
        return "BULL_TREND_HIGH_VOL"
    elif trend == "bull" and vol_level == "low":
        return "BULL_TREND_LOW_VOL"
    elif trend == "bear" and vol_level == "high":
        return "BEAR_TREND_HIGH_VOL"
    elif trend == "bear" and vol_level == "low":
        return "BEAR_TREND_LOW_VOL"
    elif vol_level == "high":
        return "RANGE_HIGH_VOL"
    else:
        return "RANGE_LOW_VOL"
```

---

## AI vs Pure Code

### What Requires AI Services ($$$)
- **Natural Language Processing** - Converting "analyze recent ETH market" to function calls
- **Dynamic Parameter Selection** - AI choosing optimal RSI periods, indicator combinations
- **Intelligent Explanations** - Generating human-readable reasoning
- **Team Coordination** - Multi-agent communication and context sharing

### What Works Without AI (FREE)
- **Market data fetching** - Direct API calls to exchanges
- **Technical indicator calculations** - Pure mathematical formulas
- **Regime classification** - Rule-based if/else logic
- **Strategy parameter optimization** - Backtesting and statistical methods
- **Risk management calculations** - Mathematical models

### Cost Breakdown
| Component | Cost | Dependencies |
|-----------|------|--------------|
| Market Data | FREE | Public APIs (Deribit, Bitfinex) |
| Technical Indicators | FREE | Python math libraries |
| Basic Regime Classification | FREE | Pure Python logic |
| Natural Language Interface | $$$ | OpenRouter API (Claude 4) |
| Dynamic AI Reasoning | $$$ | LLM services |

---

## Practical Examples

### Example 1: Your ETH Data Analysis
**Current State:**
- Price: $4,175.90
- SMA20: $4,167.73
- SMA50: $4,177.33
- RSI: 45.3
- 30-day change: -9.21%

**MRCA Classification:** `BEAR_TREND_LOW_VOL` (60% confidence)

**Trading Implications:**
- ❌ **Avoid:** Momentum/breakout strategies
- ✅ **Focus:** Mean-reversion plays, protective puts
- ⚖️ **Risk:** Medium position sizes (moderate confidence)
- 🔍 **Signals:** RSI 45.3 = Still bearish context, not neutral
- 🎯 **Expectations:** False breakouts likely, fade them

### Example 2: Strategy Switching Scenarios

#### Scenario A: Bull Market RSI Oversold
```
Market: BULL_TREND_LOW_VOL
RSI: 25 (oversold)
Action: Strong BUY signal - high probability bounce
```

#### Scenario B: Bear Market RSI Oversold
```
Market: BEAR_TREND_HIGH_VOL
RSI: 25 (oversold)
Action: AVOID - could fall much further
```

#### Scenario C: Range Market Breakout
```
Market: RANGE_HIGH_VOL
Price: Breaks above resistance
Action: Small position - could be false breakout
```

---

## Integration with Other Agents

### Data Flow
```
DPA → MRCA → Other Agents
```

| Connection | Purpose |
|------------|---------|
| **DPA → MRCA** | DPA provides OHLCV data, MRCA analyzes regime |
| **MRCA → EVA** | EVA uses regime info to evaluate strategy fitness |
| **MRCA → LAA** | LAA adapts strategies based on regime changes |
| **MRCA → MST** | MST develops strategies suitable for current regime |
| **MRCA → Trading** | Trading signals filtered by regime appropriateness |

### Team Session State
```python
# MRCA accesses DPA data
ohlcv_data = agent.team_session_state["ohlcv_data"]

# MRCA stores regime analysis
agent.team_session_state["market_regime"] = regime_analysis
```

---

## Getting Started

### Prerequisites
- Python 3.8+
- Access to market data (free public APIs work fine)
- Basic understanding of technical analysis

### Quick Start (No AI Required)

1. **Fetch Market Data**
   ```bash
   python3 simple_eth_fetch.py
   ```

2. **Run MRCA Analysis**
   ```bash
   python3 demo_mrca_analysis.py
   ```

3. **Understand the Concepts**
   ```bash
   python3 explain_mrca.py
   ```

### Files in This Repository
- `demo_mrca_analysis.py` - Real MRCA analysis using your ETH data
- `explain_mrca.py` - Complete explanation of MRCA concepts
- `mrca_real_value.py` - Deep dive into MRCA's value proposition
- `ai_vs_code_breakdown.py` - What requires AI vs pure Python

### Next Steps

#### Phase 1: Rule-Based System (Free)
1. Implement basic regime classification logic
2. Create strategy switching rules
3. Build risk management parameters
4. Backtest on historical data

#### Phase 2: Enhanced System (Optional AI)
1. Add natural language interface
2. Implement dynamic parameter optimization
3. Create learning and adaptation mechanisms
4. Build multi-agent coordination

---

## Key Takeaways

1. **MRCA is NOT just labeling** - it's actionable market intelligence
2. **Core functionality works without AI** - save money on the essentials
3. **Same signals mean different things** in different market regimes
4. **Dynamic risk management** is the key value proposition
5. **Start simple, add complexity later** - build profitable base first

---

## Conclusion

MRCA transforms raw market data into actionable trading context. While AI can enhance the experience with natural language processing and dynamic adaptation, the core value lies in **context-aware decision making** that can be implemented with pure Python logic.

The regime classification is just the output - the real value is in how it changes trading behavior across different market conditions.

**Remember:** You can build a complete, profitable trading system using rule-based MRCA logic before ever needing AI services!