#!/usr/bin/env python3
"""
SKMA Demo: Strategy Knowledge Management in Action
Shows how SKMA manages trading strategies with mock data
"""

import json
from datetime import datetime, timedelta
import uuid

# Mock strategy database
MOCK_STRATEGIES = []

def initialize_mock_strategies():
    """Create some mock strategies for demo"""
    global MOCK_STRATEGIES

    strategies = [
        {
            "strategy_uuid": str(uuid.uuid4()),
            "name": "RSI_Oversold_Bull_ETH",
            "description": "Buy when RSI < 30 in bull markets, sell when RSI > 70",
            "version": 1,
            "asset_compatibility": ["ETH"],
            "regime_suitability": ["BULL_TREND_LOW_VOL", "BULL_TREND_HIGH_VOL"],
            "timeframe_suitability": ["1h", "4h"],
            "strategy_logic_dsl": "if rsi(14) < 30 and market_regime == 'BULL': buy_signal()",
            "tags": ["RSI", "momentum", "bull-market"],
            "author": "AI_LAA",
            "created_at": datetime.now() - timedelta(days=30),
            "fitness_score": 0.75,
            "apr": 1.45,
            "win_rate": 0.68,
            "max_drawdown": 0.08,
            "status": "active"
        },
        {
            "strategy_uuid": str(uuid.uuid4()),
            "name": "Mean_Reversion_Range_ETH",
            "description": "Mean reversion strategy for ranging markets using Bollinger Bands",
            "version": 2,
            "asset_compatibility": ["ETH", "BTC"],
            "regime_suitability": ["RANGE_LOW_VOL", "RANGE_HIGH_VOL"],
            "timeframe_suitability": ["30m", "1h"],
            "strategy_logic_dsl": "if price < bollinger_lower: buy_signal(); if price > bollinger_upper: sell_signal()",
            "tags": ["bollinger-bands", "mean-reversion", "range-market"],
            "author": "AI_LAA",
            "created_at": datetime.now() - timedelta(days=15),
            "fitness_score": 0.82,
            "apr": 1.67,
            "win_rate": 0.71,
            "max_drawdown": 0.05,
            "status": "active"
        },
        {
            "strategy_uuid": str(uuid.uuid4()),
            "name": "MACD_Momentum_Bear_BTC",
            "description": "Short on MACD bearish crossover in bear markets",
            "version": 1,
            "asset_compatibility": ["BTC"],
            "regime_suitability": ["BEAR_TREND_HIGH_VOL", "BEAR_TREND_LOW_VOL"],
            "timeframe_suitability": ["4h", "1d"],
            "strategy_logic_dsl": "if macd_cross_down() and market_regime == 'BEAR': sell_signal()",
            "tags": ["MACD", "bear-market", "short-selling"],
            "author": "AI_LAA",
            "created_at": datetime.now() - timedelta(days=45),
            "fitness_score": 0.63,
            "apr": 1.23,
            "win_rate": 0.58,
            "max_drawdown": 0.12,
            "status": "active"
        },
        {
            "strategy_uuid": str(uuid.uuid4()),
            "name": "Failed_Breakout_ETH",
            "description": "Momentum breakout strategy that failed in backtesting",
            "version": 1,
            "asset_compatibility": ["ETH"],
            "regime_suitability": ["BULL_TREND_HIGH_VOL"],
            "timeframe_suitability": ["1h"],
            "strategy_logic_dsl": "if price > resistance: buy_signal()",
            "tags": ["breakout", "momentum", "failed"],
            "author": "AI_LAA",
            "created_at": datetime.now() - timedelta(days=60),
            "fitness_score": 0.35,
            "apr": 0.87,  # Below 1.0 = losing strategy
            "win_rate": 0.42,
            "max_drawdown": 0.25,
            "status": "decommissioned"
        }
    ]

    MOCK_STRATEGIES = strategies

def demo_skma_operations():
    """Demonstrate SKMA operations"""

    print("=" * 80)
    print("📚 SKMA Demo: Strategy Knowledge Management")
    print("=" * 80)

    initialize_mock_strategies()

    print(f"\n🗄️ Current Strategy Database ({len(MOCK_STRATEGIES)} strategies)")
    print("-" * 60)

    for i, strategy in enumerate(MOCK_STRATEGIES, 1):
        status_emoji = "✅" if strategy["status"] == "active" else "❌"
        print(f"{i}. {status_emoji} {strategy['name']} (v{strategy['version']})")
        print(f"   💰 APR: {strategy['apr']:.2f} | 🎯 Win Rate: {strategy['win_rate']*100:.1f}% | 📊 Fitness: {strategy['fitness_score']:.2f}")
        print(f"   🏷️ Tags: {', '.join(strategy['tags'])}")
        print(f"   🎮 Assets: {', '.join(strategy['asset_compatibility'])} | ⏰ Timeframes: {', '.join(strategy['timeframe_suitability'])}")
        print()

def fetch_strategies_demo():
    """Demo: Finding strategies by criteria"""

    print("=" * 80)
    print("🔍 DEMO: Finding Strategies by Criteria")
    print("=" * 80)

    # Example 1: Find ETH strategies for bull market
    print("\n📊 Query: Find active ETH strategies for bull markets")
    print("-" * 60)

    bull_eth_strategies = [
        s for s in MOCK_STRATEGIES
        if "ETH" in s["asset_compatibility"]
        and any("BULL" in regime for regime in s["regime_suitability"])
        and s["status"] == "active"
    ]

    if bull_eth_strategies:
        for strategy in bull_eth_strategies:
            print(f"✅ {strategy['name']}")
            print(f"   📈 Regimes: {', '.join(strategy['regime_suitability'])}")
            print(f"   💰 APR: {strategy['apr']:.2f} | 🎯 Fitness: {strategy['fitness_score']:.2f}")
            print()
    else:
        print("❌ No strategies found")

    # Example 2: Find strategies for current market (BEAR_TREND_LOW_VOL)
    print("\n📊 Query: Find strategies for BEAR_TREND_LOW_VOL (your ETH market)")
    print("-" * 60)

    bear_strategies = [
        s for s in MOCK_STRATEGIES
        if "BEAR_TREND_LOW_VOL" in s["regime_suitability"]
        and s["status"] == "active"
    ]

    if bear_strategies:
        for strategy in bear_strategies:
            print(f"✅ {strategy['name']}")
            print(f"   💡 Description: {strategy['description']}")
            print(f"   💰 Expected APR: {strategy['apr']:.2f}")
            print()
    else:
        print("❌ No strategies found for BEAR_TREND_LOW_VOL")
        print("💡 This is why LAA would need to create/adapt strategies!")

def save_strategy_demo():
    """Demo: Saving a new strategy from LAA"""

    print("=" * 80)
    print("💾 DEMO: LAA Creates New Strategy → SKMA Saves It")
    print("=" * 80)

    # Simulate LAA creating a new strategy
    new_strategy = {
        "strategy_uuid": str(uuid.uuid4()),
        "name": "Adaptive_RSI_Bear_ETH_v1",
        "description": "Adaptive RSI strategy optimized for bear markets with dynamic parameters",
        "version": 1,
        "asset_compatibility": ["ETH"],
        "regime_suitability": ["BEAR_TREND_LOW_VOL"],  # Perfect for current market!
        "timeframe_suitability": ["30m", "1h"],
        "strategy_logic_dsl": "if rsi(21) > 60 and volatility < 0.03: sell_signal(confidence=0.8)",
        "tags": ["RSI", "adaptive", "bear-market", "low-volatility"],
        "author": "AI_LAA",
        "created_at": datetime.now(),
        "fitness_score": 0.78,
        "apr": 1.34,  # Above 1.0 = profitable
        "win_rate": 0.65,
        "max_drawdown": 0.07,
        "status": "active"
    }

    print("🤖 LAA created new strategy:")
    print(f"   📝 Name: {new_strategy['name']}")
    print(f"   💡 Purpose: {new_strategy['description']}")
    print(f"   🎯 Market: {', '.join(new_strategy['regime_suitability'])}")
    print(f"   💰 Backtest APR: {new_strategy['apr']:.2f}")

    # SKMA quality check
    print(f"\n🛡️ SKMA Quality Control:")
    if new_strategy['apr'] >= 1.0:
        print("   ✅ APR check passed (≥ 1.0)")
        print("   ✅ Fitness score acceptable (≥ 0.5)")
        print("   ✅ Strategy saved to database")

        # Add to mock database
        MOCK_STRATEGIES.append(new_strategy)

        print(f"\n📊 Database updated: {len(MOCK_STRATEGIES)} strategies total")
    else:
        print("   ❌ APR check failed (< 1.0)")
        print("   ❌ Strategy rejected - not saved")

def performance_tracking_demo():
    """Demo: Tracking strategy performance"""

    print("=" * 80)
    print("📈 DEMO: Performance Tracking & Live Signals")
    print("=" * 80)

    # Mock live signal
    live_signal = {
        "signal_id": str(uuid.uuid4()),
        "strategy_id": MOCK_STRATEGIES[0]["strategy_uuid"],  # Use first strategy
        "strategy_name": MOCK_STRATEGIES[0]["name"],
        "timestamp": datetime.now(),
        "asset": "ETH",
        "signal_type": "BUY",
        "price": 4175.90,
        "confidence": 0.78,
        "position_size": 0.02,  # 2% of portfolio
        "expected_return": 0.05,  # 5% expected
        "stop_loss": 4050.00,
        "take_profit": 4390.00
    }

    print("🚨 Live Trading Signal Generated:")
    print(f"   📝 Strategy: {live_signal['strategy_name']}")
    print(f"   📈 Signal: {live_signal['signal_type']} ETH at ${live_signal['price']:,.2f}")
    print(f"   🎲 Confidence: {live_signal['confidence']:.1%}")
    print(f"   💼 Position: {live_signal['position_size']:.1%} of portfolio")
    print(f"   🛡️ Stop Loss: ${live_signal['stop_loss']:,.2f}")
    print(f"   🎯 Take Profit: ${live_signal['take_profit']:,.2f}")

    print(f"\n💾 SKMA logs signal to database for tracking...")
    print(f"   ✅ Signal logged with ID: {live_signal['signal_id'][:8]}...")

    # Mock outcome after some time
    print(f"\n⏰ 24 Hours Later...")
    outcome = {
        "signal_id": live_signal["signal_id"],
        "exit_price": 4250.30,
        "exit_reason": "take_profit_hit",
        "actual_return": (4250.30 - 4175.90) / 4175.90,  # ~1.8%
        "trade_duration_hours": 18
    }

    print(f"📊 Trade Outcome:")
    print(f"   💰 Exit Price: ${outcome['exit_price']:,.2f}")
    print(f"   📈 Actual Return: {outcome['actual_return']:.1%}")
    print(f"   ⏱️ Duration: {outcome['trade_duration_hours']} hours")
    print(f"   ✅ Result: Profitable trade!")

    print(f"\n🔄 SKMA updates strategy performance metrics...")

def strategy_lifecycle_demo():
    """Demo: Complete strategy lifecycle"""

    print("=" * 80)
    print("🔄 DEMO: Complete Strategy Lifecycle")
    print("=" * 80)

    lifecycle_steps = [
        ("🧠 1. LAA Development", "LAA analyzes current market (BEAR_TREND_LOW_VOL)"),
        ("🔧 2. Strategy Creation", "Creates adaptive RSI strategy for bear market"),
        ("🧪 3. EVA Backtesting", "EVA backtests strategy: APR 1.34, Win Rate 65%"),
        ("✅ 4. Quality Control", "SKMA validates APR ≥ 1.0, saves to database"),
        ("🚀 5. Deployment", "Strategy becomes available for live trading"),
        ("📊 6. Performance Monitoring", "SKMA tracks live signals and outcomes"),
        ("📈 7. Success Tracking", "Strategy performs well, fitness score increases"),
        ("🔄 8. Market Change", "Market regime changes to BULL_TREND_HIGH_VOL"),
        ("⚠️ 9. Performance Decline", "Bear strategy underperforms in bull market"),
        ("🛠️ 10. Adaptation", "LAA adapts strategy for new regime"),
        ("🔄 11. Version Update", "SKMA stores new version, retires old one"),
        ("♾️ 12. Continuous Evolution", "Cycle repeats as markets evolve")
    ]

    for step, description in lifecycle_steps:
        print(f"{step:<25} {description}")

    print(f"\n💡 Key Insight: SKMA enables systematic strategy evolution!")

def main():
    """Run all SKMA demos"""

    demo_skma_operations()
    fetch_strategies_demo()
    save_strategy_demo()
    performance_tracking_demo()
    strategy_lifecycle_demo()

    print("\n" + "=" * 80)
    print("🎯 SKMA SUMMARY")
    print("=" * 80)

    summary_points = [
        "📚 SKMA is the institutional memory of the trading system",
        "🔍 Enables quick discovery of strategies for any market condition",
        "🛡️ Quality control prevents deployment of losing strategies",
        "📊 Continuous performance tracking drives improvement",
        "🔄 Systematic strategy evolution as markets change",
        "⚡ Fast deployment of proven strategies saves development time"
    ]

    for point in summary_points:
        print(f"  {point}")

    print(f"\n✨ Without SKMA: Chaotic, ad-hoc strategy management")
    print(f"✨ With SKMA: Professional, systematic strategy ecosystem")

if __name__ == "__main__":
    main()