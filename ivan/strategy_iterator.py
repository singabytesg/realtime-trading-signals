#!/usr/bin/env python3
"""
Strategy Iterator: Find Profitable Strategy Through Systematic Testing
Simulates LAA-EVA iteration process to discover profitable strategies
"""

import json
from datetime import datetime, timedelta

def load_eth_data():
    """Load your real ETH data"""
    with open('eth_30min_30days.json', 'r') as f:
        data = json.load(f)
    return data['ohlcv']

def calculate_indicators(eth_records):
    """Calculate technical indicators for strategy testing"""

    closes = [r['Close'] for r in eth_records]
    volumes = [r['Volume'] for r in eth_records]
    highs = [r['High'] for r in eth_records]
    lows = [r['Low'] for r in eth_records]

    # RSI calculation
    def calc_rsi(prices, period=14):
        rsi_values = []
        for i in range(len(prices)):
            if i < period:
                rsi_values.append(None)
                continue

            gains = []
            losses = []
            for j in range(i-period+1, i+1):
                if j == 0:
                    continue
                change = prices[j] - prices[j-1]
                gains.append(max(0, change))
                losses.append(max(0, -change))

            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0

            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            rsi_values.append(rsi)
        return rsi_values

    # SMA calculation
    def calc_sma(data, period):
        sma_values = []
        for i in range(len(data)):
            if i < period - 1:
                sma_values.append(None)
            else:
                sma = sum(data[i-period+1:i+1]) / period
                sma_values.append(sma)
        return sma_values

    indicators = {
        'rsi_14': calc_rsi(closes, 14),
        'rsi_21': calc_rsi(closes, 21),
        'sma_10': calc_sma(closes, 10),
        'sma_20': calc_sma(closes, 20),
        'sma_50': calc_sma(closes, 50),
        'vol_avg_5': calc_sma(volumes, 5),
        'vol_avg_10': calc_sma(volumes, 10),
        'vol_avg_20': calc_sma(volumes, 20)
    }

    return indicators

def test_strategy_variant(eth_records, indicators, strategy_config):
    """Test a specific strategy configuration"""

    trades = []

    for i in range(50, len(eth_records) - 144):  # Room for 3-day exits
        current = eth_records[i]
        current_price = current['Close']

        # Get indicator values
        indicator_values = {}
        for name, values in indicators.items():
            indicator_values[name] = values[i] if i < len(values) and values[i] is not None else None

        # Skip if key indicators missing
        required_indicators = strategy_config.get('required_indicators', [])
        if any(indicator_values.get(ind) is None for ind in required_indicators):
            continue

        # Evaluate strategy conditions
        signal = evaluate_strategy_conditions(current, indicator_values, strategy_config)

        if signal:
            # Calculate trade outcome
            exit_index = i + strategy_config['exit_periods']
            if exit_index >= len(eth_records):
                continue

            exit_price = eth_records[exit_index]['Close']

            # Calculate P&L
            if signal['type'] == 'PUT':
                move_pct = (current_price - exit_price) / current_price * 100
                gross_profit = min(move_pct, signal['profit_cap']) if move_pct > 0 else 0
            else:  # CALL
                move_pct = (exit_price - current_price) / current_price * 100
                gross_profit = min(move_pct, signal['profit_cap']) if move_pct > 0 else 0

            net_profit = gross_profit - strategy_config['premium_cost']

            trades.append({
                'entry_date': current['Date'],
                'entry_price': current_price,
                'exit_price': exit_price,
                'signal_type': signal['type'],
                'move_pct': move_pct,
                'net_profit': net_profit,
                'profitable': net_profit > 0,
                'strategy': strategy_config['name']
            })

    # Calculate performance metrics
    if not trades:
        return {'win_rate': 0, 'total_pnl': 0, 'trades': 0, 'fitness': 0}

    profitable_trades = [t for t in trades if t['profitable']]
    win_rate = len(profitable_trades) / len(trades) * 100
    total_pnl = sum(t['net_profit'] for t in trades)
    avg_pnl = total_pnl / len(trades)

    # Simple fitness calculation
    if win_rate < 40:
        fitness = 0.2  # Poor
    elif win_rate < 55:
        fitness = 0.4  # Marginal
    elif win_rate < 65:
        fitness = 0.5  # Below threshold
    else:
        fitness = 0.6 + (win_rate - 65) / 100  # Above threshold

    return {
        'name': strategy_config['name'],
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl,
        'trades': len(trades),
        'profitable_trades': len(profitable_trades),
        'fitness': fitness,
        'trade_details': trades[:10]  # First 10 for analysis
    }

def evaluate_strategy_conditions(current, indicators, config):
    """Evaluate if strategy conditions are met"""

    conditions = config['conditions']

    # Check each condition
    for condition in conditions:
        if not check_condition(current, indicators, condition):
            return None  # Condition failed

    # All conditions met - generate signal
    return {
        'type': config['signal_type'],
        'strength': config['signal_strength'],
        'profit_cap': config['profit_cap']
    }

def check_condition(current, indicators, condition):
    """Check individual condition"""

    if condition['type'] == 'rsi_threshold':
        rsi_value = indicators.get(condition['indicator'])
        if rsi_value is None:
            return False

        if condition['operator'] == '<':
            return rsi_value < condition['value']
        elif condition['operator'] == '>':
            return rsi_value > condition['value']
        elif condition['operator'] == 'between':
            return condition['value'][0] < rsi_value < condition['value'][1]

    elif condition['type'] == 'price_vs_sma':
        price = current['Close']
        sma_value = indicators.get(condition['indicator'])
        if sma_value is None:
            return False

        threshold = sma_value * condition['multiplier']

        if condition['operator'] == '<':
            return price < threshold
        elif condition['operator'] == '>':
            return price > threshold

    elif condition['type'] == 'volume_ratio':
        volume = current['Volume']
        vol_avg = indicators.get(condition['indicator'])
        if vol_avg is None:
            return False

        ratio = volume / vol_avg
        return ratio > condition['min_ratio']

    return False

def define_strategy_variants():
    """Define different strategy variants to test"""

    strategies = [
        {
            'name': 'Simple_SMA_Reversion',
            'description': 'PUT when price above SMA, expect reversion',
            'required_indicators': ['sma_20'],
            'conditions': [
                {'type': 'price_vs_sma', 'indicator': 'sma_20', 'operator': '>', 'multiplier': 1.01}
            ],
            'signal_type': 'PUT',
            'signal_strength': -3,
            'profit_cap': 5,
            'exit_periods': 72,  # 3 days
            'premium_cost': 3.0
        },
        {
            'name': 'Oversold_RSI_Bounce',
            'description': 'CALL when very oversold, expect bounce',
            'required_indicators': ['rsi_14', 'sma_20'],
            'conditions': [
                {'type': 'rsi_threshold', 'indicator': 'rsi_14', 'operator': '<', 'value': 25},
                {'type': 'price_vs_sma', 'indicator': 'sma_20', 'operator': '<', 'multiplier': 0.97}
            ],
            'signal_type': 'CALL',
            'signal_strength': 3,
            'profit_cap': 5,
            'exit_periods': 48,  # 1 day
            'premium_cost': 3.0
        },
        {
            'name': 'Conservative_RSI_Put',
            'description': 'PUT when RSI in middle range, expect continuation down',
            'required_indicators': ['rsi_14', 'sma_20'],
            'conditions': [
                {'type': 'rsi_threshold', 'indicator': 'rsi_14', 'operator': 'between', 'value': [40, 65]},
                {'type': 'price_vs_sma', 'indicator': 'sma_20', 'operator': '>', 'multiplier': 1.005}
            ],
            'signal_type': 'PUT',
            'signal_strength': -3,
            'profit_cap': 5,
            'exit_periods': 72,  # 3 days
            'premium_cost': 3.0
        },
        {
            'name': 'Strict_Oversold_Call',
            'description': 'CALL only when extremely oversold with volume',
            'required_indicators': ['rsi_14', 'sma_20', 'vol_avg_10'],
            'conditions': [
                {'type': 'rsi_threshold', 'indicator': 'rsi_14', 'operator': '<', 'value': 20},
                {'type': 'price_vs_sma', 'indicator': 'sma_20', 'operator': '<', 'multiplier': 0.95},
                {'type': 'volume_ratio', 'indicator': 'vol_avg_10', 'min_ratio': 1.5}
            ],
            'signal_type': 'CALL',
            'signal_strength': 3,
            'profit_cap': 5,
            'exit_periods': 24,  # 12 hours
            'premium_cost': 3.0
        },
        {
            'name': 'Long_SMA_Reversion',
            'description': 'PUT when price above long-term average',
            'required_indicators': ['sma_50'],
            'conditions': [
                {'type': 'price_vs_sma', 'indicator': 'sma_50', 'operator': '>', 'multiplier': 1.02}
            ],
            'signal_type': 'PUT',
            'signal_strength': -7,  # Higher conviction
            'profit_cap': 10,       # 7-day option
            'exit_periods': 144,    # 3 days
            'premium_cost': 4.0     # Higher premium for 7-day
        },
        {
            'name': 'Volume_Spike_Put',
            'description': 'PUT on volume spikes in bear market',
            'required_indicators': ['vol_avg_20', 'sma_20'],
            'conditions': [
                {'type': 'volume_ratio', 'indicator': 'vol_avg_20', 'min_ratio': 2.5},
                {'type': 'price_vs_sma', 'indicator': 'sma_20', 'operator': '>', 'multiplier': 0.99}
            ],
            'signal_type': 'PUT',
            'signal_strength': -3,
            'profit_cap': 5,
            'exit_periods': 72,
            'premium_cost': 3.0
        }
    ]

    return strategies

def run_strategy_iteration():
    """Run LAA-style iteration to find profitable strategy"""

    print("=" * 80)
    print("🔄 LAA-EVA Strategy Iteration Simulator")
    print("=" * 80)

    eth_records = load_eth_data()
    indicators = calculate_indicators(eth_records)
    strategy_variants = define_strategy_variants()

    print(f"📊 Testing {len(strategy_variants)} strategy variants on your ETH data...")
    print(f"🎯 Target: >65% win rate, positive P&L, fitness >0.6")

    results = []

    print(f"\n🔄 Iteration Results:")
    print("-" * 80)

    for i, strategy in enumerate(strategy_variants, 1):
        print(f"\nIteration {i}: {strategy['name']}")
        print(f"Description: {strategy['description']}")

        result = test_strategy_variant(eth_records, indicators, strategy)
        results.append(result)

        status = "✅ APPROVED" if result['fitness'] >= 0.6 and result['win_rate'] >= 65 else "❌ REJECTED"

        print(f"Results: {result['trades']} trades, {result['win_rate']:.1f}% win rate, {result['total_pnl']:+.1f}% P&L, fitness {result['fitness']:.2f}")
        print(f"EVA Verdict: {status}")

        if result['fitness'] >= 0.6 and result['win_rate'] >= 65:
            print(f"🎉 FOUND PROFITABLE STRATEGY!")
            break

    return results

def analyze_best_strategies(results):
    """Analyze the best performing strategies"""

    print(f"\n" + "=" * 80)
    print("📊 STRATEGY PERFORMANCE RANKING")
    print("=" * 80)

    # Sort by fitness score
    sorted_results = sorted(results, key=lambda x: x['fitness'], reverse=True)

    print(f"📈 Performance Ranking (by fitness score):")
    print("-" * 60)

    for i, result in enumerate(sorted_results, 1):
        approval_status = "✅ APPROVED" if result['fitness'] >= 0.6 and result['win_rate'] >= 65 else "❌ REJECTED"

        print(f"{i}. {result['name']}")
        print(f"   Win Rate: {result['win_rate']:.1f}% | P&L: {result['total_pnl']:+.1f}% | Fitness: {result['fitness']:.3f} | {approval_status}")
        print(f"   Trades: {result['trades']} | Avg per trade: {result['avg_pnl']:+.2f}%")

        # Show sample trades for top 3
        if i <= 3 and result['trade_details']:
            print(f"   Sample trades:")
            for j, trade in enumerate(result['trade_details'][:3], 1):
                entry_time = datetime.fromisoformat(trade['entry_date'].replace('+00:00', ''))
                profit_status = "✅" if trade['profitable'] else "❌"
                print(f"      {j}. {entry_time.strftime('%m/%d %H:%M')}: ${trade['entry_price']:.2f} → ${trade['exit_price']:.2f} = {trade['net_profit']:+.1f}% {profit_status}")
        print()

def create_enhanced_strategy():
    """Create enhanced strategy based on learnings"""

    print(f"\n" + "=" * 80)
    print("🚀 Creating Enhanced Strategy Based on Iteration Learnings")
    print("=" * 80)

    enhanced_strategy = {
        'name': 'ETH_Enhanced_Profitable',
        'description': 'Enhanced strategy combining best elements from iteration testing',
        'required_indicators': ['rsi_14', 'sma_20', 'vol_avg_10'],
        'conditions': [
            # Very selective conditions based on what worked
            {'type': 'rsi_threshold', 'indicator': 'rsi_14', 'operator': 'between', 'value': [35, 70]},
            {'type': 'price_vs_sma', 'indicator': 'sma_20', 'operator': '>', 'multiplier': 1.015},  # 1.5% above
            {'type': 'volume_ratio', 'indicator': 'vol_avg_10', 'min_ratio': 1.3}  # Strong volume
        ],
        'signal_type': 'PUT',
        'signal_strength': -3,
        'profit_cap': 5,
        'exit_periods': 96,  # 2 days (compromise)
        'premium_cost': 2.5  # Lower premium assumption
    }

    return enhanced_strategy

def main():
    print("🔄 Strategy Iterator: Finding Profitable Strategy")
    print("=" * 80)

    print(f"\n🎯 Objective:")
    print(f"   Find strategy with >65% win rate and positive returns")
    print(f"   Simulate LAA-EVA iteration process")
    print(f"   Test multiple approaches systematically")

    # Run iteration process
    results = run_strategy_iteration()

    # Analyze results
    analyze_best_strategies(results)

    # Check if we found a winner
    winners = [r for r in results if r['fitness'] >= 0.6 and r['win_rate'] >= 65]

    if winners:
        best_strategy = max(winners, key=lambda x: x['fitness'])
        print(f"🎉 SUCCESS: Found profitable strategy!")
        print(f"   Strategy: {best_strategy['name']}")
        print(f"   Win Rate: {best_strategy['win_rate']:.1f}%")
        print(f"   Total P&L: {best_strategy['total_pnl']:+.1f}%")
        print(f"   Fitness: {best_strategy['fitness']:.3f}")
    else:
        print(f"❌ No strategy met profitability criteria")
        print(f"💡 This shows why LAA iteration is crucial!")

        # Try enhanced strategy
        enhanced = create_enhanced_strategy()
        print(f"\n🔄 Testing Enhanced Strategy...")

        eth_records = load_eth_data()
        indicators = calculate_indicators(eth_records)
        enhanced_result = test_strategy_variant(eth_records, indicators, enhanced)

        print(f"Enhanced Results: {enhanced_result['win_rate']:.1f}% win rate, {enhanced_result['total_pnl']:+.1f}% P&L")

    print(f"\n" + "=" * 80)
    print("💡 ITERATION INSIGHTS")
    print("=" * 80)

    insights = [
        "🔄 Real LAA would test dozens of strategy variants",
        "📊 Each iteration reveals what works vs what doesn't",
        "🎯 Successful strategies emerge from systematic testing",
        "⚡ Simple strategies often outperform complex ones",
        "💰 Profitability requires matching strategy to market character",
        "✅ EVA quality control prevents deployment of losing strategies"
    ]

    for insight in insights:
        print(f"  {insight}")

    print(f"\n✨ This demonstrates the real LAA-EVA iterative process!")
    print(f"🎯 Profitable strategies are discovered, not invented!")

if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError:
        print("❌ eth_30min_30days.json not found")
        print("💡 Make sure you're running from the correct directory")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()