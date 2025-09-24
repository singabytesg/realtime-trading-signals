"""
Portfolio Management with CORRECT Option Trading Mechanics

This implements the proper calculation for capped options:
- Nominal exposure determines payout calculation
- Only premium is capital at risk
- Position sizing based on premium budget, not nominal
- Accurate APR based on premium deployed
"""

import json
import logging
import uuid
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== DATA STRUCTURES ====================
@dataclass
class OptionInstrument:
    """Option instrument with costs and parameters"""
    name: str
    duration_days: int
    profit_cap_pct: float
    premium_cost_pct: float

    @property
    def daily_theta(self) -> float:
        """Daily theta decay of premium"""
        return self.premium_cost_pct / self.duration_days


# Available option instruments
OPTION_INSTRUMENTS = {
    "3D_5PCT": OptionInstrument("3D_5PCT", 3, 5.0, 2.2),
    "3D_10PCT": OptionInstrument("3D_10PCT", 3, 10.0, 2.6),
    "7D_5PCT": OptionInstrument("7D_5PCT", 7, 5.0, 2.8),
    "7D_10PCT": OptionInstrument("7D_10PCT", 7, 10.0, 2.8)
}


@dataclass
class Signal:
    """Trading signal with instrument selection"""
    timestamp: str
    signal: int  # -1 for PUT, 0 for neutral, 1 for CALL
    strength: int  # -10 to 10
    instrument: str  # e.g., "7D_5PCT"
    reason: str = ""
    expected_move: float = 0.0
    entry_price: float = 0.0


@dataclass
class PortfolioConfig:
    """Portfolio configuration with CORRECT option semantics"""
    initial_capital_eth: float = 10.0

    # Premium allocation (what we actually risk)
    premium_per_trade_pct: float = 5.0  # % of capital to risk as premium per trade
    max_daily_premium_pct: float = 15.0  # Max % of capital in premiums per day
    max_total_premium_pct: float = 30.0  # Max % of capital in premiums at any time

    # Risk limits
    max_concurrent_positions: int = 10  # Can have many positions with small premiums
    max_drawdown_pct: float = 25.0  # Stop trading if down 25%

    # Position sizing
    use_kelly_sizing: bool = False
    kelly_fraction: float = 0.25  # Conservative Kelly

    def get_premium_budget_eth(self, capital: float, existing_premiums: float = 0) -> float:
        """Calculate how much premium we can spend on a new position"""
        # Check total premium limit
        max_total_premium = capital * (self.max_total_premium_pct / 100)
        remaining_budget = max_total_premium - existing_premiums

        # Check per-trade limit
        per_trade_limit = capital * (self.premium_per_trade_pct / 100)

        return min(remaining_budget, per_trade_limit)


@dataclass
class OptionPosition:
    """Represents an active option position with CORRECT mechanics"""
    position_id: str
    entry_time: str
    expiry_time: str

    # Option details
    instrument_name: str
    is_call: bool  # True for CALL, False for PUT

    # Pricing
    entry_price: float  # Price when option was bought
    nominal_eth: float  # Nominal exposure (for payout calculation)
    premium_paid_eth: float  # Actual capital at risk
    profit_cap_pct: float  # Max profit percentage

    # Tracking
    signal_strength: int
    reason: str = ""

    def calculate_pnl(self, exit_price: float) -> Dict[str, float]:
        """Calculate P&L at exit/expiry"""
        # Calculate price movement
        if self.is_call:
            price_move_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:  # PUT
            price_move_pct = ((self.entry_price - exit_price) / self.entry_price) * 100

        # Cap the movement
        capped_move_pct = min(max(price_move_pct, 0), self.profit_cap_pct)

        # Calculate payout
        payout_eth = self.nominal_eth * (capped_move_pct / 100)

        # Net P&L
        net_pnl_eth = payout_eth - self.premium_paid_eth

        return {
            'price_move_pct': price_move_pct,
            'capped_move_pct': capped_move_pct,
            'payout_eth': payout_eth,
            'net_pnl_eth': net_pnl_eth,
            'return_on_premium_pct': (net_pnl_eth / self.premium_paid_eth * 100) if self.premium_paid_eth > 0 else 0,
            'win': net_pnl_eth > 0
        }


@dataclass
class TradeLog:
    """Complete trade history with CORRECT metrics"""
    trade_id: str

    # Timing
    entry_time: str

    # Option details
    instrument_type: str
    is_call: bool
    signal_strength: int

    # Pricing
    entry_price: float

    # Position sizing (CORRECTED)
    nominal_eth: float  # Exposure for payout
    premium_paid_eth: float  # Capital at risk
    premium_paid_pct: float  # % of portfolio

    # Optional fields with defaults
    exit_time: Optional[str] = None
    exit_price: float = 0

    # Results
    price_move_pct: float = 0
    capped_move_pct: float = 0
    payout_eth: float = 0
    net_pnl_eth: float = 0
    return_on_premium_pct: float = 0

    # Portfolio context
    capital_before: float = 0
    capital_after: float = 0
    portfolio_pct_before: float = 0
    portfolio_pct_after: float = 0
    concurrent_positions: int = 0
    total_premium_deployed: float = 0  # Total premium in all positions

    # Outcome
    win: bool = False
    exit_reason: str = ""


# ==================== PORTFOLIO BACKTESTER ====================
class CorrectedPortfolioBacktester:
    """Backtester with CORRECT option trading mechanics"""

    def __init__(self, config: PortfolioConfig):
        self.config = config
        self.capital_eth = config.initial_capital_eth
        self.initial_capital = config.initial_capital_eth

        self.positions: List[OptionPosition] = []
        self.completed_trades: List[TradeLog] = []
        self.daily_premium_spent: Dict[str, float] = {}

        self.peak_capital = config.initial_capital_eth
        self.in_drawdown = False

    def run_backtest(self, signals: List[Signal], ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
        """Run backtest with correct option mechanics"""

        # Ensure DataFrame has proper datetime index
        if 'timestamp' in ohlcv_df.columns:
            ohlcv_df['timestamp'] = pd.to_datetime(ohlcv_df['timestamp'])
            ohlcv_df.set_index('timestamp', inplace=True)

        matched_count = 0
        processed_count = 0

        # Debug: log signal and data timestamp formats
        if signals and len(ohlcv_df) > 0:
            logger.debug(f"Signal timestamp example: {signals[0].timestamp}")
            logger.debug(f"Data timestamp example: {ohlcv_df.index[0].isoformat()}")

        # Process each timestamp
        for timestamp, row in ohlcv_df.iterrows():
            current_time = timestamp.isoformat()
            current_price = row['close']

            # Check for expired positions
            self._process_expirations(current_time, current_price)

            # Check drawdown
            if self._check_drawdown():
                continue

            # Process signals at this timestamp
            for signal in signals:
                # Try to match timestamps with some flexibility
                signal_ts = signal.timestamp
                if 'T' not in signal_ts and ' ' in signal_ts:
                    # Convert space-separated format to ISO format
                    signal_ts = signal_ts.replace(' ', 'T')

                # Compare timestamps (ignoring timezone for now)
                if signal_ts.split('+')[0] == current_time.split('+')[0] and signal.signal != 0:
                    matched_count += 1
                    if self._process_signal(signal, current_price, current_time):
                        processed_count += 1

        if len(signals) > 0 and matched_count == 0:
            logger.warning(f"No signals matched! Total signals: {len(signals)}")
            logger.warning(f"Signal timestamp example: {signals[0].timestamp}")
            logger.warning(f"Data timestamp example: {ohlcv_df.index[0].isoformat() if len(ohlcv_df) > 0 else 'none'}")
        elif matched_count > 0:
            logger.info(f"Matched {matched_count} signals, processed {processed_count} trades")

        # Close any remaining positions at last price
        if len(ohlcv_df) > 0:
            last_price = ohlcv_df.iloc[-1]['close']
            self._close_all_positions(last_price, ohlcv_df.index[-1].isoformat())

        # Calculate statistics
        return self._calculate_results(ohlcv_df)

    def _process_signal(self, signal: Signal, current_price: float, current_time: str) -> bool:
        """Process a trading signal with correct position sizing"""

        # Check position limits
        if len(self.positions) >= self.config.max_concurrent_positions:
            logger.debug(f"Max positions reached: {len(self.positions)}")
            return False

        # Calculate current premium exposure
        current_premium_exposure = sum(p.premium_paid_eth for p in self.positions)

        # Get premium budget for this trade
        premium_budget = self.config.get_premium_budget_eth(
            self.capital_eth,
            current_premium_exposure
        )

        if premium_budget <= 0:
            logger.debug("No premium budget available")
            return False

        # Get instrument details
        instrument = OPTION_INSTRUMENTS.get(signal.instrument)
        if not instrument:
            logger.warning(f"Unknown instrument: {signal.instrument}")
            return False

        # Check daily premium limit
        trade_date = current_time[:10]
        daily_spent = self.daily_premium_spent.get(trade_date, 0)
        daily_limit = self.capital_eth * (self.config.max_daily_premium_pct / 100)

        if daily_spent >= daily_limit:
            logger.debug(f"Daily premium limit reached: {daily_spent:.4f}/{daily_limit:.4f}")
            return False

        # Calculate position size based on signal strength (optional)
        strength_multiplier = min(abs(signal.strength) / 10.0, 1.0) if signal.strength != 0 else 0.5
        adjusted_budget = premium_budget * strength_multiplier

        # Ensure minimum position size
        min_premium = self.capital_eth * 0.001  # 0.1% minimum
        if adjusted_budget < min_premium:
            return False

        # Calculate nominal exposure from premium budget
        # Premium = Nominal * (Premium_Rate/100)
        # So: Nominal = Premium / (Premium_Rate/100)
        nominal_eth = adjusted_budget / (instrument.premium_cost_pct / 100)

        # Actual premium to pay
        premium_eth = nominal_eth * (instrument.premium_cost_pct / 100)

        # Ensure we don't exceed budget due to rounding
        if premium_eth > premium_budget:
            nominal_eth = premium_budget / (instrument.premium_cost_pct / 100)
            premium_eth = premium_budget

        # Deduct premium from capital
        self.capital_eth -= premium_eth

        # Update daily spending
        self.daily_premium_spent[trade_date] = daily_spent + premium_eth

        # Calculate expiry
        entry_dt = datetime.fromisoformat(current_time.replace('Z', '+00:00'))
        expiry_dt = entry_dt + timedelta(days=instrument.duration_days)

        # Create position
        position = OptionPosition(
            position_id=str(uuid.uuid4())[:8],
            entry_time=current_time,
            expiry_time=expiry_dt.isoformat(),
            instrument_name=signal.instrument,
            is_call=(signal.signal > 0),
            entry_price=current_price,
            nominal_eth=nominal_eth,
            premium_paid_eth=premium_eth,
            profit_cap_pct=instrument.profit_cap_pct,
            signal_strength=signal.strength,
            reason=signal.reason
        )

        self.positions.append(position)

        # Create trade log entry
        trade_log = TradeLog(
            trade_id=position.position_id,
            entry_time=current_time,
            instrument_type=signal.instrument,
            is_call=(signal.signal > 0),
            signal_strength=signal.strength,
            entry_price=current_price,
            nominal_eth=nominal_eth,
            premium_paid_eth=premium_eth,
            premium_paid_pct=(premium_eth / self.initial_capital) * 100,
            capital_before=self.capital_eth + premium_eth,
            capital_after=self.capital_eth,
            portfolio_pct_before=((self.capital_eth + premium_eth) / self.initial_capital) * 100,
            portfolio_pct_after=(self.capital_eth / self.initial_capital) * 100,
            concurrent_positions=len(self.positions),
            total_premium_deployed=sum(p.premium_paid_eth for p in self.positions)
        )

        self.completed_trades.append(trade_log)

        logger.info(f"Opened {signal.instrument} {'CALL' if signal.signal > 0 else 'PUT'}: "
                   f"Nominal={nominal_eth:.3f} ETH, Premium={premium_eth:.4f} ETH, "
                   f"Signal={signal.strength}")

        return True

    def _process_expirations(self, current_time: str, current_price: float):
        """Process expired positions"""

        expired = []
        for position in self.positions:
            if current_time >= position.expiry_time:
                expired.append(position)

        for position in expired:
            self._close_position(position, current_price, current_time, "expiry")

    def _close_position(self, position: OptionPosition, exit_price: float,
                        exit_time: str, reason: str):
        """Close a position with correct P&L calculation"""

        # Calculate P&L
        pnl_result = position.calculate_pnl(exit_price)

        # Update capital
        self.capital_eth += pnl_result['payout_eth']

        # Update peak for drawdown calculation
        if self.capital_eth > self.peak_capital:
            self.peak_capital = self.capital_eth

        # Update trade log
        for trade in self.completed_trades:
            if trade.trade_id == position.position_id:
                trade.exit_time = exit_time
                trade.exit_price = exit_price
                trade.price_move_pct = pnl_result['price_move_pct']
                trade.capped_move_pct = pnl_result['capped_move_pct']
                trade.payout_eth = pnl_result['payout_eth']
                trade.net_pnl_eth = pnl_result['net_pnl_eth']
                trade.return_on_premium_pct = pnl_result['return_on_premium_pct']
                trade.capital_after = self.capital_eth
                trade.portfolio_pct_after = (self.capital_eth / self.initial_capital) * 100
                trade.win = pnl_result['win']
                trade.exit_reason = reason
                break

        # Remove from active positions
        self.positions.remove(position)

        logger.info(f"Closed {position.instrument_name} {'CALL' if position.is_call else 'PUT'}: "
                   f"Move={pnl_result['price_move_pct']:.2f}% (capped at {pnl_result['capped_move_pct']:.2f}%), "
                   f"Net P&L={pnl_result['net_pnl_eth']:.4f} ETH, "
                   f"Return on Premium={pnl_result['return_on_premium_pct']:.1f}%")

    def _close_all_positions(self, exit_price: float, exit_time: str):
        """Close all remaining positions"""
        positions_copy = self.positions.copy()
        for position in positions_copy:
            self._close_position(position, exit_price, exit_time, "end_of_data")

    def _check_drawdown(self) -> bool:
        """Check if in drawdown"""
        current_drawdown = ((self.peak_capital - self.capital_eth) / self.peak_capital) * 100

        if current_drawdown > self.config.max_drawdown_pct:
            if not self.in_drawdown:
                logger.warning(f"Entering drawdown mode: {current_drawdown:.1f}% > {self.config.max_drawdown_pct}%")
                self.in_drawdown = True
            return True

        if self.in_drawdown and current_drawdown < (self.config.max_drawdown_pct * 0.7):
            logger.info(f"Exiting drawdown mode: {current_drawdown:.1f}%")
            self.in_drawdown = False

        return False

    def _calculate_results(self, ohlcv_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate comprehensive results with CORRECT metrics"""

        completed = [t for t in self.completed_trades if t.exit_time is not None]

        if not completed:
            return self._empty_results()

        # Win/Loss statistics
        winning_trades = [t for t in completed if t.win]
        losing_trades = [t for t in completed if not t.win]

        # Calculate returns
        total_premium_paid = sum(t.premium_paid_eth for t in completed)
        total_net_pnl = sum(t.net_pnl_eth for t in completed)
        total_return_pct = (total_net_pnl / self.initial_capital) * 100

        # Time calculations
        first_trade = min(completed, key=lambda t: t.entry_time)
        last_trade = max(completed, key=lambda t: t.exit_time or t.entry_time)

        first_date = pd.to_datetime(first_trade.entry_time)
        last_date = pd.to_datetime(last_trade.exit_time or last_trade.entry_time)
        trading_days = (last_date - first_date).days

        if trading_days == 0:
            trading_days = 1

        # APR Calculations (CORRECTED)

        # 1. Simple APR (based on total capital)
        simple_apr = (total_return_pct / trading_days) * 365

        # 2. Premium-Efficient APR (based on premium deployed)
        if total_premium_paid > 0:
            premium_return_pct = (total_net_pnl / total_premium_paid) * 100
            premium_efficient_apr = (premium_return_pct / trading_days) * 365
        else:
            premium_efficient_apr = 0

        # 3. Average Capital Deployed
        avg_premium_deployed = np.mean([t.total_premium_deployed for t in completed])
        max_premium_deployed = max([t.total_premium_deployed for t in completed])

        # Risk metrics
        returns = [t.net_pnl_eth for t in completed]
        if len(returns) > 1:
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0

        # Drawdown calculation
        cumulative_returns = []
        running_capital = self.initial_capital
        peak = self.initial_capital
        max_dd = 0

        for trade in sorted(completed, key=lambda t: t.exit_time or t.entry_time):
            running_capital = trade.capital_after
            cumulative_returns.append(running_capital)
            if running_capital > peak:
                peak = running_capital
            dd = ((peak - running_capital) / peak) * 100
            max_dd = max(max_dd, dd)

        # Compile results
        results = {
            'statistics': {
                # Trade counts
                'total_trades': len(completed),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate_pct': (len(winning_trades) / len(completed) * 100) if completed else 0,

                # Returns (CORRECTED)
                'total_net_pnl_eth': total_net_pnl,
                'total_return_pct': total_return_pct,
                'final_capital_eth': self.capital_eth,

                # Premium metrics (NEW)
                'total_premium_paid_eth': total_premium_paid,
                'total_payout_received_eth': sum(t.payout_eth for t in completed),
                'avg_premium_per_trade_eth': total_premium_paid / len(completed),
                'return_on_premium_pct': (total_net_pnl / total_premium_paid * 100) if total_premium_paid > 0 else 0,

                # Win/Loss metrics
                'avg_win_pct': np.mean([t.return_on_premium_pct for t in winning_trades]) if winning_trades else 0,
                'avg_loss_pct': np.mean([t.return_on_premium_pct for t in losing_trades]) if losing_trades else 0,
                'avg_win_eth': np.mean([t.net_pnl_eth for t in winning_trades]) if winning_trades else 0,
                'avg_loss_eth': np.mean([t.net_pnl_eth for t in losing_trades]) if losing_trades else 0,

                # Risk metrics
                'max_drawdown_pct': max_dd,
                'sharpe_ratio': sharpe_ratio,

                # APR metrics (CORRECTED)
                'simple_apr': simple_apr,  # Based on total capital
                'premium_efficient_apr': premium_efficient_apr,  # Based on premium deployed

                # Capital efficiency (CORRECTED)
                'avg_premium_deployed_eth': avg_premium_deployed,
                'max_premium_deployed_eth': max_premium_deployed,
                'avg_premium_deployed_pct': (avg_premium_deployed / self.initial_capital) * 100,
                'max_premium_deployed_pct': (max_premium_deployed / self.initial_capital) * 100,
                'avg_nominal_exposure_eth': np.mean([t.nominal_eth for t in completed]),

                # Time metrics
                'trading_days': trading_days,
                'trades_per_day': len(completed) / trading_days if trading_days > 0 else 0,

                # Instrument breakdown
                'instrument_stats': self._calculate_instrument_stats(completed)
            },
            'trade_logs': [self._format_trade_log(t) for t in completed],
            'capital_curve': cumulative_returns
        }

        return results

    def _calculate_instrument_stats(self, trades: List[TradeLog]) -> Dict[str, Any]:
        """Calculate statistics by instrument type"""
        stats = {}

        for instrument_name in OPTION_INSTRUMENTS.keys():
            instrument_trades = [t for t in trades if t.instrument_type == instrument_name]
            if instrument_trades:
                wins = [t for t in instrument_trades if t.win]
                stats[instrument_name] = {
                    'count': len(instrument_trades),
                    'wins': len(wins),
                    'win_rate': (len(wins) / len(instrument_trades)) * 100,
                    'total_premium_eth': sum(t.premium_paid_eth for t in instrument_trades),
                    'total_pnl_eth': sum(t.net_pnl_eth for t in instrument_trades),
                    'avg_return_on_premium': np.mean([t.return_on_premium_pct for t in instrument_trades])
                }

        return stats

    def _format_trade_log(self, trade: TradeLog) -> Dict[str, Any]:
        """Format trade log for output"""
        return {
            'trade_id': trade.trade_id,
            'entry_time': trade.entry_time,
            'exit_time': trade.exit_time,
            'instrument': trade.instrument_type,
            'type': 'CALL' if trade.is_call else 'PUT',
            'signal_strength': trade.signal_strength,

            # Pricing
            'entry_price': round(trade.entry_price, 2),
            'exit_price': round(trade.exit_price, 2),

            # Position (CORRECTED)
            'nominal_eth': round(trade.nominal_eth, 3),
            'premium_paid_eth': round(trade.premium_paid_eth, 4),
            'premium_paid_pct': round(trade.premium_paid_pct, 2),

            # Results
            'price_move_pct': round(trade.price_move_pct, 2),
            'capped_move_pct': round(trade.capped_move_pct, 2),
            'payout_eth': round(trade.payout_eth, 4),
            'net_pnl_eth': round(trade.net_pnl_eth, 4),
            'return_on_premium_pct': round(trade.return_on_premium_pct, 1),

            # Context
            'capital_before': round(trade.capital_before, 3),
            'capital_after': round(trade.capital_after, 3),
            'concurrent_positions': trade.concurrent_positions,
            'total_premium_deployed_eth': round(trade.total_premium_deployed, 4),

            # Outcome
            'win': trade.win,
            'exit_reason': trade.exit_reason
        }

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure"""
        return {
            'statistics': {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate_pct': 0,
                'total_net_pnl_eth': 0,
                'total_return_pct': 0,
                'final_capital_eth': self.capital_eth,
                'total_premium_paid_eth': 0,
                'total_payout_received_eth': 0,
                'avg_premium_per_trade_eth': 0,
                'return_on_premium_pct': 0,
                'avg_win_pct': 0,
                'avg_loss_pct': 0,
                'avg_win_eth': 0,
                'avg_loss_eth': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
                'simple_apr': 0,
                'premium_efficient_apr': 0,
                'avg_premium_deployed_eth': 0,
                'max_premium_deployed_eth': 0,
                'avg_premium_deployed_pct': 0,
                'max_premium_deployed_pct': 0,
                'avg_nominal_exposure_eth': 0,
                'trading_days': 0,
                'trades_per_day': 0,
                'instrument_stats': {}
            },
            'trade_logs': [],
            'capital_curve': []
        }


# ==================== HELPER FUNCTIONS ====================
def load_market_data(file_path: str) -> pd.DataFrame:
    """Load and prepare market data"""
    with open(file_path, 'r') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def demonstrate_corrected_system():
    """Demonstrate the corrected portfolio management system"""

    print("=" * 80)
    print("CORRECTED OPTION PORTFOLIO MANAGEMENT SYSTEM")
    print("=" * 80)

    # Example signals (would come from your strategy)
    signals = [
        Signal(
            timestamp="2025-09-02T00:00:00+00:00",
            signal=-1,  # PUT
            strength=-7,
            instrument="7D_5PCT",
            reason="Strong bearish signal",
            entry_price=4472.60
        )
    ]

    # Create sample OHLCV data
    ohlcv_data = pd.DataFrame([
        {"timestamp": "2025-09-02T00:00:00+00:00", "close": 4472.60, "high": 4480, "low": 4470, "open": 4475},
        {"timestamp": "2025-09-03T00:00:00+00:00", "close": 4400.00, "high": 4475, "low": 4395, "open": 4472},
        {"timestamp": "2025-09-04T00:00:00+00:00", "close": 4350.00, "high": 4410, "low": 4340, "open": 4400},
        {"timestamp": "2025-09-05T00:00:00+00:00", "close": 4300.00, "high": 4360, "low": 4290, "open": 4350},
        {"timestamp": "2025-09-06T00:00:00+00:00", "close": 4250.00, "high": 4310, "low": 4240, "open": 4300},
        {"timestamp": "2025-09-07T00:00:00+00:00", "close": 4200.00, "high": 4260, "low": 4190, "open": 4250},
        {"timestamp": "2025-09-08T00:00:00+00:00", "close": 4189.75, "high": 4210, "low": 4180, "open": 4200},
        {"timestamp": "2025-09-09T00:00:00+00:00", "close": 4195.00, "high": 4200, "low": 4185, "open": 4189}
    ])

    # Configure portfolio with correct semantics
    config = PortfolioConfig(
        initial_capital_eth=10.0,
        premium_per_trade_pct=5.0,  # Risk 5% of capital as premium per trade
        max_daily_premium_pct=15.0,  # Max 15% in premiums per day
        max_total_premium_pct=30.0,  # Max 30% in premiums total
        max_concurrent_positions=10,
        max_drawdown_pct=25.0
    )

    print("\n📊 PORTFOLIO CONFIGURATION:")
    print(f"  Initial Capital: {config.initial_capital_eth} ETH")
    print(f"  Premium per Trade: {config.premium_per_trade_pct}% of capital")
    print(f"  Max Daily Premium: {config.max_daily_premium_pct}% of capital")
    print(f"  Max Total Premium: {config.max_total_premium_pct}% of capital")
    print(f"  Max Positions: {config.max_concurrent_positions}")

    # Run backtest
    backtester = CorrectedPortfolioBacktester(config)
    results = backtester.run_backtest(signals, ohlcv_data)

    # Display results
    stats = results['statistics']

    print("\n📈 RESULTS:")
    print(f"  Total Trades: {stats['total_trades']}")
    print(f"  Win Rate: {stats['win_rate_pct']:.1f}%")

    print("\n💰 CAPITAL & RETURNS:")
    print(f"  Final Capital: {stats['final_capital_eth']:.4f} ETH")
    print(f"  Total Return: {stats['total_return_pct']:.2f}%")
    print(f"  Simple APR: {stats['simple_apr']:.2f}%")
    print(f"  Premium-Efficient APR: {stats['premium_efficient_apr']:.2f}%")

    print("\n🎯 PREMIUM METRICS:")
    print(f"  Total Premium Paid: {stats['total_premium_paid_eth']:.4f} ETH")
    print(f"  Total Payout Received: {stats['total_payout_received_eth']:.4f} ETH")
    print(f"  Return on Premium: {stats['return_on_premium_pct']:.1f}%")
    print(f"  Avg Premium Deployed: {stats['avg_premium_deployed_pct']:.1f}% of capital")

    # Show trade details
    if results['trade_logs']:
        print("\n📝 TRADE DETAILS:")
        for trade in results['trade_logs']:
            print(f"\n  Trade {trade['trade_id']}:")
            print(f"    Type: {trade['instrument']} {trade['type']}")
            print(f"    Entry: ${trade['entry_price']:.2f} → Exit: ${trade['exit_price']:.2f}")
            print(f"    Nominal: {trade['nominal_eth']:.3f} ETH")
            print(f"    Premium Paid: {trade['premium_paid_eth']:.4f} ETH ({trade['premium_paid_pct']:.2f}%)")
            print(f"    Price Move: {trade['price_move_pct']:.2f}% (capped at {trade['capped_move_pct']:.2f}%)")
            print(f"    Payout: {trade['payout_eth']:.4f} ETH")
            print(f"    Net P&L: {trade['net_pnl_eth']:.4f} ETH")
            print(f"    Return on Premium: {trade['return_on_premium_pct']:.1f}%")
            print(f"    Result: {'WIN ✅' if trade['win'] else 'LOSS ❌'}")


if __name__ == "__main__":
    demonstrate_corrected_system()