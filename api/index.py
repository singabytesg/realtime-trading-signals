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
from datetime import timedelta
import aiosqlite
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebLogger:
    """Custom logger that captures logs and sends them to web interface"""
    def __init__(self, signal_manager_ref=None):
        self.signal_manager_ref = signal_manager_ref

    def info(self, message):
        logger.info(message)
        if self.signal_manager_ref and hasattr(self.signal_manager_ref, 'add_log'):
            self.signal_manager_ref.add_log(message)

    def error(self, message):
        logger.error(message)
        if self.signal_manager_ref and hasattr(self.signal_manager_ref, 'add_log'):
            self.signal_manager_ref.add_log(f"ERROR: {message}")

    def warning(self, message):
        logger.warning(message)
        if self.signal_manager_ref and hasattr(self.signal_manager_ref, 'add_log'):
            self.signal_manager_ref.add_log(f"WARNING: {message}")

# Will be initialized after signal_manager is created
web_logger = None

class PersistentLogManager:
    """Manages logs with both memory cache and database persistence"""

    def __init__(self, db_path: str = "/app/data/logs.db", max_memory_logs: int = 100):
        self.db_path = db_path
        self.max_memory_logs = max_memory_logs
        self.memory_logs: deque = deque(maxlen=max_memory_logs)
        self.batch_logs: List = []
        self.batch_size = 10
        self.last_batch_time = datetime.now()

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    async def initialize_database(self):
        """Create database tables if they don't exist"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    message TEXT NOT NULL,
                    log_type TEXT DEFAULT 'info',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at DESC)
            ''')
            await db.commit()

    async def load_recent_logs(self, limit: int = 100):
        """Load recent logs from database into memory on startup"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT timestamp, message, log_type, created_at
                    FROM logs
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,)) as cursor:
                    rows = await cursor.fetchall()

                    # Add to memory in reverse order (oldest first)
                    for row in reversed(rows):
                        log_entry = {
                            "timestamp": row[0],
                            "message": row[1],
                            "log_type": row[2] or 'info'
                        }
                        self.memory_logs.append(log_entry)

            if rows:
                logger.info(f"Loaded {len(rows)} logs from database")
        except Exception as e:
            logger.error(f"Error loading logs from database: {e}")

    async def add_log(self, message: str, log_type: str = 'info'):
        """Add log to both memory and batch for database"""
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "log_type": log_type
        }

        # Add to memory immediately
        self.memory_logs.append(log_entry)

        # Add to batch for database persistence
        self.batch_logs.append(log_entry)

        # Check if we should flush to database
        await self._maybe_flush_batch()

        return log_entry

    async def _maybe_flush_batch(self):
        """Flush batch to database if batch is full or enough time has passed"""
        now = datetime.now()
        time_since_last = (now - self.last_batch_time).total_seconds()

        if len(self.batch_logs) >= self.batch_size or time_since_last >= 30:
            await self._flush_batch()

    async def _flush_batch(self):
        """Write batch logs to database"""
        if not self.batch_logs:
            return

        try:
            async with aiosqlite.connect(self.db_path) as db:
                batch_data = [
                    (log['timestamp'], log['message'], log['log_type'])
                    for log in self.batch_logs
                ]

                await db.executemany('''
                    INSERT INTO logs (timestamp, message, log_type)
                    VALUES (?, ?, ?)
                ''', batch_data)
                await db.commit()

                logger.debug(f"Saved {len(batch_data)} logs to database")

            self.batch_logs.clear()
            self.last_batch_time = datetime.now()

            # Cleanup old logs periodically
            await self._cleanup_old_logs()

        except Exception as e:
            logger.error(f"Error saving logs to database: {e}")

    async def _cleanup_old_logs(self):
        """Remove old logs to prevent database bloat"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Keep only last 1000 logs
                await db.execute('''
                    DELETE FROM logs
                    WHERE id NOT IN (
                        SELECT id FROM logs
                        ORDER BY created_at DESC
                        LIMIT 1000
                    )
                ''')
                await db.commit()
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")

    def get_memory_logs(self):
        """Get logs from memory cache"""
        return list(self.memory_logs)

app = FastAPI(title="Real-time Trading Signals", version="1.0.0")

# ==================== CORE MODELS ====================

@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

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

    def process_candle_close(self, close_price: float, timestamp: datetime) -> Optional[TradingSignal]:
        self.price_history.append(close_price)

        if web_logger:
            web_logger.info(f"   📝 Added price ${close_price:.2f} to history. Total candles: {len(self.price_history)}")

        if len(self.price_history) < 20:
            if web_logger:
                web_logger.info(f"   ⏳ Not enough candles for analysis. Need 20, have {len(self.price_history)}. Skipping...")
                web_logger.info("=" * 80)
            return None

        # Calculate indicators
        if web_logger:
            web_logger.info(f"   🧮 Calculating technical indicators...")

        sma_short = self.indicators.sma(self.price_history, self.winning_strategy["constants"]["sma_short_period"])
        sma_long = self.indicators.sma(self.price_history, self.winning_strategy["constants"]["sma_long_period"])
        rsi = self.indicators.rsi(self.price_history)
        macd_data = self.indicators.macd(self.price_history)
        volatility = self._calculate_volatility()

        current_price = close_price

        # Log all calculated indicators
        if web_logger:
            web_logger.info(f"   📊 INDICATORS CALCULATED:")
            web_logger.info(f"      • Current Price: ${current_price:.2f}")
            web_logger.info(f"      • SMA Short (15): ${sma_short:.2f}")
            web_logger.info(f"      • SMA Long (20): ${sma_long:.2f}")
            web_logger.info(f"      • RSI: {rsi:.1f}")
            web_logger.info(f"      • MACD Line: {macd_data['macd']:.4f}")
            web_logger.info(f"      • MACD Signal: {macd_data['signal']:.4f}")
            web_logger.info(f"      • MACD Histogram: {macd_data['histogram']:.4f}")
            web_logger.info(f"      • Volatility: {volatility:.2f}%")

        # Check each rule
        if web_logger:
            web_logger.info(f"   🔍 Evaluating {len(self.winning_strategy['rules'])} DSL rules...")

        for i, rule in enumerate(self.winning_strategy["rules"], 1):
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

            if web_logger:
                web_logger.info(f"   📋 Rule {i}: '{rule['name']}'")

            # Log each condition check
            rule_passed = True
            for j, condition in enumerate(rule["conditions"], 1):
                condition_result = self._evaluate_condition(condition, indicators_dict)
                status = "✅ PASS" if condition_result else "❌ FAIL"
                if web_logger:
                    web_logger.info(f"      Condition {j}: {condition} → {status}")
                if not condition_result:
                    rule_passed = False

            if rule_passed:
                # Calculate expected move percentage
                expected_move_pct = abs(macd_data["histogram"]) * 2 + (volatility / 10)

                # Select optimal instrument based on signal strength, volatility, and expected move
                optimal_instrument = self.option_instruments.select_optimal_instrument(
                    signal_strength=rule["signal"]["strength"],
                    volatility=volatility,
                    expected_move=expected_move_pct,
                    high_vol_threshold=self.winning_strategy["constants"]["high_vol_threshold"]
                )

                if web_logger:
                    web_logger.info(f"   🎯 SIGNAL GENERATED!")
                    web_logger.info(f"      • Rule: {rule['name']}")
                    web_logger.info(f"      • Signal: {rule['signal']['type']} (strength: {rule['signal']['strength']})")
                    web_logger.info(f"      • Expected Move: {expected_move_pct:.2f}%")
                    web_logger.info(f"      • Optimal Instrument: {optimal_instrument}")
                    web_logger.info("=" * 80)

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
            else:
                if web_logger:
                    web_logger.info(f"      → Rule failed. Moving to next rule.")

        if web_logger:
            web_logger.info(f"   ❌ No signals generated. All {len(self.winning_strategy['rules'])} rules failed.")
            web_logger.info("=" * 80)
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

            # Subscribe to ETH perpetual 30-minute candles
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "public/subscribe",
                "params": {
                    "channels": ["chart.trades.ETH-PERPETUAL.30"]
                }
            }

            await self.websocket.send(json.dumps(subscribe_msg))
            logger.info("Subscribed to ETH-PERPETUAL 30-min candles")

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
                    candle_data = data["params"]["data"]

                    # Handle candle data: [timestamp, open, high, low, close, volume]
                    if isinstance(candle_data, list) and len(candle_data) >= 5:
                        timestamp_ms, open_price, high, low, close_price, volume = candle_data[:6]
                        candle_time = datetime.fromtimestamp(timestamp_ms / 1000)

                        # Detailed candle logging
                        if web_logger:
                            web_logger.info("=" * 80)
                            web_logger.info(f"📊 NEW 30-MIN CANDLE RECEIVED")
                            web_logger.info(f"   📅 Time: {candle_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                            web_logger.info(f"   💰 OHLC: Open=${open_price:.2f} | High=${high:.2f} | Low=${low:.2f} | Close=${close_price:.2f}")
                            web_logger.info(f"   📈 Volume: {volume:,.0f}")
                            web_logger.info(f"   🔄 Processing DSL strategy...")

                        await self.signal_callback(close_price, candle_time)

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
        self.persistent_log_manager = PersistentLogManager()
        self.stats = {
            "total_signals": 0,
            "active_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0
        }

    async def process_candle_close(self, close_price: float, timestamp: datetime):
        self.current_price = close_price

        signal = self.dsl_executor.process_candle_close(close_price, timestamp)

        if signal and signal.signal_type != "NEUTRAL":
            self.signal_history.append(signal)
            self.stats["total_signals"] += 1

            logger.info(f"🚨 NEW SIGNAL: {signal.signal_type} {signal.strength} @ ${close_price:.2f}")

            # Broadcast to all connected WebSocket clients
            signal_data = {
                "type": "signal",
                "data": asdict(signal),
                "stats": self.stats,
                "current_price": close_price
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
                "stats": self.stats,
                "logs": self.persistent_log_manager.get_memory_logs()
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

    def add_log(self, message: str, log_type: str = 'info'):
        """Add a log message and broadcast to connected clients"""
        async def _add_log_async():
            log_entry = await self.persistent_log_manager.add_log(message, log_type)
            # Broadcast log to connected clients
            await self._broadcast({
                "type": "log",
                "data": log_entry
            })

        # Schedule the async operation
        asyncio.create_task(_add_log_async())

# ==================== GLOBAL INSTANCES ====================

signal_manager = SignalManager()
deribit_client = None

# Initialize web logger with signal manager reference
web_logger = WebLogger(signal_manager)

# ==================== WEBSOCKET ENDPOINTS ====================

@app.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    await signal_manager.connect_websocket(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        signal_manager.disconnect_websocket(websocket)

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
        .log-controls { margin-bottom: 15px; }
        .log-controls button { padding: 8px 16px; margin-right: 10px; background: #2196F3; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .log-controls button:hover { background: #1976D2; }
        #log-container { max-height: 400px; overflow-y: auto; background: #1e1e1e; border-radius: 4px; padding: 10px; }
        .log-entry { margin: 2px 0; padding: 4px 8px; border-radius: 3px; font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.4; }
        .log-entry.info { color: #ffffff; }
        .log-entry.candle { color: #4CAF50; background: rgba(76, 175, 80, 0.1); }
        .log-entry.indicator { color: #2196F3; background: rgba(33, 150, 243, 0.1); }
        .log-entry.rule { color: #FF9800; background: rgba(255, 152, 0, 0.1); }
        .log-entry.signal { color: #f44336; background: rgba(244, 67, 54, 0.1); font-weight: bold; }
        .log-entry.error { color: #f44336; background: rgba(244, 67, 54, 0.2); }
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

        <div class="signals">
            <h2>🔍 Real-time Processing Logs</h2>
            <div class="log-controls">
                <button id="clear-logs">Clear Logs</button>
                <button id="toggle-auto-scroll">Auto-scroll: ON</button>
            </div>
            <div id="log-container">
                <div id="log-list">
                    <p class="log-entry info">System starting... waiting for data...</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Use wss:// for HTTPS deployments (like DigitalOcean), ws:// for local development
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/signals`);
        const statusEl = document.getElementById('connection-status');
        const priceEl = document.getElementById('current-price');
        const signalListEl = document.getElementById('signal-list');
        const logListEl = document.getElementById('log-list');
        const logContainerEl = document.getElementById('log-container');
        let autoScroll = true;

        ws.onopen = function() {
            statusEl.textContent = 'Connected';
            statusEl.className = 'status connected';
        };

        ws.onclose = function() {
            statusEl.textContent = 'Disconnected';
            statusEl.className = 'status disconnected';
        };

        ws.onmessage = function(event) {
            const message = JSON.parse(event.data);

            if (message.type === 'signal') {
                addSignal(message.data);
                updateStats(message.stats);
                updatePrice(message.current_price);
            } else if (message.type === 'init') {
                updatePrice(message.data.current_price);
                updateStats(message.data.stats);
                message.data.signal_history.forEach(addSignal);
                // Load initial logs if any
                if (message.data.logs) {
                    message.data.logs.forEach(addLog);
                }
            } else if (message.type === 'log') {
                addLog(message.data);
            }
        };

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

        function addLog(logData) {
            const logEl = document.createElement('div');

            // Determine log type for styling
            let logClass = 'info';
            const msg = logData.message.toLowerCase();

            if (msg.includes('new 30-min candle') || msg.includes('ohlc:')) {
                logClass = 'candle';
            } else if (msg.includes('indicators calculated') || msg.includes('sma') || msg.includes('rsi') || msg.includes('macd')) {
                logClass = 'indicator';
            } else if (msg.includes('rule') || msg.includes('condition') || msg.includes('evaluating')) {
                logClass = 'rule';
            } else if (msg.includes('signal generated') || msg.includes('no signals generated')) {
                logClass = 'signal';
            } else if (msg.includes('error') || msg.includes('failed')) {
                logClass = 'error';
            }

            logEl.className = `log-entry ${logClass}`;
            logEl.innerHTML = `[${logData.timestamp}] ${logData.message}`;

            logListEl.appendChild(logEl);

            // Keep only last 200 log entries
            while (logListEl.children.length > 200) {
                logListEl.removeChild(logListEl.firstChild);
            }

            // Auto-scroll to bottom if enabled
            if (autoScroll) {
                logContainerEl.scrollTop = logContainerEl.scrollHeight;
            }
        }

        // Log controls
        document.getElementById('clear-logs').addEventListener('click', function() {
            logListEl.innerHTML = '<p class="log-entry info">Logs cleared</p>';
        });

        document.getElementById('toggle-auto-scroll').addEventListener('click', function() {
            autoScroll = !autoScroll;
            this.textContent = `Auto-scroll: ${autoScroll ? 'ON' : 'OFF'}`;
            this.style.background = autoScroll ? '#4CAF50' : '#f44336';
        });

        // Keep WebSocket connection alive
        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send('ping');
            }
        }, 30000);
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

@app.on_event("startup")
async def startup_event():
    global deribit_client

    logger.info("🚀 Starting Real-time Trading Signal System")

    # Initialize persistent logging system
    await signal_manager.persistent_log_manager.initialize_database()
    await signal_manager.persistent_log_manager.load_recent_logs()

    # Add system startup log
    signal_manager.add_log("🚀 System restarted - Real-time Trading Signal System started", "info")
    signal_manager.add_log("📚 Loaded previous logs from database", "info")

    deribit_client = DeribitWebSocketClient(signal_manager.process_candle_close)

    # Start Deribit connection in background
    asyncio.create_task(start_deribit_connection())

async def start_deribit_connection():
    global deribit_client

    while True:
        try:
            if not deribit_client.is_connected:
                await deribit_client.connect()
                if deribit_client.is_connected:
                    await deribit_client.listen()
        except Exception as e:
            logger.error(f"Deribit connection error: {e}")

        # Reconnect after 5 seconds if disconnected
        await asyncio.sleep(5)

@app.on_event("shutdown")
async def shutdown_event():
    global deribit_client

    logger.info("🛑 Shutting down Real-time Trading Signal System")

    # Flush any remaining logs to database
    signal_manager.add_log("🛑 System shutting down - saving final logs", "info")
    await signal_manager.persistent_log_manager._flush_batch()

    if deribit_client:
        await deribit_client.disconnect()

# For Vercel deployment
handler = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)