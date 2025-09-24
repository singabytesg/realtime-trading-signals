# Running DPA (Data Provisioning Agent) - Quick Start Guide

## Prerequisites

### 1. Install Python Package Manager
You need either `poetry`, `uv`, or `pip` to install dependencies.

**Option A: Install uv (Recommended)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Option B: Install Poetry**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Install Dependencies

**Using uv:**
```bash
make install
# OR
uv pip install -r requirements.txt
```

**Using Poetry:**
```bash
poetry install
```

**Using pip:**
```bash
pip3 install -r requirements.txt
```

### 3. Set Environment Variables

Create a `.env` file with required API keys:
```bash
cp .env-sample .env
```

Edit `.env` with your keys:
```env
OPENROUTER_API_KEY=your_openrouter_key
TOGETHER_API_KEY=your_together_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## Running DPA

### Option 1: Direct Agent Execution
```bash
python3 -m src.core.agents.exp.dpa
```

**Expected Output:**
- Fetches 30 days of ETH 1-day OHLCV data
- Displays formatted market data
- Stores data in team_session_state

### Option 2: Through Team Interface
```bash
python3 agno_exp.py
```
Then access the playground at `http://localhost:7777`

### Option 3: API Endpoint
```bash
make run-pokpok-api-dev
```
Then call:
```bash
curl -X POST http://localhost:8000/agent-brain/run \
  -H "Content-Type: application/json" \
  -d '{"message": "Get OHLCV data for ETH", "agent_id": "historical_market_agent"}'
```

### Option 4: Interactive Test
```bash
python3 test_dpa_output.py
```
This shows mock DPA output format without needing full setup.

## Sample DPA Usage Patterns

### 1. Basic Data Fetch
```python
from src.core.agents.exp.dpa import dpa_agent

response = dpa_agent.run("Get OHLCV for ETH 1d 30-day lookback.")
print(response.output)
```

### 2. Custom Parameters
```python
response = dpa_agent.run(
    "Fetch Bitcoin 4-hour data for last 7 days",
    stream=True
)
```

### 3. Team Integration
```python
# Data automatically shared via team_session_state["ohlcv_data"]
# Other agents can access immediately
```

## Data Output Structure

```json
{
  "ohlcv": [
    {
      "Date": "2024-01-01T00:00:00Z",
      "Open": 2200.50,
      "High": 2250.75,
      "Low": 2180.25,
      "Close": 2240.00,
      "Volume": 150000.0
    }
  ],
  "asset": "ETH",
  "timeframe": "DAY_1",
  "lookback_days": 30
}
```

## Data Storage Locations

1. **In-Memory**: `agent.team_session_state["ohlcv_data"]`
2. **SQLite DB**: `tmp/agent.db`
3. **Context Objects**: Passed through EVAInputContext, MRCAInputContext, etc.

## Consuming Agents

- **MRCA**: Technical analysis (RSI, MACD, Bollinger Bands)
- **EVA**: Strategy backtesting and evaluation
- **LAA**: Learning and adapting strategies
- **MST**: Market strategy development
- **MAT**: Market analysis and regime detection

## Troubleshooting

### Missing Dependencies
```bash
pip3 install agno pandas fastapi uvicorn
```

### API Key Issues
Ensure all required environment variables are set in `.env`

### Module Import Errors
Run from project root directory:
```bash
cd /Users/ivanhmac/github/pokpok/Archive/pokpok_agents
PYTHONPATH=. python3 -m src.core.agents.exp.dpa
```

### Database Permissions
Ensure `tmp/` directory exists and is writable:
```bash
mkdir -p tmp
chmod 755 tmp
```

## Next Steps

1. **Run DPA**: Start with `python3 test_dpa_output.py` to see output format
2. **Set Up Environment**: Install dependencies and configure API keys
3. **Test Integration**: Run with other agents through team interface
4. **Custom Data Requests**: Modify parameters for different assets/timeframes