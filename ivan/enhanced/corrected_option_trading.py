"""
Corrected Option Trading Mechanics

This demonstrates the CORRECT way to calculate P&L for capped options:
- Nominal position is the exposure amount (e.g., 1 ETH worth at entry price)
- Premium is paid upfront as a percentage of nominal
- Payout is based on price movement, capped at the option's limit
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class OptionTrade:
    """Represents a single option trade with correct mechanics"""
    nominal_eth: float  # Nominal exposure (e.g., 1 ETH)
    entry_price: float  # Entry price in USD
    exit_price: float   # Exit price in USD
    is_call: bool      # True for CALL, False for PUT
    profit_cap_pct: float  # Cap percentage (e.g., 5% or 10%)
    premium_pct: float  # Premium cost as % of nominal (e.g., 2.8%)

    def calculate_pnl(self) -> Dict[str, float]:
        """Calculate P&L with correct option mechanics"""

        # 1. Premium paid upfront
        premium_eth = self.nominal_eth * (self.premium_pct / 100)

        # 2. Calculate price movement
        if self.is_call:
            # CALL: profit when price goes up
            price_move_pct = ((self.exit_price - self.entry_price) / self.entry_price) * 100
        else:
            # PUT: profit when price goes down
            price_move_pct = ((self.entry_price - self.exit_price) / self.entry_price) * 100

        # 3. Cap the movement at the option's limit
        capped_move_pct = min(max(price_move_pct, 0), self.profit_cap_pct)

        # 4. Calculate payout in ETH
        payout_eth = self.nominal_eth * (capped_move_pct / 100)

        # 5. Net P&L = Payout - Premium
        net_pnl_eth = payout_eth - premium_eth

        # 6. Return on premium (what matters for capital efficiency)
        return_on_premium_pct = (net_pnl_eth / premium_eth) * 100 if premium_eth > 0 else 0

        return {
            'nominal_eth': self.nominal_eth,
            'premium_paid_eth': premium_eth,
            'price_move_pct': price_move_pct,
            'capped_move_pct': capped_move_pct,
            'payout_eth': payout_eth,
            'net_pnl_eth': net_pnl_eth,
            'return_on_premium_pct': return_on_premium_pct,
            'win': net_pnl_eth > 0
        }


def demonstrate_correct_calculation():
    """Show the correct calculation for your example trade"""

    print("=" * 80)
    print("CORRECT OPTION TRADING CALCULATION")
    print("=" * 80)

    # Your example trade: PUT option
    trade = OptionTrade(
        nominal_eth=1.0,        # 1 ETH nominal exposure
        entry_price=4472.60,    # Entry at $4,472.60
        exit_price=4189.75,     # Exit at $4,189.75
        is_call=False,          # PUT option (profit on down move)
        profit_cap_pct=5.0,     # 5% cap (7D_5PCT option)
        premium_pct=2.8         # 2.8% premium cost
    )

    result = trade.calculate_pnl()

    print("\n📊 TRADE DETAILS:")
    print(f"  Type: {'CALL' if trade.is_call else 'PUT'} Option")
    print(f"  Instrument: 7D_5PCT (7-day, 5% cap)")
    print(f"  Nominal Position: {trade.nominal_eth} ETH")
    print(f"  Entry Price: ${trade.entry_price:,.2f}")
    print(f"  Exit Price: ${trade.exit_price:,.2f}")

    print("\n💰 CALCULATION:")
    print(f"  1. Premium Paid: {result['premium_paid_eth']:.4f} ETH ({trade.premium_pct}% of nominal)")
    print(f"  2. Price Movement: {result['price_move_pct']:.2f}% {'down' if not trade.is_call else 'up'}")
    print(f"  3. Capped at: {result['capped_move_pct']:.2f}% (max {trade.profit_cap_pct}%)")
    print(f"  4. Payout: {result['payout_eth']:.4f} ETH")
    print(f"  5. Net P&L: {result['net_pnl_eth']:.4f} ETH")
    print(f"  6. Return on Premium: {result['return_on_premium_pct']:.1f}%")
    print(f"  7. Result: {'WIN ✅' if result['win'] else 'LOSS ❌'}")

    # Show comparison with incorrect calculation
    print("\n⚠️  INCORRECT CALCULATION (what the system currently does):")
    incorrect_position_size = 2.181  # System uses this as "position size"
    incorrect_premium = incorrect_position_size * 0.028  # 2.8% of position
    incorrect_pnl = 0.048  # What system reported
    print(f"  Position Size: {incorrect_position_size:.3f} ETH")
    print(f"  Premium: {incorrect_premium:.4f} ETH")
    print(f"  P&L: {incorrect_pnl:.3f} ETH")

    print("\n🔍 KEY DIFFERENCES:")
    print("  1. Nominal vs Position Size:")
    print(f"     - CORRECT: 1 ETH nominal exposure, {result['premium_paid_eth']:.4f} ETH capital at risk")
    print(f"     - INCORRECT: {incorrect_position_size:.3f} ETH 'position size' (mixing concepts)")
    print("  2. Capital at Risk:")
    print(f"     - CORRECT: Only premium ({result['premium_paid_eth']:.4f} ETH) is at risk")
    print(f"     - INCORRECT: Treating entire position as at risk")
    print("  3. Return Calculation:")
    print(f"     - CORRECT: {result['return_on_premium_pct']:.1f}% return on {result['premium_paid_eth']:.4f} ETH premium")
    print(f"     - INCORRECT: Unclear what the return represents")


def show_portfolio_impact():
    """Show how this affects portfolio management"""

    print("\n" + "=" * 80)
    print("PORTFOLIO MANAGEMENT IMPLICATIONS")
    print("=" * 80)

    initial_capital = 10.0  # 10 ETH portfolio

    print("\n📈 CORRECT APPROACH (Premium-Based):")
    print(f"  Initial Capital: {initial_capital} ETH")
    print(f"  Position Sizing Strategy: Allocate % of capital as PREMIUM")
    print(f"  Example: 5% allocation = 0.5 ETH premium budget")
    print(f"  With 2.8% premium rate: 0.5 / 0.028 = 17.86 ETH nominal exposure")
    print(f"  Max Loss: 0.5 ETH (5% of portfolio)")
    print(f"  Max Gain: 0.893 ETH (17.86 × 5% cap)")

    print("\n📉 INCORRECT APPROACH (Current System):")
    print(f"  Treats 'position size' as capital allocation")
    print(f"  Mixes nominal exposure with capital at risk")
    print(f"  Overestimates capital usage")
    print(f"  Underestimates returns")

    print("\n💡 RECOMMENDED FIX:")
    print("  1. Track 'nominal_eth' (exposure) separately from 'premium_eth' (cost)")
    print("  2. Position sizing should limit PREMIUM, not nominal")
    print("  3. Capital at risk = sum of premiums paid")
    print("  4. APR calculation based on premium capital, not nominal")


if __name__ == "__main__":
    demonstrate_correct_calculation()
    show_portfolio_impact()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
The key insight: In options trading, you're not putting up the full nominal
amount as capital. You only risk the premium. The nominal is just the
exposure amount used to calculate the payout.

Current system needs refactoring to:
1. Separate nominal_eth (exposure) from premium_eth (capital at risk)
2. Calculate position sizes based on premium budget, not nominal
3. Track actual capital deployment (sum of premiums)
4. Calculate returns relative to premium paid, not nominal
""")