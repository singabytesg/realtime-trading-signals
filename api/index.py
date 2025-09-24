"""
Real-time Trading Signal System
A standalone app for generating live trading signals using DSL strategies
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import websockets
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from collections import deque

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Real-time Trading Signals", version="1.0.0")

# ==================== CORE MODELS ====================

@dataclass
class TradingSignal:
    timestamp: datetime
    signal_type: str  # "CALL", "PUT", "NEUTRAL"
    strength: int  # -7, -3, 0, 3, 7
    price: float
    rule_triggered: str
    instrument_type: str
    confidence: float
    expected_move: float

@dataclass
class TradeExecution:
    id: str
    signal: TradingSignal
    entry_price: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    status: str = "OPEN"  # OPEN, CLOSED, EXPIRED

# ==================== TECHNICAL INDICATORS ====================

class TechnicalIndicators:
    @staticmethod
    def sma(data: deque, period: int) -> float:
        if len(data) < period:
            return np.nan
        return np.mean(list(data)[-period:])

    @staticmethod
    def rsi(prices: deque, period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0

        prices_list = list(prices)[-period-1:]
        deltas = np.diff(prices_list)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(prices: deque, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        if len(prices) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0}

        prices_array = np.array(list(prices))

        # Simple approximation of EMA
        ema_fast = np.mean(prices_array[-fast:])
        ema_slow = np.mean(prices_array[-slow:])

        macd_line = ema_fast - ema_slow
        signal_line = macd_line  # Simplified
        histogram = macd_line - signal_line

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram
        }

# ==================== OPTION INSTRUMENTS ====================

class OptionInstruments:
    INSTRUMENTS = {
        "3D_5PCT": {
            "duration_days": 3,
            "profit_cap_pct": 5.0,
            "premium_cost_pct": 2.2,
            "description": "3-day option with 5% profit cap"
        },
        "3D_10PCT": {
            "duration_days": 3,
            "profit_cap_pct": 10.0,
            "premium_cost_pct": 2.6,
            "description": "3-day option with 10% profit cap"
        },
        "7D_5PCT": {
            "duration_days": 7,
            "profit_cap_pct": 5.0,
            "premium_cost_pct": 2.8,
            "description": "7-day option with 5% profit cap"
        },
        "7D_10PCT": {
            "duration_days": 7,
            "profit_cap_pct": 10.0,
            "premium_cost_pct": 2.8,
            "description": "7-day option with 10% profit cap (best risk/reward)"
        }
    }

    @classmethod
    def get_instrument(cls, instrument_type: str) -> Dict:
        return cls.INSTRUMENTS.get(instrument_type, cls.INSTRUMENTS["3D_5PCT"])

    @classmethod
    def select_optimal_instrument(cls, signal_strength: int, volatility: float,
                                 expected_move: float, high_vol_threshold: float = 3.5) -> str:
        """
        Select optimal instrument based on signal strength, volatility, and expected move
        This implements the exact logic from your winning strategy
        """
        abs_strength = abs(signal_strength)

        if abs_strength >= 7:
            # Strong signal - use higher profit cap
            if volatility > high_vol_threshold:
                # High volatility - shorter duration
                return "3D_10PCT" if expected_move > 7 else "3D_5PCT"
            else:
                # Low volatility - can use longer duration
                return "7D_10PCT" if expected_move > 5 else "7D_5PCT"
        else:
            # Moderate signal (strength 3) - conservative approach
            if volatility > high_vol_threshold:
                # High volatility - stick to shorter, cheaper options
                return "3D_5PCT"
            else:
                # Low volatility - still conservative
                return "7D_5PCT" if expected_move < 5 else "3D_5PCT"

# ==================== DSL STRATEGY EXECUTOR ====================

class SimpleDSLExecutor:
    def __init__(self, strategy_config: Dict):
        self.config = strategy_config
        self.price_history = deque(maxlen=100)
        self.indicators = TechnicalIndicators()
        self.option_instruments = OptionInstruments()

        # Load the winning strategy configuration (no hardcoded instruments)
        self.winning_strategy = {
            "constants": {
                "rsi_oversold": 30,
                "macd_fast": 12,
                "macd_slow": 21,
                "macd_signal": 7,
                "sma_short_period": 15,
                "sma_long_period": 20,
                "atr_period": 10,
                "high_vol_threshold": 3.5
            },
            "rules": [
                {
                    "name": "strong_bear_breakdown",
                    "conditions": [
                        "close < sma_short",
                        "sma_short < sma_long",
                        "macd_hist < -0.5",
                        "rsi < 40"
                    ],
                    "signal": {"type": "PUT", "strength": -7},
                    "time_horizon_days": 7  # Expect sustained move
                },
                {
                    "name": "moderate_bear_signal",
                    "conditions": [
                        "macd_line < macd_signal",
                        "close < sma_long",
                        "volatility < 70"
                    ],
                    "signal": {"type": "PUT", "strength": -3},
                    "time_horizon_days": 3  # Shorter move expected
                },
                {
                    "name": "oversold_bounce",
                    "conditions": [
                        "rsi < 30",
                        "macd_line > macd_signal"
                    ],
                    "signal": {"type": "CALL", "strength": 3},
                    "time_horizon_days": 3  # Quick bounce expected
                }
            ]
        }

    def process_price_update(self, price: float, timestamp: datetime) -> Optional[TradingSignal]:
        self.price_history.append(price)

        if len(self.price_history) < 20:
            return None

        # Calculate indicators
        sma_short = self.indicators.sma(self.price_history, self.winning_strategy["constants"]["sma_short_period"])
        sma_long = self.indicators.sma(self.price_history, self.winning_strategy["constants"]["sma_long_period"])
        rsi = self.indicators.rsi(self.price_history)
        macd_data = self.indicators.macd(self.price_history)

        current_price = price
        volatility = self._calculate_volatility()

        # Check each rule
        for rule in self.winning_strategy["rules"]:
            indicators_dict = {
                "close": current_price,
                "sma_short": sma_short,
                "sma_long": sma_long,
                "rsi": rsi,
                "macd_line": macd_data["macd"],
                "macd_signal": macd_data["signal"],
                "macd_hist": macd_data["histogram"],
                "volatility": volatility
            }

            if self._evaluate_rule(rule, indicators_dict):
                # Calculate expected move percentage
                expected_move_pct = abs(macd_data["histogram"]) * 2 + (volatility / 10)

                # Select optimal instrument based on signal strength, volatility, and expected move
                optimal_instrument = self.option_instruments.select_optimal_instrument(
                    signal_strength=rule["signal"]["strength"],
                    volatility=volatility,
                    expected_move=expected_move_pct,
                    high_vol_threshold=self.winning_strategy["constants"]["high_vol_threshold"]
                )

                return TradingSignal(
                    timestamp=timestamp,
                    signal_type=rule["signal"]["type"],
                    strength=rule["signal"]["strength"],
                    price=current_price,
                    rule_triggered=rule["name"],
                    instrument_type=optimal_instrument,
                    confidence=0.8,
                    expected_move=expected_move_pct
                )

        return None

    def _evaluate_rule(self, rule: Dict, indicators: Dict) -> bool:
        for condition in rule["conditions"]:
            if not self._evaluate_condition(condition, indicators):
                return False
        return True

    def _evaluate_condition(self, condition: str, indicators: Dict) -> bool:
        # Simple condition evaluator
        try:
            # Replace indicator names with values
            condition_eval = condition
            for key, value in indicators.items():
                if key in condition_eval and not pd.isna(value):
                    condition_eval = condition_eval.replace(key, str(value))

            # Basic condition evaluation (simplified)
            if ">" in condition_eval:
                left, right = condition_eval.split(">")
                return float(left.strip()) > float(right.strip())
            elif "<" in condition_eval:
                left, right = condition_eval.split("<")
                return float(left.strip()) < float(right.strip())

        except Exception as e:
            logger.error(f"Error evaluating condition {condition}: {e}")
            return False

        return False

    def _calculate_volatility(self) -> float:
        if len(self.price_history) < 10:
            return 50.0

        returns = np.diff(list(self.price_history)[-10:]) / list(self.price_history)[-10:-1]
        return np.std(returns) * 100 * np.sqrt(252)  # Annualized volatility

# ==================== DERIBIT WEBSOCKET CLIENT ====================

class DeribitWebSocketClient:
    def __init__(self, signal_callback):
        self.ws_url = "wss://www.deribit.com/ws/api/v2"
        self.signal_callback = signal_callback
        self.websocket = None
        self.is_connected = False

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.ws_url)
            self.is_connected = True
            logger.info("Connected to Deribit WebSocket")

            # Subscribe to ETH perpetual price updates
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "public/subscribe",
                "params": {
                    "channels": ["ticker.ETH-PERPETUAL.100ms"]
                }
            }

            await self.websocket.send(json.dumps(subscribe_msg))
            logger.info("Subscribed to ETH-PERPETUAL ticker")

        except Exception as e:
            logger.error(f"Failed to connect to Deribit: {e}")
            self.is_connected = False

    async def listen(self):
        if not self.websocket:
            return

        try:
            async for message in self.websocket:
                data = json.loads(message)

                if "params" in data and "data" in data["params"]:
                    ticker_data = data["params"]["data"]
                    price = ticker_data.get("last_price")

                    if price:
                        await self.signal_callback(price, datetime.now())

        except websockets.exceptions.ConnectionClosed:
            logger.warning("Deribit WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in Deribit WebSocket: {e}")
            self.is_connected = False

    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False

# ==================== SIGNAL MANAGER ====================

class SignalManager:
    def __init__(self):
        self.dsl_executor = SimpleDSLExecutor({})
        self.active_connections: List[WebSocket] = []
        self.signal_history: List[TradingSignal] = []
        self.trade_history: List[TradeExecution] = []
        self.current_price = 0.0
        self.stats = {
            "total_signals": 0,
            "active_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0
        }

    async def process_price_update(self, price: float, timestamp: datetime):
        self.current_price = price

        signal = self.dsl_executor.process_price_update(price, timestamp)

        if signal and signal.signal_type != "NEUTRAL":
            self.signal_history.append(signal)
            self.stats["total_signals"] += 1

            logger.info(f"🚨 NEW SIGNAL: {signal.signal_type} {signal.strength} @ ${price:.2f}")

            # Broadcast to all connected WebSocket clients
            signal_data = {
                "type": "signal",
                "data": asdict(signal),
                "stats": self.stats,
                "current_price": price
            }

            await self._broadcast(signal_data)

    async def connect_websocket(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

        # Send initial data
        initial_data = {
            "type": "init",
            "data": {
                "current_price": self.current_price,
                "signal_history": [asdict(s) for s in self.signal_history[-10:]],
                "stats": self.stats
            }
        }
        await websocket.send_text(json.dumps(initial_data, default=str))

    def disconnect_websocket(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def _broadcast(self, data: Dict):
        if not self.active_connections:
            return

        message = json.dumps(data, default=str)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.active_connections.remove(connection)

# ==================== GLOBAL INSTANCES ====================

signal_manager = SignalManager()
deribit_client = None

# ==================== WEBSOCKET ENDPOINTS ====================
# WebSockets commented out for Vercel compatibility
# Vercel serverless functions have limited WebSocket support

# @app.websocket("/ws/signals")
# async def websocket_signals(websocket: WebSocket):
#     await signal_manager.connect_websocket(websocket)
#     try:
#         while True:
#             # Keep connection alive
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         signal_manager.disconnect_websocket(websocket)

# ==================== REST ENDPOINTS ====================

@app.get("/")
async def get_dashboard():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>Real-time Trading Signals</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2196F3; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 24px; font-weight: bold; color: #2196F3; }
        .stat-label { color: #666; margin-top: 5px; }
        .signals { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .signal { padding: 15px; border-left: 4px solid #4CAF50; margin: 10px 0; background: #f9f9f9; }
        .signal.PUT { border-color: #f44336; }
        .signal.CALL { border-color: #4CAF50; }
        .signal-header { font-weight: bold; color: #333; }
        .signal-details { color: #666; margin-top: 5px; }
        .status { display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-size: 12px; }
        .status.connected { background: #4CAF50; }
        .status.disconnected { background: #f44336; }
        .price-display { font-size: 32px; font-weight: bold; color: #2196F3; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Real-time Trading Signals</h1>
            <p>Live DSL Strategy Execution with Deribit Data Feed</p>
            <div class="price-display" id="current-price">$0.00</div>
            <span class="status" id="connection-status">Disconnected</span>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="total-signals">0</div>
                <div class="stat-label">Total Signals</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="active-trades">0</div>
                <div class="stat-label">Active Trades</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="win-rate">0%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="total-pnl">$0.00</div>
                <div class="stat-label">Total P&L</div>
            </div>
        </div>

        <div class="signals">
            <h2>Latest Signals</h2>
            <div id="signal-list">
                <p>No signals yet...</p>
            </div>
        </div>
    </div>

    <script>
        // WebSocket functionality disabled for Vercel compatibility
        // Using REST API polling instead
        const statusEl = document.getElementById('connection-status');
        const priceEl = document.getElementById('current-price');
        const signalListEl = document.getElementById('signal-list');

        statusEl.textContent = 'API Mode';
        statusEl.className = 'status connected';

        // Poll for updates every 10 seconds
        async function fetchUpdates() {
            try {
                const response = await fetch('/api/signals');
                const data = await response.json();

                updatePrice(data.current_price || 0);
                updateStats(data.stats);

                // Clear and repopulate signals
                signalListEl.innerHTML = '';
                data.signals.slice(-10).reverse().forEach(addSignal);

            } catch (error) {
                console.error('Failed to fetch updates:', error);
                statusEl.textContent = 'API Error';
                statusEl.className = 'status disconnected';
            }
        }

        // Initial load and periodic updates
        fetchUpdates();
        setInterval(fetchUpdates, 10000);

        function updatePrice(price) {
            priceEl.textContent = `$${price.toFixed(2)}`;
        }

        function updateStats(stats) {
            document.getElementById('total-signals').textContent = stats.total_signals;
            document.getElementById('active-trades').textContent = stats.active_trades;
            document.getElementById('win-rate').textContent = `${stats.win_rate.toFixed(1)}%`;
            document.getElementById('total-pnl').textContent = `$${stats.total_pnl.toFixed(2)}`;
        }

        function getInstrumentDetails(instrumentType) {
            const instruments = {
                '3D_5PCT': '3-day, 5% cap, 2.2% cost',
                '3D_10PCT': '3-day, 10% cap, 2.6% cost',
                '7D_5PCT': '7-day, 5% cap, 2.8% cost',
                '7D_10PCT': '7-day, 10% cap, 2.8% cost - Best risk/reward!'
            };
            return instruments[instrumentType] || 'Unknown instrument';
        }

        function addSignal(signal) {
            const signalEl = document.createElement('div');
            signalEl.className = `signal ${signal.signal_type}`;

            const time = new Date(signal.timestamp).toLocaleTimeString();
            const strengthIcon = signal.strength > 0 ? '🔵' : signal.strength < 0 ? '🔴' : '⚪';

            const instrumentDetails = getInstrumentDetails(signal.instrument_type);

            signalEl.innerHTML = `
                <div class="signal-header">
                    ${strengthIcon} ${signal.signal_type} Signal (Strength: ${signal.strength})
                </div>
                <div class="signal-details">
                    Time: ${time} | Price: $${signal.price.toFixed(2)} | Rule: ${signal.rule_triggered}
                    <br>Instrument: <strong>${signal.instrument_type}</strong> (${instrumentDetails})
                    <br>Expected Move: ${signal.expected_move.toFixed(2)}% | Confidence: ${(signal.confidence * 100).toFixed(1)}%
                </div>
            `;

            if (signalListEl.firstChild.textContent === 'No signals yet...') {
                signalListEl.innerHTML = '';
            }

            signalListEl.insertBefore(signalEl, signalListEl.firstChild);

            // Keep only last 10 signals
            while (signalListEl.children.length > 10) {
                signalListEl.removeChild(signalListEl.lastChild);
            }
        }

        // Removed WebSocket ping functionality
    </script>
</body>
</html>
    """)

@app.get("/api/signals")
async def get_signals():
    return {
        "signals": [asdict(s) for s in signal_manager.signal_history[-50:]],
        "stats": signal_manager.stats,
        "current_price": signal_manager.current_price
    }

@app.get("/api/status")
async def get_status():
    return {
        "status": "running",
        "connected_clients": len(signal_manager.active_connections),
        "deribit_connected": deribit_client.is_connected if deribit_client else False,
        "total_signals": signal_manager.stats["total_signals"]
    }

# ==================== STARTUP/SHUTDOWN ====================
# Removed startup/shutdown events for Vercel compatibility
# Vercel serverless functions don't support persistent connections

# For Vercel deployment
handler = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)