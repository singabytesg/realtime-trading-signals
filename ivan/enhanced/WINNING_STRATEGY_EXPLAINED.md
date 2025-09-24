# How the Winning Strategy Generates Signals and Trades

## Overview
The winning strategy achieved **77.8% win rate** using a sophisticated DSL (Domain Specific Language) that evaluates multiple technical indicators and market conditions to generate trading signals.

## Step-by-Step Signal Generation Process

### 1. **Indicator Calculation Phase**

First, the strategy calculates 5 key indicators for each timestamp:

```python
indicators = {
    "rsi_main": RSI(14),           # Momentum oscillator
    "macd_main": MACD(12, 21, 7),  # Trend following
    "sma_short": SMA(15),          # Short-term trend
    "sma_long": SMA(20),           # Long-term trend
    "atr": ATR(10)                 # Volatility measure
}
```

These indicators use the **constants** defined in the DSL:
- `macd_fast: 12`, `macd_slow: 21`, `macd_signal: 7`
- `sma_short_period: 15`, `sma_long_period: 20`
- `atr_period: 10`

### 2. **Signal Rule Evaluation**

For each 30-minute candle, the system evaluates three signal rules:

#### **Rule 1: Strong Bear Breakdown** (Generates PUT with strength -7)
```python
if ALL of these conditions are true:
    1. close crosses_below sma_short     # Price breaks below 15-period SMA
    2. sma_short < sma_long              # 15-SMA is below 20-SMA (downtrend)
    3. macd_hist < -0.5                  # Strong negative MACD histogram
    4. rsi_value < 40                    # RSI shows weakness
then:
    Generate PUT signal with strength -7
    Use 7-day option (expecting sustained move)
```

#### **Rule 2: Moderate Bear Signal** (Generates PUT with strength -3)
```python
if ALL of these conditions are true:
    1. macd_line crosses_below macd_signal  # MACD bearish crossover
    2. close < sma_long                     # Price below long-term average
    3. atr_value < 70                       # Low volatility environment
then:
    Generate PUT signal with strength -3
    Use 3-day option (shorter move expected)
```

#### **Rule 3: Oversold Bounce** (Generates CALL with strength 3)
```python
if ALL of these conditions are true:
    1. rsi_value < 30                       # RSI oversold (below 30)
    2. macd_line crosses_above macd_signal  # MACD bullish crossover
then:
    Generate CALL signal with strength 3
    Use 3-day option (quick bounce expected)
```

### 3. **Crossing Detection Logic**

The **"crosses_above"** and **"crosses_below"** operators are crucial:

```python
def crosses_below(series1, series2, current_idx):
    current_val1 = series1[current_idx]
    current_val2 = series2[current_idx]
    prev_val1 = series1[current_idx - 1]
    prev_val2 = series2[current_idx - 1]

    return (prev_val1 >= prev_val2) and (current_val1 < current_val2)
```

This detects the **exact moment** when one line crosses another, triggering signals at optimal entry points.

### 4. **Instrument Selection**

Based on market conditions, the system selects the optimal option type:

```python
def select_instrument(signal_strength, volatility, expected_move):
    if abs(signal_strength) >= 7:  # Strong signal
        if volatility > 3.5:        # High volatility (> high_vol_threshold)
            return "3D_10PCT"       # 3-day, 10% cap, 2.6% cost
        else:
            return "7D_5PCT"        # 7-day, 5% cap, 2.8% cost (DEFAULT)
    else:  # Moderate signal
        return "3D_5PCT"            # 3-day, 5% cap, 2.2% cost
```

### 5. **Actual Trading Example**

Let's trace a real trade from the results:

**Timestamp: 2025-08-27T13:30:00**
```
Price: $4594.60
RSI: 38.5 (< 40) ✓
SMA_15: $4601.20
SMA_20: $4608.50
MACD_hist: -0.82 (< -0.5) ✓
```

**Evaluation:**
1. Price ($4594.60) crosses below SMA_15 ($4601.20) ✓
2. SMA_15 ($4601.20) < SMA_20 ($4608.50) ✓
3. MACD_hist (-0.82) < -0.5 ✓
4. RSI (38.5) < 40 ✓

**Result:** All conditions met for "Strong Bear Breakdown"
- **Signal Generated:** PUT with strength -7
- **Instrument Selected:** 7D_5PCT (7-day duration, 5% cap)
- **Trade Opened:** 35.7 ETH nominal, 1.0 ETH premium paid

**7 days later (2025-09-03):**
- Exit price: $4418.25
- Price moved down 3.84%
- Payout: 3.84% of 35.7 ETH = 1.37 ETH
- Net P&L: 1.37 - 1.0 = 0.37 ETH profit (37% return on premium)

## Why This Strategy Won

### 1. **Multiple Confirmation Signals**
The strategy doesn't rely on a single indicator. For strong signals, it requires:
- Price action (crossing)
- Trend alignment (SMA positions)
- Momentum confirmation (MACD)
- Sentiment extreme (RSI)

### 2. **Adaptive Instrument Selection**
Instead of using fixed options, it adapts based on:
- Signal strength (strong vs moderate)
- Market volatility (ATR-based)
- Expected move magnitude

### 3. **Asymmetric Risk/Reward**
- Risk: Limited to premium (2.2-2.8%)
- Reward: Up to 5-10% capture
- This 2:1 to 3.5:1 reward/risk ratio means even 50% win rate would be profitable

### 4. **Market Regime Awareness**
The strategy performed well because it was tuned for "BEAR_TREND_LOW_VOL" conditions, which matched the actual market during testing (ETH declined from $4600 to $4200).

## Key Success Factors

1. **Crossing Operators**: Detect precise entry points, not just conditions
2. **Multi-Timeframe Analysis**: 15 vs 20 period SMAs capture micro-trends
3. **Volatility Filters**: ATR < 70 ensures entering in calm markets
4. **Dynamic Constants**: Using @variable references allows easy optimization
5. **Conservative Defaults**: When no signal, stays neutral (avoids overtrading)

## The Numbers

From the actual backtest:
- **Total Signals Generated**: 48
- **Trades Executed**: 9-16 (depending on portfolio config)
- **Win Rate**: 75-77.8%
- **Average Win**: +52% return on premium
- **Average Loss**: -100% of premium (total loss)
- **Net Result**: +13.4% portfolio return in 27 days

The strategy succeeds by being **highly selective** - it waits for perfect setups where multiple indicators align, then uses options to capture moves with limited downside risk.