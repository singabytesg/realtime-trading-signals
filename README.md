# Real-time Trading Signal System

A standalone FastAPI application that generates live trading signals using DSL strategies with real-time Deribit market data.

## Features

- 🔴 **Real-time Signal Generation**: Uses your winning 77.8% win rate DSL strategy
- 📊 **Live Market Data**: WebSocket connection to Deribit for ETH perpetual futures
- 🎯 **Signal Rules**: Implements the exact logic from your winning strategy:
  - Strong Bear Breakdown (PUT -7)
  - Moderate Bear Signal (PUT -3)
  - Oversold Bounce (CALL 3)
- 📱 **Web Interface**: Simple dashboard showing signals, stats, and current price
- ⚡ **WebSocket API**: Real-time signal streaming to connected clients

## Quick Start

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

3. Open your browser to: `http://localhost:8000`

### Deploy to Vercel

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Deploy:
```bash
vercel --prod
```

The app will be available at your Vercel URL with full WebSocket support.

## API Endpoints

- `GET /` - Web dashboard interface
- `WS /ws/signals` - WebSocket for real-time signals
- `GET /api/signals` - REST API for signal history
- `GET /api/status` - System status

## Architecture

### Core Components

1. **SimpleDSLExecutor**: Processes live price updates using your DSL strategy
2. **DeribitWebSocketClient**: Connects to Deribit for real-time ETH prices
3. **SignalManager**: Coordinates signal generation and client communication
4. **Web Interface**: Real-time dashboard with WebSocket updates

### Signal Logic

The system implements your winning strategy rules with **dynamic instrument selection**:

### Technical Indicators
- **RSI**: 14-period momentum indicator
- **MACD**: 12/21/7 trend following
- **SMA**: 15/20 period moving averages
- **Volatility**: ATR-based volatility filtering

### Dynamic Instrument Selection

The system automatically selects the optimal option instrument based on:

1. **Signal Strength**:
   - Strong signals (±7): Use higher profit cap instruments (10% cap)
   - Moderate signals (±3): Use conservative instruments (5% cap)

2. **Volatility Conditions**:
   - High volatility (>3.5%): Shorter duration (3-day options)
   - Low volatility (≤3.5%): Longer duration (7-day options)

3. **Expected Move**:
   - Large expected move (>7%): 10% profit cap
   - Moderate expected move (5-7%): 5% profit cap
   - Small expected move (<5%): Conservative approach

### Instrument Options
- **3D_5PCT**: 3-day, 5% cap, 2.2% cost (Conservative short-term)
- **3D_10PCT**: 3-day, 10% cap, 2.6% cost (Aggressive short-term)
- **7D_5PCT**: 7-day, 5% cap, 2.8% cost (Conservative longer-term)
- **7D_10PCT**: 7-day, 10% cap, 2.8% cost (Best risk/reward for strong signals!)

### Timeframe

Currently processes live price updates (100ms from Deribit). Can be adjusted to any timeframe by modifying the subscription channel.

## Configuration

The strategy parameters are embedded in the code using your winning configuration:

```python
"constants": {
    "rsi_oversold": 30,
    "macd_fast": 12,
    "macd_slow": 21,
    "macd_signal": 7,
    "sma_short_period": 15,
    "sma_long_period": 20,
    "atr_period": 10,
    "high_vol_threshold": 3.5
}
```

## WebSocket Message Format

```json
{
  "type": "signal",
  "data": {
    "timestamp": "2024-01-01T12:00:00",
    "signal_type": "PUT",
    "strength": -7,
    "price": 2500.50,
    "rule_triggered": "strong_bear_breakdown",
    "instrument_type": "7D_5PCT",
    "confidence": 0.8,
    "expected_move": 3.2
  },
  "stats": {
    "total_signals": 15,
    "active_trades": 2,
    "win_rate": 77.8,
    "total_pnl": 150.25
  },
  "current_price": 2500.50
}
```

## Production Notes

- The system is designed to be lightweight and run on serverless platforms
- WebSocket connections are managed efficiently with automatic cleanup
- Error handling includes automatic Deribit reconnection
- All time-sensitive calculations use deques for optimal performance

## Extending

To modify the strategy:

1. Update the `winning_strategy` config in `SimpleDSLExecutor`
2. Add new indicators to the `TechnicalIndicators` class
3. Extend the condition evaluator for more complex rules

The system is built to be easily extended while maintaining the core simplicity for Vercel deployment.