# AI Trading Assistant - Python

A trading simulation that uses Cerebras AI models with optional Membit tools for news/sentiment analysis. Each of the 6 configurations (3 models × 2 modes) starts with **$10,000** and trades to maximize P&L.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) - Python package manager

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# or with Homebrew
brew install uv

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Setup

1. Install dependencies:
   ```bash
   cd python
   uv sync
   ```

2. Create environment file:
   ```bash
   cp .env.example .env
   ```

3. Add your API keys to `.env`:
   ```
   CEREBRAS_API_KEY=your_cerebras_key
   TWELVE_DATA_API_KEY=your_twelvedata_key
   MEMBIT_API_KEY=your_membit_key
   ```

## API Keys

| Service | Required | Free Tier | Get Key |
|---------|----------|-----------|---------|
| Cerebras | Yes | Yes | [cloud.cerebras.ai](https://cloud.cerebras.ai/) |
| Twelve Data | Yes | 800 calls/day | [twelvedata.com](https://twelvedata.com/) |
| Membit | For tools mode | Yes | [membit.ai](https://membit.ai/) |
| Band Protocol | No key needed | Free | - |

## Usage

### Interactive Mode

Run the trading assistant with interactive model and mode selection:

```bash
uv run python -m src.examples.main
```

You'll be prompted to:
1. Select a model (llama3.1-8b, llama-3.3-70b, qwen-3-32b)
2. Select a symbol (BTC, ETH, SOL, AVAX, LINK, ATOM)
3. Enable/disable Membit tools

### Scheduler (Continuous Trading Simulation)

Run all 6 configurations continuously with hourly updates:

```bash
uv run python -m src.scheduler        # Default: BTC
uv run python -m src.scheduler ETH    # Or specify symbol
```

This starts a **continuous trading simulation** that:
- Runs every hour automatically (no cron needed)
- Each configuration starts with **$10,000**
- Tracks asset holdings, capital, and P&L
- Shows action summary table after each run
- Shows a leaderboard after each run
- Press `Ctrl+C` to stop

Each model runs in both modes:
- **Basic**: Price + Technical Indicators only (AI cannot use Membit tools)
- **Membit**: AI must call Membit tools for news/sentiment before trading

### Compare Results & Leaderboard

View the current leaderboard and historical comparison report:

```bash
uv run python -m src.compare_results
```

This shows:
- **Leaderboard**: Current portfolio values ranked by performance
- **Historical Analysis**: P&L comparison between Basic and Membit modes

## Running in Background

The scheduler runs continuously with a built-in hourly loop. To run it in the background:

### Using screen (recommended)

```bash
# Start a new screen session
screen -S trading

# Run the scheduler
cd /path/to/ai-api-client/python
uv run python -m src.scheduler

# Detach with Ctrl+A, then D
# Reattach later with: screen -r trading
```

### Using nohup

```bash
cd /path/to/ai-api-client/python
nohup uv run python -m src.scheduler > trading.log 2>&1 &
```

## Available Models

| Model | Description |
|-------|-------------|
| `llama3.1-8b` | Fast, efficient |
| `llama-3.3-70b` | Latest Llama, recommended |
| `qwen-3-32b` | Qwen 32B |

## How It Works

### Exchange Tools (Available in Both Modes)
- `get_portfolio` - Get current portfolio status (cash, position, P&L)
- `buy` - Buy asset with specified USD amount (flexible sizing)
- `sell` - Sell specified asset amount (flexible sizing)
- `hold` - Keep position unchanged

### Membit Tools (Only in Membit Mode)
- `search_posts` - Search for recent social media posts about a topic
- `search_clusters` - Search for trending topic clusters
- `get_cluster_info` - Get detailed info about a specific cluster

### Basic Mode
AI receives price data and technical indicators, then makes a decision using only exchange tools.

### Membit Tools Mode
AI **must** call Membit tools to gather sentiment data before deciding:

```
AI: Let me check market sentiment first.
    TOOL_CALL: {"name": "search_posts", "arguments": {"query": "Bitcoin market sentiment"}}

[Tool executes and returns results]

AI: Based on RSI at 45 and bullish sentiment from recent posts...
    TOOL_CALL: {"name": "buy", "arguments": {"usd_amount": 5000}}
```

**Important**: In basic mode, the AI is instructed to only use exchange tools. Membit tools are only available when explicitly enabled.

## Data Sources

- **Price**: Band Protocol (free, no API key)
- **Technical Indicators**: Twelve Data (SMA, MACD, Bollinger Bands, RSI)
- **News/Sentiment**: Membit (social media posts and trending clusters)

## Project Structure

```
python/
├── src/
│   ├── agent.py              # AI agent with MCP-style tool support
│   ├── cerebras_client.py    # Cerebras API client
│   ├── membit_client.py      # Membit SDK wrapper
│   ├── price_client.py       # Band Protocol price fetcher
│   ├── indicators_client.py  # Twelve Data technical indicators
│   ├── state_manager.py      # Position state persistence
│   ├── scheduler.py          # Scheduled execution for all configs
│   ├── compare_results.py    # Results comparison report
│   ├── types.py              # Type definitions
│   └── examples/
│       └── main.py           # Interactive entry point
├── .states/                   # Position states (gitignored)
├── .results/                  # Scheduler results (gitignored)
├── .env                       # API keys (gitignored)
├── .env.example               # Example env file
└── pyproject.toml
```

## Action Summary Table

After each scheduler run, an action summary table shows what each model did:

| Action | Details Format |
|--------|----------------|
| BUY | `$5,000 @ $98,500 -> 0.050761 BTC` (USD spent @ price -> amount bought) |
| SELL | `Sold 0.04 BTC -> $3,940, remaining: 0.01 ($985)` |
| HOLD | `Holding 0.05 BTC ($4,925)` or `Holding cash: $10,000` |
| NONE | No trade executed |
| ERROR | Error message |

## Position States

Each model+mode combination maintains its own position state:

- `.states/llama3_1_8b_btc_basic.json`
- `.states/llama3_1_8b_btc_membit.json`
- `.states/llama_3_3_70b_btc_basic.json`
- etc.

## Example Output

### Scheduler Run
```
============================================================
  Trading Simulation Run: 2025-01-15T14:00:00
  Symbol: BTC | Starting Capital: $10,000
============================================================

BTC Price: $98,500.00

[llama3.1-8b] (basic) - Portfolio: $10,000.00
    [Tool] get_portfolio({"symbol": "BTC"})
    [Tool] buy({"usd_amount": 2000, "symbol": "BTC"})
  -> BUY | 2 tools
[llama3.1-8b] (membit) - Portfolio: $10,245.00
    [Tool] get_portfolio({"symbol": "BTC"})
    [Membit] post_search('Bitcoin') raw response: {...}
    [Tool] search_posts({"query": "Bitcoin crypto market"})
    [Tool] buy({"usd_amount": 5000, "symbol": "BTC"})
  -> BUY | 3 tools
...

====================================================================================================
  RUN SUMMARY - Actions Taken
====================================================================================================
Model                Mode     Action   Details                                                    Tools
----------------------------------------------------------------------------------------------------
llama3.1-8b          basic    BUY      $2,000 @ $98,500 -> 0.020305 BTC                          2
llama3.1-8b          membit   BUY      $5,000 @ $98,500 -> 0.050761 BTC                          3
llama-3.3-70b        basic    HOLD     Holding cash: $10,000                                      2
llama-3.3-70b        membit   SELL     Sold 0.040000 BTC -> $3,940, remaining: 0.010 ($985)      4
qwen-3-32b           basic    BUY      $3,000 @ $98,500 -> 0.030457 BTC                          2
qwen-3-32b           membit   HOLD     Holding 0.050000 BTC ($4,925)                             3
====================================================================================================

============================================================
  LEADERBOARD (BTC)
============================================================
Config                         Value        P&L          Return
----------------------------------------------------------------
1. llama-3.3-70b (membit)     $11,250.00   $+1,250.00   +12.50%
2. llama-3.3-70b (basic)      $10,890.00     $+890.00    +8.90%
3. qwen-3-32b (membit)        $10,450.00     $+450.00    +4.50%
...

  WINNER: llama-3.3-70b (membit) with $+1,250.00 (+12.50%)

Next run at: 2025-01-15T15:00:00
Sleeping for 60 minutes...
```

### Comparison Report
```
======================================================================
  LEADERBOARD - Current Portfolio Values
======================================================================

  BTC Price: $98,500.00

  Rank  Config                          Value          P&L            Return
  ------------------------------------------------------------------------
  1     llama-3.3-70b (membit)        $11,250.00    $+1,250.00      +12.50%
  2     llama-3.3-70b (basic)         $10,890.00      $+890.00       +8.90%
  3     qwen-3-32b (membit)           $10,450.00      $+450.00       +4.50%*
  ...

  * = has open BTC position

======================================================================
  MEMBIT vs BASIC COMPARISON REPORT
======================================================================

  MODEL: llama-3.3-70b
==================================================
  Basic (Price + Indicators only):
    Runs: 168 | Errors: 0
    Signals: BUY=42 SELL=35 HOLD=91
    Trades: 35 closed | Win Rate: 48.6%
    Total P&L: $+890.00
  Membit (+ News/Sentiment tools):
    Runs: 168 | Errors: 2
    Signals: BUY=38 SELL=32 HOLD=98
    Trades: 32 closed | Win Rate: 56.3%
    Total P&L: $+1,250.00
    Tool Calls: 312

    >> MEMBIT wins by $360.00

----------------------------------------------------------------------
  BEST CONFIGURATION: llama-3.3-70b (membit) (P&L: $+1,250.00)
----------------------------------------------------------------------
```

## Disclaimer

This is for educational and research purposes only. Not financial advice. Always do your own research before making investment decisions.
