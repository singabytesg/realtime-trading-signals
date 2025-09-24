# Prompt for New Chat Session: Full LAA-EVA Implementation

## 🎯 PRIMARY OBJECTIVE

Create a complete LAA-EVA replication system that:
1. **LAA Agent**: Generates full StrategyLogicDSL with all advanced capabilities
2. **EVA Agent**: Backtests strategies using comprehensive evaluation framework
3. **Strategy Iterator**: Systematically iterates through parameter combinations to find profitable strategies
4. **Target**: Find strategies with >65% win rate and positive returns on real market data

## 📁 REFERENCE FILES (All located in `/ivan/` directory)

### **Market Data**
- `eth_30min_30days.json` - Real 30-day ETH dataset (1,441 30-minute candles, Aug 25 - Sep 24, 2025)

### **Architecture Analysis**
- `LAA_EVA_DEEP_DIVE.md` - Complete LAA-EVA architecture analysis (37KB)
- `LAA_EVA_OPTIMIZATIONS.md` - Detailed optimization recommendations (26KB)
- `DSL_CAPABILITY_ANALYSIS.md` - Full DSL capabilities vs simplified implementation gaps

### **Strategy Analysis Results**
- `PROFITABLE_STRATEGY_ANALYSIS.md` - Bull vs Bear strategy profitability comparison
- `TRADE_BY_TRADE_ANALYSIS.md` - Detailed trade execution results
- `STRATEGY_ITERATION_COMPLETE.md` - Results of 6 failed strategy iterations

### **Previous Implementation Attempts**
- `test_real_laa_strategy_fixed.py` - Real LAA strategy complexity test
- `strategy_iterator.py` - Mini-program iteration attempt (limited DSL)
- `detailed_trade_analysis.py` - Trade-by-trade breakdown implementation

### **Supporting Analysis**
- `demo_laa_eva_integration.py` - LAA-EVA workflow demonstration
- `real_laa_complexity_analysis.py` - Real vs simplified strategy analysis

## 🚨 CRITICAL FINDINGS FROM PREVIOUS WORK

### **Previous Attempt Limitations**
1. **Used only ~20% of full DSL capabilities**
2. **Missing critical features**:
   - Advanced operators (`crosses_above`, `crosses_below`)
   - Multi-component indicators (MACD with 3 outputs)
   - Dynamic constant references (`@rsi_oversold`)
   - Complex condition groups (nested AND/OR logic)
   - Time filters and advanced parameters

3. **Results**: 6 strategy iterations, ALL FAILED (best: 52.9% win rate, -21.3% P&L)

### **Key Discovery**
The failures might be due to **DSL implementation limitations** rather than fundamental impossibility of profitable strategies!

## 🎯 IMPLEMENTATION REQUIREMENTS

### **1. Full DSL Executor Implementation**

Must support ALL DSL capabilities found in the codebase:

#### **Advanced Operators**
```python
SUPPORTED_OPERATORS = [
    ">", "<", ">=", "<=", "==", "!=",
    "crosses_above",     # Crossover detection
    "crosses_below",     # Crossunder detection
    "is_rising",         # Trend detection
    "is_falling",        # Trend detection
    "is_between",        # Range detection
    "is_not_between"     # Range exclusion
]
```

#### **Multi-Component Indicators**
```python
MACD_OUTPUT = {
    "primary_output_column": "macd_line",
    "component_output_map": {
        "MACDh_12_26_9": "macd_hist",      # Histogram
        "MACDs_12_26_9": "macd_signal",    # Signal line
        "MACD_12_26_9": "macd_line"        # MACD line
    }
}

BOLLINGER_OUTPUT = {
    "component_output_map": {
        "BBL_20_2.0": "bb_lower",          # Lower band
        "BBM_20_2.0": "bb_middle",         # Middle band
        "BBU_20_2.0": "bb_upper"           # Upper band
    }
}
```

#### **Dynamic Constants System**
```python
# Constants that can be referenced and optimized
DYNAMIC_CONSTANTS = {
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "min_move_threshold_3d": 2.0,
    "min_move_threshold_7d": 3.5,
    "volatility_threshold_high": 40,
    "min_volume_multiplier": 1.2
}

# Usage in conditions
condition = {
    "series1": "rsi_value",
    "operator": ">",
    "series2_or_value": "@rsi_oversold"  # Dynamic reference!
}
```

### **2. LAA Strategy Generator**

Must replicate LAA character profile capabilities:

#### **PokPok Requirements Integration**
```python
POKPOK_REQUIREMENTS = {
    "minimum_success_probability": 0.65,
    "minimum_expected_move_3d": 2.0,
    "minimum_expected_move_7d": 3.5,
    "maximum_premium_to_profit_ratio": 0.6,
    "minimum_risk_reward_ratio": 1.8
}
```

#### **Regime-Specific Guidelines**
```python
REGIME_CONFIGS = {
    "BEAR_TREND_LOW_VOL": {
        "preferred_signals": [-3],
        "signal_3_min_move": -1.8,
        "avoid_signals": [7, -7],
        "ideal_profit_cap": 5.0,
        "strategy_focus": "conservative_breakdown"
    }
}
```

### **3. EVA Evaluation Framework**

Must implement complete fitness calculation:

#### **Mathematical Fitness Formula**
```python
def calculate_fitness_score(backtest_report):
    # Extract metrics
    apr = stats.get("apr", -100.0)
    win_rate_pct = stats.get("win_rate_pct", 0.0)
    sharpe_ratio = stats.get("sharpe_ratio", -10.0)
    max_drawdown_pct = stats.get("max_drawdown_eth_pct", 100.0)

    # Zero tolerance policies
    if apr < 0:
        return 0.15, "Negative APR triggers zero tolerance"
    if win_rate_pct < 40:
        return 0.25, "Win Rate below 40% threshold"

    # Weighted calculation
    norm_apr = (apr + 50.0) / 100.0
    norm_win_rate = win_rate_pct / 100.0
    norm_sharpe = (sharpe_ratio + 2.0) / 4.0
    drawdown_score = 1.0 - (max_drawdown_pct / 50.0)

    fitness = (norm_apr * 0.4) + (norm_win_rate * 0.3) + (norm_sharpe * 0.2) + (drawdown_score * 0.1)

    return min(fitness, 1.0), calculation_explanation
```

### **4. Strategy Parameter Iterator**

Must systematically test parameter combinations:

#### **Parameter Optimization Space**
```python
OPTIMIZATION_RANGES = {
    "rsi_oversold": [20, 25, 30, 35],
    "rsi_overbought": [65, 70, 75, 80],
    "sma_period": [10, 15, 20, 25, 30],
    "macd_fast": [8, 10, 12, 15],
    "macd_slow": [21, 24, 26, 30],
    "volume_multiplier": [1.1, 1.2, 1.5, 2.0],
    "profit_cap": [5, 10],
    "signal_strength": [-7, -3, 0, 3, 7]
}
```

## 🎯 SYSTEM ARCHITECTURE

### **Core Components Required**

1. **DslStrategyExecutor** - Full implementation with all operators
2. **LAA_Agent_Simulator** - Strategy generation with regime optimization
3. **EVA_Agent_Simulator** - Comprehensive backtesting and fitness calculation
4. **ParameterOptimizer** - Systematic parameter space exploration
5. **PerformanceTracker** - Detailed trade analysis and reporting

### **Expected Workflow**
```
1. LAA generates strategy with full DSL capabilities
2. DSL executor processes with advanced operators (crosses_above, etc.)
3. EVA runs comprehensive backtest with premium costs
4. EVA calculates fitness score using mathematical framework
5. If fitness < 0.6: Iterator adjusts parameters and repeats
6. Continue until fitness >= 0.6 OR determine regime inappropriate
```

## 📊 SUCCESS CRITERIA

### **Target Metrics**
- **Win rate**: >65% (LAA requirement)
- **EVA fitness**: >0.6 (approval threshold)
- **Total return**: Positive after premium costs
- **Max drawdown**: <25%
- **Signal frequency**: Reasonable (not too sparse/frequent)

### **Quality Gates**
- **DSL validation**: Syntactic and semantic correctness
- **PokPok compliance**: Premium coverage and profit cap adherence
- **Regime appropriateness**: Optimized for BEAR_TREND_LOW_VOL
- **Mathematical rigor**: EVA fitness calculation accuracy

## 🚀 DELIVERABLES

### **Primary Output**
1. **Working profitable strategy** with >65% win rate on ETH data
2. **Complete DSL implementation** using all advanced features
3. **Detailed backtest report** with trade-by-trade analysis
4. **Parameter optimization results** showing best combinations

### **Documentation**
1. **Strategy performance report** with all metrics
2. **DSL implementation guide** showing advanced features used
3. **Comparison analysis** vs previous simplified attempts
4. **Optimization insights** for future improvements

## 💡 SPECIFIC TECHNICAL REQUIREMENTS

### **DSL Features Must Include**
- ✅ **crosses_above/crosses_below** operators for precise timing
- ✅ **Multi-component MACD** with line, signal, histogram
- ✅ **@constant references** for dynamic parameter optimization
- ✅ **Complex condition groups** with nested AND/OR logic
- ✅ **ATR volatility filtering** for market condition awareness
- ✅ **Volume confirmation** with multiple timeframe averages

### **Backtesting Must Include**
- ✅ **Premium cost calculations** (3-4% realistic costs)
- ✅ **Profit cap enforcement** (5% for 3-day, 10% for 7-day)
- ✅ **Time decay simulation** for options characteristics
- ✅ **Transaction costs** and slippage
- ✅ **Drawdown analysis** and risk metrics

### **Iteration Must Include**
- ✅ **Systematic parameter testing** across optimization ranges
- ✅ **Performance tracking** for each parameter combination
- ✅ **Early termination** when profitable strategy found
- ✅ **Regime appropriateness** validation throughout

## 🎯 KEY INSIGHT FOR NEW IMPLEMENTATION

The previous iteration failures revealed that our **simplified DSL implementation was the bottleneck**, not the fundamental difficulty of creating profitable strategies.

**With full DSL capabilities (crossing detection, multi-component indicators, parameter optimization), the same market data might yield dramatically different results.**

## 📋 REFERENCE CODEBASE LOCATIONS

Point to these actual implementation files for reference:
- `/src/core/agents/exp/laa.py` - Real LAA implementation
- `/src/core/agents/exp/eval.py` - Real EVA implementation
- `/src/core/characters/laa.py` - LAA character profile with PokPok requirements
- `/src/core/characters/eva.py` - EVA character profile with fitness calculation
- `/src/core/dsl_enum.py` - Complete DSL specification
- `/src/core/function_tools/dsl_executor.py` - Full DSL executor implementation

## 🚀 START NEW CHAT WITH THIS CONTEXT

**Goal**: Build a complete LAA-EVA replication system that uses full DSL capabilities to find profitable strategies through systematic parameter optimization on the real 30-day ETH dataset.

**Expected Outcome**: Either find a profitable strategy (>65% win rate) OR conclusively prove that the specific market regime is unsuitable for short-term options trading.

**The difference**: This time with FULL DSL implementation, not educational simplifications!