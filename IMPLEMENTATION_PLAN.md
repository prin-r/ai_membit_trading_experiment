# Monorepo Conversion Implementation Plan

This document outlines the plan to convert the current `ai-api-client` repository into a monorepo containing both Node.js and Python implementations.

## Overview

**Goal**: Create a monorepo with two language implementations:

1. **Node.js** - Move existing code to `node/` folder
2. **Python** - New implementation using Cerebras Cloud SDK with Membit integration

## Final Directory Structure

```
ai-api-client/
├── README.md                 # Root README explaining the monorepo
├── CLAUDE.md                 # Updated project instructions
├── .gitignore                # Combined gitignore for both projects
│
├── node/                     # Node.js implementation (existing code)
│   ├── src/
│   │   ├── index.ts
│   │   ├── types.ts
│   │   ├── providers.ts
│   │   ├── client.ts
│   │   └── example.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── .env.example
│   └── README.md
│
└── python/                   # Python implementation (new)
    ├── src/
    │   ├── __init__.py
    │   ├── types.py
    │   ├── cerebras_client.py
    │   ├── membit_client.py
    │   ├── price_client.py             # Band Protocol price data
    │   ├── indicators_client.py        # Twelve Data technical indicators
    │   ├── state_manager.py            # Persistent position state
    │   └── examples/
    │       ├── __init__.py
    │       └── main.py                 # Single entry point with interactive selection
    ├── pyproject.toml
    ├── .env.example
    ├── .states/                        # Position states folder (gitignored)
    │   ├── llama3_1_8b_basic.json
    │   ├── llama3_1_8b_membit.json
    │   └── ...                         # One file per model+membit combination
    └── README.md
```

---

## Phase 1: Restructure for Monorepo

### Step 1.1: Create Node.js folder and move existing code

```bash
# Create node directory
mkdir -p node

# Move all Node.js related files
mv src/ node/
mv package.json node/
mv tsconfig.json node/
mv .env node/.env  # if exists
```

### Step 1.2: Update Node.js package paths

Update `node/package.json` if needed (paths should still work since structure is preserved).

### Step 1.3: Create root-level files

Create a new root `README.md` explaining the monorepo structure.

Update root `.gitignore` to include patterns for both languages:

```gitignore
# Node
node/node_modules/
node/dist/
node/.env

# Python (uv)
python/.venv/
python/__pycache__/
python/*.egg-info/
python/.env
python/uv.lock
python/.states/
*.pyc
```

---

## Phase 2: Python Implementation

### Step 2.1: Initialize Python project

```bash
mkdir -p python/src/examples
cd python
uv init
```

Create `pyproject.toml`:

```toml
[project]
name = "ai-api-client"
version = "0.1.0"
description = "AI API client for Cerebras with optional Membit integration"
requires-python = ">=3.10"
dependencies = [
    "cerebras-cloud-sdk",      # Cerebras Cloud SDK
    "requests>=2.31.0",        # HTTP client for Band Protocol API
    "membit-python>=0.1.0",    # Membit SDK
    "python-dotenv>=1.0.0",    # Environment variable management
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "ruff>=0.1.0",
]
```

### Step 2.2: Create type definitions

Create `python/src/types.py`:

```python
from dataclasses import dataclass
from typing import Literal, Any, Optional

Provider = Literal["cerebras"]

@dataclass
class CallOptions:
    system_prompt: str
    user_message: str
    model: Optional[str] = None
    max_tokens: int = 1024

@dataclass
class AIResponse:
    provider: Provider
    content: str
    raw: Any
```

### Step 2.3: Create Cerebras client

Create `python/src/cerebras_client.py`:

**Note**: Uses the official Cerebras Cloud SDK from https://github.com/Cerebras/cerebras-cloud-sdk-python

```python
import os
from cerebras.cloud.sdk import Cerebras
from .types import CallOptions, AIResponse

def get_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Missing: {key}")
    return value

def call_cerebras(options: CallOptions) -> AIResponse:
    """
    Call Cerebras API using the official Cerebras Cloud SDK.

    Cerebras offers models like:
    - llama3.1-8b (fast, efficient)
    - llama3.1-70b (more capable)
    - llama-3.3-70b (latest, recommended)
    """
    api_key = get_env("CEREBRAS_API_KEY")

    client = Cerebras(api_key=api_key)

    model = options.model or "llama-3.3-70b"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": options.system_prompt},
            {"role": "user", "content": options.user_message},
        ],
        max_tokens=options.max_tokens,
    )

    content = response.choices[0].message.content or ""

    return AIResponse(
        provider="cerebras",
        content=content,
        raw=response.model_dump(),
    )
```

### Step 2.4: Create Membit client wrapper

Create `python/src/membit_client.py`:

**Note**: Based on the official Membit Python SDK from https://github.com/bandprotocol/membit-python

```python
import os
from typing import Optional, List, Dict, Any
from membit import MembitClient

def get_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Missing: {key}")
    return value

class MembitWrapper:
    """Wrapper around Membit SDK for fetching contextual data."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_env("MEMBIT_API_KEY")
        self.client = MembitClient(api_key=self.api_key)

    def search_clusters(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for trending topic clusters.
        Returns list of cluster dicts with 'label' and other fields.
        """
        result = self.client.cluster_search(query, limit=limit)
        # API returns {"clusters": [...]}
        return result.get("clusters", []) if isinstance(result, dict) else []

    def search_posts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for individual posts.
        Returns list of post dicts.
        """
        result = self.client.post_search(query, limit=limit)
        # API returns {"posts": [...]} or similar structure
        if isinstance(result, dict):
            return result.get("posts", result.get("results", []))
        return result if isinstance(result, list) else []

    def get_cluster_info(self, cluster_label: str, limit: int = 5) -> Dict[str, Any]:
        """
        Get detailed info about a specific cluster by its label.
        """
        return self.client.cluster_info(cluster_label, limit=limit)

    def format_clusters_for_prompt(self, clusters: List[Dict[str, Any]]) -> str:
        """Format cluster search results as context for AI prompt."""
        if not clusters:
            return "No trending clusters found."

        lines = ["TRENDING TOPIC CLUSTERS:"]
        for i, cluster in enumerate(clusters[:5], 1):
            label = cluster.get("label", str(cluster))
            lines.append(f"{i}. {label}")

        return "\n".join(lines)

    def format_posts_for_prompt(self, posts: List[Dict[str, Any]]) -> str:
        """Format post search results as context for AI prompt."""
        if not posts:
            return "No recent posts found."

        lines = ["RECENT SOCIAL POSTS:"]
        for i, post in enumerate(posts[:10], 1):
            # Handle various possible field names
            content = (
                post.get("content") or
                post.get("text") or
                post.get("body") or
                str(post)
            )
            # Truncate long content
            if len(content) > 200:
                content = content[:197] + "..."
            lines.append(f"{i}. {content}")

        return "\n".join(lines)
```

---

## Phase 3: Data Clients & Exchange MCP

This phase creates the data clients and an Exchange MCP server that allows the AI agent to interact with a simulated exchange through MCP tools.

### Step 3.1: Price API Client (Band Protocol)

Create a price client using Band Protocol's price feed API (free, no API key required).

Create `python/src/price_client.py`:

```python
"""
Price data client using Band Protocol price feeds.
https://laozi3.bandchain.org/api/feeds/v1beta1/all_prices
Free API, no authentication required.
"""
import requests
from typing import Any, Optional, List
from dataclasses import dataclass

BAND_PROTOCOL_API_URL = "https://laozi3.bandchain.org/api/feeds/v1beta1/all_prices"

@dataclass
class PriceData:
    symbol: str
    price: float
    timestamp: Optional[int] = None
    raw: Any = None

def fetch_bitcoin_price() -> PriceData:
    """
    Fetch current Bitcoin price from Band Protocol API.
    No API key required.

    Price is returned in 9 decimal places (e.g., 87443860813094 = $87,443.86)
    """
    response = requests.get(BAND_PROTOCOL_API_URL)
    response.raise_for_status()
    data = response.json()

    # Find BTC-USD in the prices list
    btc_data = None
    for price_item in data.get("prices", []):
        if price_item.get("signal_id") == "CS:BTC-USD":
            btc_data = price_item
            break

    if not btc_data or btc_data.get("status") != "PRICE_STATUS_AVAILABLE":
        raise ValueError("Bitcoin price not available from Band Protocol")

    # Price has 9 decimal places
    raw_price = int(btc_data.get("price", 0))
    price = raw_price / 1_000_000_000

    return PriceData(
        symbol="BTC",
        price=price,
        timestamp=int(btc_data.get("timestamp", 0)) if btc_data.get("timestamp") else None,
        raw=btc_data,
    )

def fetch_all_prices() -> List[PriceData]:
    """
    Fetch all available prices from Band Protocol API.
    Returns a list of PriceData for all available assets.
    """
    response = requests.get(BAND_PROTOCOL_API_URL)
    response.raise_for_status()
    data = response.json()

    prices = []
    for price_item in data.get("prices", []):
        if price_item.get("status") != "PRICE_STATUS_AVAILABLE":
            continue

        signal_id = price_item.get("signal_id", "")
        # Parse symbol from signal_id (e.g., "CS:BTC-USD" -> "BTC")
        symbol = signal_id.replace("CS:", "").replace("-USD", "")

        raw_price = int(price_item.get("price", 0))
        price = raw_price / 1_000_000_000

        prices.append(PriceData(
            symbol=symbol,
            price=price,
            timestamp=int(price_item.get("timestamp", 0)) if price_item.get("timestamp") else None,
            raw=price_item,
        ))

    return prices

def format_price_context(price_data: PriceData) -> str:
    """Format price data as context for AI prompt."""
    return f"Current {price_data.symbol} Price: ${price_data.price:,.2f}"

def format_multi_price_context(prices: List[PriceData], symbols: List[str] = None) -> str:
    """Format multiple prices as context for AI prompt."""
    if symbols:
        prices = [p for p in prices if p.symbol in symbols]

    lines = [f"{p.symbol}: ${p.price:,.2f}" for p in prices]
    return "\n".join(lines)
```

---

### Step 3.2: Technical Indicators Client (Twelve Data)

Create a client to fetch technical indicators from Twelve Data API.

Create `python/src/indicators_client.py`:

```python
"""
Technical indicators client using Twelve Data API.
https://twelvedata.com/docs

Indicators:
1. SMA (200) - Trend: "Big Picture" - Buy when price is above
2. MACD (12, 26, 9) - Momentum: Trend strength/weakness
3. Bollinger Bands (20, 2) - Volatility: Price range from average
4. RSI (14) - Sentiment: Overbought (>70) / Oversold (<30)
"""
import os
import requests
from typing import Any, Optional
from dataclasses import dataclass

TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"

@dataclass
class SMAData:
    value: float
    timestamp: str
    raw: Any = None

@dataclass
class MACDData:
    macd: float
    macd_signal: float
    macd_hist: float
    timestamp: str
    raw: Any = None

@dataclass
class BollingerBandsData:
    upper_band: float
    middle_band: float
    lower_band: float
    timestamp: str
    raw: Any = None

@dataclass
class RSIData:
    value: float
    timestamp: str
    raw: Any = None

@dataclass
class TechnicalIndicators:
    sma_200: Optional[SMAData] = None
    macd: Optional[MACDData] = None
    bbands: Optional[BollingerBandsData] = None
    rsi: Optional[RSIData] = None
    current_price: Optional[float] = None

def get_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Missing: {key}")
    return value

def fetch_sma(symbol: str = "BTC/USD", interval: str = "1day", time_period: int = 200) -> SMAData:
    """Fetch Simple Moving Average (SMA) - Trend indicator."""
    api_key = get_env("TWELVE_DATA_API_KEY")

    response = requests.get(
        f"{TWELVE_DATA_BASE_URL}/sma",
        params={
            "symbol": symbol,
            "interval": interval,
            "time_period": time_period,
            "apikey": api_key,
            "outputsize": 1,
        }
    )
    response.raise_for_status()
    data = response.json()

    if "values" not in data or not data["values"]:
        raise ValueError(f"SMA data not available: {data.get('message', 'Unknown error')}")

    latest = data["values"][0]
    return SMAData(
        value=float(latest["sma"]),
        timestamp=latest["datetime"],
        raw=data,
    )

def fetch_macd(
    symbol: str = "BTC/USD",
    interval: str = "1day",
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> MACDData:
    """Fetch MACD - Momentum indicator."""
    api_key = get_env("TWELVE_DATA_API_KEY")

    response = requests.get(
        f"{TWELVE_DATA_BASE_URL}/macd",
        params={
            "symbol": symbol,
            "interval": interval,
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
            "apikey": api_key,
            "outputsize": 1,
        }
    )
    response.raise_for_status()
    data = response.json()

    if "values" not in data or not data["values"]:
        raise ValueError(f"MACD data not available: {data.get('message', 'Unknown error')}")

    latest = data["values"][0]
    return MACDData(
        macd=float(latest["macd"]),
        macd_signal=float(latest["macd_signal"]),
        macd_hist=float(latest["macd_hist"]),
        timestamp=latest["datetime"],
        raw=data,
    )

def fetch_bbands(
    symbol: str = "BTC/USD",
    interval: str = "1day",
    time_period: int = 20,
    sd: float = 2.0
) -> BollingerBandsData:
    """Fetch Bollinger Bands - Volatility indicator."""
    api_key = get_env("TWELVE_DATA_API_KEY")

    response = requests.get(
        f"{TWELVE_DATA_BASE_URL}/bbands",
        params={
            "symbol": symbol,
            "interval": interval,
            "time_period": time_period,
            "sd": sd,
            "apikey": api_key,
            "outputsize": 1,
        }
    )
    response.raise_for_status()
    data = response.json()

    if "values" not in data or not data["values"]:
        raise ValueError(f"Bollinger Bands data not available: {data.get('message', 'Unknown error')}")

    latest = data["values"][0]
    return BollingerBandsData(
        upper_band=float(latest["upper_band"]),
        middle_band=float(latest["middle_band"]),
        lower_band=float(latest["lower_band"]),
        timestamp=latest["datetime"],
        raw=data,
    )

def fetch_rsi(symbol: str = "BTC/USD", interval: str = "1day", time_period: int = 14) -> RSIData:
    """Fetch RSI - Sentiment/Overbought/Oversold indicator."""
    api_key = get_env("TWELVE_DATA_API_KEY")

    response = requests.get(
        f"{TWELVE_DATA_BASE_URL}/rsi",
        params={
            "symbol": symbol,
            "interval": interval,
            "time_period": time_period,
            "apikey": api_key,
            "outputsize": 1,
        }
    )
    response.raise_for_status()
    data = response.json()

    if "values" not in data or not data["values"]:
        raise ValueError(f"RSI data not available: {data.get('message', 'Unknown error')}")

    latest = data["values"][0]
    return RSIData(
        value=float(latest["rsi"]),
        timestamp=latest["datetime"],
        raw=data,
    )

def fetch_all_indicators(symbol: str = "BTC/USD", interval: str = "1day") -> TechnicalIndicators:
    """Fetch all technical indicators for a symbol."""
    return TechnicalIndicators(
        sma_200=fetch_sma(symbol, interval, time_period=200),
        macd=fetch_macd(symbol, interval),
        bbands=fetch_bbands(symbol, interval),
        rsi=fetch_rsi(symbol, interval),
    )

def format_indicators_context(indicators: TechnicalIndicators, current_price: float) -> str:
    """Format technical indicators as context for AI prompt (raw values only, no interpretation)."""
    lines = ["TECHNICAL INDICATORS:"]

    # SMA 200 - Trend
    if indicators.sma_200:
        lines.append(f"1. SMA(200): ${indicators.sma_200.value:,.2f}")

    # MACD - Momentum
    if indicators.macd:
        lines.append(f"2. MACD(12,26,9): MACD={indicators.macd.macd:.2f}, Signal={indicators.macd.macd_signal:.2f}, Histogram={indicators.macd.macd_hist:.2f}")

    # Bollinger Bands - Volatility
    if indicators.bbands:
        lines.append(f"3. Bollinger Bands(20,2): Upper=${indicators.bbands.upper_band:,.2f}, Middle=${indicators.bbands.middle_band:,.2f}, Lower=${indicators.bbands.lower_band:,.2f}")

    # RSI - Sentiment
    if indicators.rsi:
        lines.append(f"4. RSI(14): {indicators.rsi.value:.1f}")

    return "\n".join(lines)
```

---

### Step 3.3: Portfolio State Manager (with Capital Tracking)

Create a persistent state manager to track position and **portfolio capital** ($10,000 starting).

Create `python/src/state_manager.py`:

```python
"""
Persistent state manager for tracking trading position and portfolio capital.
Each configuration starts with $10,000 and trades to maximize P&L.
"""
import json
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field

STATE_DIR = ".states"
DEFAULT_STATE_FILE = "position_state.json"
STARTING_CAPITAL = 10000.0

@dataclass
class Position:
    action: str           # "buy"
    price: float          # Entry price per BTC
    timestamp: str        # ISO format timestamp
    symbol: str = "BTC"
    btc_amount: float = 0.0      # How much BTC was bought
    capital_used: float = 0.0    # How much USD was spent

@dataclass
class Portfolio:
    starting_capital: float = STARTING_CAPITAL
    current_capital: float = STARTING_CAPITAL
    position: Optional[Position] = None
    trade_history: List[Dict[str, Any]] = field(default_factory=list)
    total_realized_pnl: float = 0.0

def get_state_dir() -> str:
    """Get the path to the states directory."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), STATE_DIR)

def get_state_file_path(state_file: str = DEFAULT_STATE_FILE) -> str:
    """Get the path to the state file."""
    state_dir = get_state_dir()
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, state_file)

def load_portfolio(state_file: str = DEFAULT_STATE_FILE) -> Portfolio:
    """Load portfolio from persistent state (creates new if not exists)."""
    path = get_state_file_path(state_file)
    if not os.path.exists(path):
        return Portfolio()

    try:
        with open(path, "r") as f:
            data = json.load(f)
            position = None
            if data.get("position"):
                position = Position(**data["position"])
            return Portfolio(
                starting_capital=data.get("starting_capital", STARTING_CAPITAL),
                current_capital=data.get("current_capital", STARTING_CAPITAL),
                position=position,
                trade_history=data.get("trade_history", []),
                total_realized_pnl=data.get("total_realized_pnl", 0.0),
            )
    except (json.JSONDecodeError, KeyError):
        return Portfolio()

def save_portfolio(portfolio: Portfolio, state_file: str = DEFAULT_STATE_FILE) -> None:
    """Save portfolio to persistent state."""
    path = get_state_file_path(state_file)
    data = {
        "starting_capital": portfolio.starting_capital,
        "current_capital": portfolio.current_capital,
        "position": asdict(portfolio.position) if portfolio.position else None,
        "trade_history": portfolio.trade_history,
        "total_realized_pnl": portfolio.total_realized_pnl,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_portfolio_value(portfolio: Portfolio, current_price: float) -> float:
    """Calculate current portfolio value."""
    if portfolio.position:
        return portfolio.position.btc_amount * current_price
    return portfolio.current_capital

def format_portfolio_context(portfolio: Portfolio, current_price: float) -> str:
    """Format portfolio status for AI prompt."""
    portfolio_value = get_portfolio_value(portfolio, current_price)
    total_pnl = portfolio_value - portfolio.starting_capital
    pnl_percent = (total_pnl / portfolio.starting_capital) * 100
    pnl_sign = "+" if total_pnl >= 0 else ""

    if portfolio.position:
        unrealized_pnl = (current_price - portfolio.position.price) * portfolio.position.btc_amount
        unrealized_sign = "+" if unrealized_pnl >= 0 else ""
        position_status = f"""OPEN POSITION:
- BTC Holdings: {portfolio.position.btc_amount:.6f} BTC
- Entry Price: ${portfolio.position.price:,.2f}
- Current Price: ${current_price:,.2f}
- Unrealized P&L: {unrealized_sign}${unrealized_pnl:,.2f}"""
    else:
        position_status = "POSITION: None (cash)"

    return f"""PORTFOLIO STATUS:
- Starting Capital: ${portfolio.starting_capital:,.2f}
- Portfolio Value: ${portfolio_value:,.2f}
- Available Cash: ${portfolio.current_capital:,.2f}
- Total P&L: {pnl_sign}${total_pnl:,.2f} ({pnl_sign}{pnl_percent:.2f}%)
- Trades Completed: {len(portfolio.trade_history)}

{position_status}

GOAL: Maximize P&L through smart trading decisions."""
```

---

### Step 3.4: Exchange MCP Server

Create an MCP (Model Context Protocol) server that provides exchange tools for the AI agent. The agent can decide **how much** to buy or sell based on its analysis. The exchange is **symbol-agnostic** and works with any trading pair.

**Key Features:**

- **Symbol-agnostic**: Works with any asset (BTC, ETH, SOL, etc.)
- **Flexible position sizing**: Agent decides the USD amount to buy or asset amount to sell
- **Four tools**: `get_portfolio`, `buy`, `sell`, `hold`
- **Partial trades**: No need to go all-in; agent can scale positions

**Note**: Price data is provided in the system prompt (fetched from Band Protocol before agent runs), so no separate `get_price` tool is needed.

Create `python/src/exchange_mcp.py`:

```python
"""
Exchange MCP Server - Simulated exchange for AI trading agents.

Provides MCP tools for:
- get_portfolio: Get current portfolio status
- buy: Buy asset with specified USD amount
- sell: Sell specified asset amount
- hold: Do nothing (keep current position)

The agent decides trade sizes based on its analysis.
Price data is provided in the system prompt, not via a tool.
Symbol-agnostic: works with any trading pair available in Band Protocol.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict

from .price_client import PriceContext
from .state_manager import (
    load_portfolio, save_portfolio, get_portfolio_value,
    Portfolio, Position, STARTING_CAPITAL
)


@dataclass
class TradeResult:
    success: bool
    action: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ExchangeMCP:
    """
    Simulated exchange with MCP-style tool interface.
    Symbol-agnostic: supports any asset available in Band Protocol.
    Each instance manages a specific portfolio state file.

    Uses PriceContext singleton from price_client for price data.
    Price must be fetched via fetch_price() before using exchange tools.
    """

    def __init__(self, state_file: str = "default.json", default_symbol: str = "BTC"):
        self.state_file = state_file
        self.default_symbol = default_symbol

    def get_price(self, symbol: str) -> float:
        """Get price from shared PriceContext."""
        ctx = PriceContext.get_instance()
        return ctx.get_price(symbol)

    # =========================================
    # MCP TOOLS
    # =========================================

    def tool_get_portfolio(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        MCP Tool: Get current portfolio status.

        Args:
            symbol: Asset symbol to check position for (default: configured symbol)

        Returns portfolio value, cash balance, asset holdings, and P&L.
        """
        symbol = symbol or self.default_symbol
        portfolio = load_portfolio(self.state_file)
        current_price = self.get_price(symbol)
        portfolio_value = get_portfolio_value(portfolio, current_price)
        total_pnl = portfolio_value - portfolio.starting_capital
        pnl_percent = (total_pnl / portfolio.starting_capital) * 100

        result = {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "starting_capital": portfolio.starting_capital,
            "portfolio_value": round(portfolio_value, 2),
            "available_cash": round(portfolio.current_capital, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(pnl_percent, 2),
            "trades_completed": len(portfolio.trade_history),
            "has_position": portfolio.position is not None,
        }

        if portfolio.position:
            position_value = portfolio.position.asset_amount * current_price
            unrealized_pnl = position_value - portfolio.position.capital_used
            result["position"] = {
                "symbol": portfolio.position.symbol,
                "asset_amount": round(portfolio.position.asset_amount, 8),
                "entry_price": round(portfolio.position.price, 2),
                "current_price": round(current_price, 2),
                "position_value": round(position_value, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
            }

        return result

    def tool_buy(self, usd_amount: float, symbol: Optional[str] = None) -> TradeResult:
        """
        MCP Tool: Buy asset with specified USD amount.

        Args:
            usd_amount: Amount of USD to spend.
                        Must be > 0 and <= available cash.
            symbol: Asset symbol to buy (default: configured symbol)

        Returns:
            TradeResult with success status and details.
        """
        symbol = symbol or self.default_symbol
        portfolio = load_portfolio(self.state_file)
        current_price = self.get_price(symbol)

        # Validation
        if usd_amount <= 0:
            return TradeResult(
                success=False,
                action="buy",
                message="USD amount must be greater than 0.",
            )

        if usd_amount > portfolio.current_capital:
            return TradeResult(
                success=False,
                action="buy",
                message=f"Insufficient funds. Available: ${portfolio.current_capital:,.2f}, Requested: ${usd_amount:,.2f}",
            )

        # Calculate asset amount
        asset_to_buy = usd_amount / current_price

        # Update or create position
        if portfolio.position and portfolio.position.symbol == symbol:
            # Add to existing position (average up/down)
            old_value = portfolio.position.asset_amount * portfolio.position.price
            new_value = old_value + usd_amount
            new_asset_total = portfolio.position.asset_amount + asset_to_buy
            new_avg_price = new_value / new_asset_total

            portfolio.position.asset_amount = new_asset_total
            portfolio.position.price = new_avg_price
            portfolio.position.capital_used += usd_amount
            portfolio.position.timestamp = datetime.now().isoformat()
        elif portfolio.position and portfolio.position.symbol != symbol:
            return TradeResult(
                success=False,
                action="buy",
                message=f"Already have a position in {portfolio.position.symbol}. Sell it first before buying {symbol}.",
            )
        else:
            # New position
            portfolio.position = Position(
                action="buy",
                price=current_price,
                timestamp=datetime.now().isoformat(),
                symbol=symbol,
                asset_amount=asset_to_buy,
                capital_used=usd_amount,
            )

        # Deduct cash
        portfolio.current_capital -= usd_amount

        # Record trade
        portfolio.trade_history.append({
            "type": "buy",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "usd_amount": usd_amount,
            "asset_amount": asset_to_buy,
            "price": current_price,
        })

        save_portfolio(portfolio, self.state_file)

        return TradeResult(
            success=True,
            action="buy",
            message=f"Bought {asset_to_buy:.8f} {symbol} for ${usd_amount:,.2f} at ${current_price:,.2f}",
            details={
                "symbol": symbol,
                "asset_bought": round(asset_to_buy, 8),
                "usd_spent": round(usd_amount, 2),
                "price": round(current_price, 2),
                "new_asset_total": round(portfolio.position.asset_amount, 8),
                "remaining_cash": round(portfolio.current_capital, 2),
            }
        )

    def tool_sell(self, asset_amount: float, symbol: Optional[str] = None) -> TradeResult:
        """
        MCP Tool: Sell specified amount of asset.

        Args:
            asset_amount: Amount of asset to sell.
                          Must be > 0 and <= current holdings.
            symbol: Asset symbol to sell (default: configured symbol)

        Returns:
            TradeResult with success status and details.
        """
        symbol = symbol or self.default_symbol
        portfolio = load_portfolio(self.state_file)
        current_price = self.get_price(symbol)

        # Validation
        if portfolio.position is None:
            return TradeResult(
                success=False,
                action="sell",
                message=f"No position to sell.",
            )

        if portfolio.position.symbol != symbol:
            return TradeResult(
                success=False,
                action="sell",
                message=f"No {symbol} position. Current position is in {portfolio.position.symbol}.",
            )

        if asset_amount <= 0:
            return TradeResult(
                success=False,
                action="sell",
                message="Asset amount must be greater than 0.",
            )

        if asset_amount > portfolio.position.asset_amount:
            return TradeResult(
                success=False,
                action="sell",
                message=f"Insufficient {symbol}. Holdings: {portfolio.position.asset_amount:.8f}, Requested: {asset_amount:.8f}",
            )

        # Calculate sale proceeds
        sale_value = asset_amount * current_price

        # Calculate P&L for this portion
        portion_ratio = asset_amount / portfolio.position.asset_amount
        portion_cost = portfolio.position.capital_used * portion_ratio
        pnl = sale_value - portion_cost
        pnl_percent = (pnl / portion_cost) * 100 if portion_cost > 0 else 0

        # Update position
        portfolio.position.asset_amount -= asset_amount
        portfolio.position.capital_used -= portion_cost

        # Add proceeds to cash
        portfolio.current_capital += sale_value

        # Update realized P&L
        portfolio.total_realized_pnl += pnl

        # Record trade
        portfolio.trade_history.append({
            "type": "sell",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "asset_amount": asset_amount,
            "usd_received": sale_value,
            "price": current_price,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
        })

        # Clear position if fully sold
        remaining_asset = portfolio.position.asset_amount
        if remaining_asset < 0.00000001:  # Essentially zero
            portfolio.position = None
            remaining_asset = 0

        save_portfolio(portfolio, self.state_file)

        return TradeResult(
            success=True,
            action="sell",
            message=f"Sold {asset_amount:.8f} {symbol} for ${sale_value:,.2f} at ${current_price:,.2f}. P&L: ${pnl:+,.2f} ({pnl_percent:+.2f}%)",
            details={
                "symbol": symbol,
                "asset_sold": round(asset_amount, 8),
                "usd_received": round(sale_value, 2),
                "price": round(current_price, 2),
                "pnl": round(pnl, 2),
                "pnl_percent": round(pnl_percent, 2),
                "remaining_asset": round(remaining_asset, 8),
                "new_cash_balance": round(portfolio.current_capital, 2),
            }
        )

    def tool_hold(self, symbol: Optional[str] = None) -> TradeResult:
        """
        MCP Tool: Hold current position (do nothing).

        Args:
            symbol: Asset symbol for price reference (default: configured symbol)

        Use this when the agent decides not to trade.
        """
        symbol = symbol or self.default_symbol
        portfolio = load_portfolio(self.state_file)
        current_price = self.get_price(symbol)
        portfolio_value = get_portfolio_value(portfolio, current_price)

        message = "Holding position. "
        if portfolio.position:
            position_value = portfolio.position.asset_amount * current_price
            unrealized_pnl = position_value - portfolio.position.capital_used
            message += f"Current {portfolio.position.symbol}: {portfolio.position.asset_amount:.8f}, Unrealized P&L: ${unrealized_pnl:+,.2f}"
        else:
            message += f"No position. Cash: ${portfolio.current_capital:,.2f}"

        return TradeResult(
            success=True,
            action="hold",
            message=message,
            details={
                "portfolio_value": round(portfolio_value, 2),
                "has_position": portfolio.position is not None,
            }
        )


# =========================================
# MCP TOOL DEFINITIONS (for AI prompt)
# =========================================

def get_exchange_tools(symbol: str = "BTC") -> list:
    """
    Get MCP tool definitions for the exchange.
    Symbol is used in descriptions for clarity.
    """
    return [
        {
            "name": "get_portfolio",
            "description": f"Get current portfolio status including cash balance, {symbol} holdings, total value, and P&L. Call this first to understand your current position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": f"Asset symbol (default: {symbol})",
                        "default": symbol
                    }
                },
                "required": []
            }
        },
        {
            "name": "buy",
            "description": f"Buy {symbol} with a specified USD amount. You decide how much to spend based on your analysis and risk tolerance. You don't have to use all your cash.",
            "parameters": {
                "type": "object",
                "properties": {
                    "usd_amount": {
                        "type": "number",
                        "description": "Amount of USD to spend. Must be > 0 and <= available cash."
                    },
                    "symbol": {
                        "type": "string",
                        "description": f"Asset symbol to buy (default: {symbol})",
                        "default": symbol
                    }
                },
                "required": ["usd_amount"]
            }
        },
        {
            "name": "sell",
            "description": f"Sell a specified amount of {symbol}. You decide how much to sell based on your analysis. You don't have to sell your entire position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_amount": {
                        "type": "number",
                        "description": "Amount of asset to sell. Must be > 0 and <= current holdings."
                    },
                    "symbol": {
                        "type": "string",
                        "description": f"Asset symbol to sell (default: {symbol})",
                        "default": symbol
                    }
                },
                "required": ["asset_amount"]
            }
        },
        {
            "name": "hold",
            "description": "Do nothing - keep your current position unchanged. Use this when you want to wait for better conditions or are satisfied with your current position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": f"Asset symbol for price reference (default: {symbol})",
                        "default": symbol
                    }
                },
                "required": []
            }
        },
    ]
```

---

### Step 3.5: Update Price Client for Symbol Support

Update `python/src/price_client.py` to support fetching any symbol:

```python
def o (symbol: str = "BTC") -> PriceData:
    """
    Fetch current price for a symbol from Band Protocol API.
    No API key required.

    Args:
        symbol: Asset symbol (e.g., "BTC", "ETH", "SOL")

    Price is returned in 9 decimal places.
    """
    response = requests.get(BAND_PROTOCOL_API_URL)
    response.raise_for_status()
    data = response.json()

    # Find symbol in the prices list
    signal_id = f"CS:{symbol}-USD"
    symbol_data = None
    for price_item in data.get("prices", []):
        if price_item.get("signal_id") == signal_id:
            symbol_data = price_item
            break

    if not symbol_data or symbol_data.get("status") != "PRICE_STATUS_AVAILABLE":
        raise ValueError(f"{symbol} price not available from Band Protocol")

    # Price has 9 decimal places
    raw_price = int(symbol_data.get("price", 0))
    price = raw_price / 1_000_000_000

    return PriceData(
        symbol=symbol,
        price=price,
        timestamp=int(symbol_data.get("timestamp", 0)) if symbol_data.get("timestamp") else None,
        raw=symbol_data,
    )
```

---

### Step 3.6: Update State Manager for Symbol Support

Update `python/src/state_manager.py` Position dataclass:

```python
@dataclass
class Position:
    action: str           # "buy"
    price: float          # Entry price per unit
    timestamp: str        # ISO format timestamp
    symbol: str           # Asset symbol (e.g., "BTC", "ETH")
    asset_amount: float = 0.0    # How much asset was bought
    capital_used: float = 0.0    # How much USD was spent
```

---

### Step 3.7: Update Directory Structure

Update the final directory structure to include the Exchange MCP:

```
python/
├── src/
│   ├── __init__.py
│   ├── types.py
│   ├── cerebras_client.py
│   ├── membit_client.py
│   ├── price_client.py          # Updated: symbol support
│   ├── indicators_client.py
│   ├── state_manager.py         # Updated: symbol support
│   ├── exchange_mcp.py          # NEW: Exchange MCP server
│   ├── agent.py                  # Agent with tool support
│   ├── scheduler.py              # Automated hourly runs
│   └── examples/
│       ├── __init__.py
│       └── main.py               # Interactive entry point
├── pyproject.toml
├── .env.example
├── .states/                      # Portfolio states (gitignored)
└── README.md
```

---

### Trading Rules with Exchange MCP

| Rule             | Description                            |
| ---------------- | -------------------------------------- |
| Starting Capital | $10,000 per configuration              |
| Asset            | Any symbol available in Band Protocol  |
| Position Sizing  | **Agent decides** (flexible amounts)   |
| Goal             | Maximize P&L                           |
| Available Tools  | `buy`, `sell`, `hold`, `get_portfolio` |

**Key Features:**

- **Symbol-agnostic**: Works with BTC, ETH, SOL, or any supported asset
- **Flexible position sizing**: Agent is NOT forced to go all-in
- **Partial trades**: Agent can buy/sell partial amounts
- **Position management**: Agent decides position size based on confidence level

**Example Agent Decisions:**

- Low confidence bullish → Buy with 20% of cash
- High confidence bullish → Buy with 80% of cash
- Taking profits → Sell 50% of position
- Stop loss → Sell 100% of position
- Uncertain → Hold

---

## Phase 4: Documentation and Configuration

### Step 4.1: Create Python README

Create `python/README.md`:

````markdown
# AI API Client - Python

Python client for Cerebras AI with optional Membit integration.

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```
````

2. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Environment Variables

- `CEREBRAS_API_KEY` - Required for Cerebras API access
- `TWELVE_DATA_API_KEY` - Required for technical indicators (free tier available)
- `MEMBIT_API_KEY` - Required for Membit integration (Scenario 2 only)

Note: Band Protocol price API is free and requires no API key.

## Usage

Run the interactive trading assistant:

```bash
uv run python -m src.examples.main
```

This will prompt you to:

1. Select a model
2. Choose whether to enable Membit for news/sentiment

Each model + Membit combination maintains its own position state in `.states/`.

## Available Models (Cerebras)

- `llama3.1-8b` - Fast, efficient
- `llama3.1-70b` - More capable
- `llama-3.3-70b` - Latest, recommended

```

### Step 4.2: Create .env.example files

Create `python/.env.example`:
```

# Required for AI inference (get key at https://cloud.cerebras.ai/)

CEREBRAS_API_KEY=your_cerebras_api_key_here

# Required for technical indicators (get free key at https://twelvedata.com/)

TWELVE_DATA_API_KEY=your_twelve_data_api_key_here

# Required for Scenario 2 only (Membit integration)

MEMBIT_API_KEY=your_membit_api_key_here

# Note: Band Protocol price API is free and requires no API key

```

Create `node/.env.example` (move from root if exists):
```

ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here

````

### Step 4.3: Update root README

Create root `README.md`:
```markdown
# AI API Client - Monorepo

A multi-language AI API client supporting various AI providers.

## Structure

- **[node/](./node/)** - Node.js/TypeScript implementation (Claude, OpenAI, Gemini)
- **[python/](./python/)** - Python implementation (Cerebras with Membit integration)

## Quick Start

### Node.js

```bash
cd node
pnpm install
pnpm dev
````

### Python

```bash
cd python
uv sync
uv run python -m src.examples.main
```

See individual README files in each directory for detailed documentation.

````

---

## Phase 5: Scheduled Execution & Membit Comparison

### Overview

Run the trading assistant automatically every hour across all models, comparing **with Membit tools** vs **without Membit tools** for each model.

**Key Features:**
- **Exchange MCP**: Agent uses exchange tools (`buy`, `sell`, `hold`) to make trades
- **Membit MCP** (optional): Agent can query news/sentiment for better decisions
- **Flexible sizing**: Agent decides how much to buy/sell based on confidence
- **Symbol-agnostic**: Works with any asset available in Band Protocol

### Trading Simulation

Each of the 6 configurations receives **$10,000 starting capital**. The goal is to **maximize P&L (profit and loss)**.

| Rule | Description |
|------|-------------|
| Starting Capital | $10,000 per configuration |
| Asset | Configurable (default: BTC) |
| Position Sizing | **Agent decides** (partial trades allowed) |
| Goal | Maximize P&L |
| Exchange Tools | `buy`, `sell`, `hold`, `get_portfolio` |
| Membit Tools | `search_posts`, `search_clusters`, `get_cluster_info` |

### Comparison Matrix

| Config | Model | Mode | Starting Capital |
|--------|-------|------|------------------|
| 1 | llama3.1-8b | basic | $10,000 |
| 2 | llama3.1-8b | membit | $10,000 |
| 3 | llama-3.3-70b | basic | $10,000 |
| 4 | llama-3.3-70b | membit | $10,000 |
| 5 | qwen-3-32b | basic | $10,000 |
| 6 | qwen-3-32b | membit | $10,000 |

**Total configurations per run: 6** (3 models × 2 modes)

### Step 5.1: Create Agent Module with MCP Tool Support

Create `python/src/agent.py`:
```python
"""
AI Agent with MCP-style tool support.
Supports both Exchange tools (trading) and Membit tools (sentiment).
The agent decides when and how to use available tools.
"""
import json
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict

from .cerebras_client import call_cerebras
from .types import CallOptions
from .exchange_mcp import ExchangeMCP, get_exchange_tools, TradeResult
from .price_client import PriceContext
from .membit_client import MembitWrapper


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    name: str
    result: Any
    error: Optional[str] = None


# Membit tools (MCP-style definitions)
MEMBIT_TOOLS = [
    {
        "name": "search_posts",
        "description": "Search for recent social media posts about a topic. Returns current news, sentiment, and discussions. Use this to understand market sentiment before making trading decisions.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g., 'Bitcoin crypto market news')"},
                "limit": {"type": "integer", "description": "Max posts to return", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_clusters",
        "description": "Search for trending topic clusters. Use this to discover what topics are trending.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for trending topics"},
                "limit": {"type": "integer", "description": "Max clusters to return", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_cluster_info",
        "description": "Get detailed info about a specific trending cluster by its label.",
        "parameters": {
            "type": "object",
            "properties": {
                "cluster_label": {"type": "string", "description": "The cluster label to get info for"},
                "limit": {"type": "integer", "description": "Max items to return", "default": 5}
            },
            "required": ["cluster_label"]
        }
    }
]


def format_tools_for_prompt(tools: List[Dict]) -> str:
    """Format tool definitions for the system prompt."""
    if not tools:
        return ""

    lines = [
        "AVAILABLE TOOLS:",
        "You can call these tools to gather information and execute trades.",
        "To use a tool, respond with:",
        'TOOL_CALL: {"name": "tool_name", "arguments": {...}}',
        "",
        "You may call multiple tools. After gathering information, make your trading decision.",
        ""
    ]

    for tool in tools:
        params = tool.get("parameters", {}).get("properties", {})
        param_list = ", ".join([f"{k}: {v.get('type', 'any')}" for k, v in params.items()])
        lines.append(f"- {tool['name']}({param_list}): {tool['description']}")

    return "\n".join(lines)


def parse_tool_calls(response: str) -> List[ToolCall]:
    """Parse tool calls from AI response."""
    calls = []
    # Match TOOL_CALL: followed by JSON (handles nested objects)
    pattern = r'TOOL_CALL:\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'

    for match in re.finditer(pattern, response, re.IGNORECASE):
        try:
            data = json.loads(match.group(1))
            calls.append(ToolCall(
                name=data.get("name", ""),
                arguments=data.get("arguments", {})
            ))
        except json.JSONDecodeError:
            continue

    return calls


class TradingAgent:
    """
    AI Trading Agent with access to Exchange and Membit MCP tools.
    """

    def __init__(
        self,
        state_file: str,
        symbol: str = "BTC",
        use_membit: bool = False,
    ):
        self.state_file = state_file
        self.symbol = symbol
        self.use_membit = use_membit

        # Initialize Exchange MCP
        self.exchange = ExchangeMCP(state_file=state_file, default_symbol=symbol)

        # Initialize Membit if enabled
        self.membit = MembitWrapper() if use_membit else None

    def get_available_tools(self) -> List[Dict]:
        """Get all available tools for this agent."""
        tools = get_exchange_tools(self.symbol)
        if self.use_membit:
            tools.extend(MEMBIT_TOOLS)
        return tools

    def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call and return the result."""
        try:
            name = tool_call.name
            args = tool_call.arguments

            # Exchange tools
            if name == "get_portfolio":
                result = self.exchange.tool_get_portfolio(args.get("symbol"))
                return ToolResult(name=name, result=json.dumps(result, indent=2))

            elif name == "buy":
                result = self.exchange.tool_buy(
                    usd_amount=args.get("usd_amount", 0),
                    symbol=args.get("symbol")
                )
                return ToolResult(
                    name=name,
                    result=result.message if result.success else None,
                    error=result.message if not result.success else None
                )

            elif name == "sell":
                result = self.exchange.tool_sell(
                    asset_amount=args.get("asset_amount", 0),
                    symbol=args.get("symbol")
                )
                return ToolResult(
                    name=name,
                    result=result.message if result.success else None,
                    error=result.message if not result.success else None
                )

            elif name == "hold":
                result = self.exchange.tool_hold(args.get("symbol"))
                return ToolResult(name=name, result=result.message)

            # Membit tools
            elif name == "search_posts" and self.membit:
                posts = self.membit.search_posts(
                    query=args.get("query", self.symbol),
                    limit=args.get("limit", 10)
                )
                formatted = self.membit.format_posts_for_prompt(posts)
                return ToolResult(name=name, result=formatted)

            elif name == "search_clusters" and self.membit:
                clusters = self.membit.search_clusters(
                    query=args.get("query", self.symbol),
                    limit=args.get("limit", 5)
                )
                formatted = self.membit.format_clusters_for_prompt(clusters)
                return ToolResult(name=name, result=formatted)

            elif name == "get_cluster_info" and self.membit:
                info = self.membit.get_cluster_info(
                    cluster_label=args.get("cluster_label", ""),
                    limit=args.get("limit", 5)
                )
                return ToolResult(name=name, result=json.dumps(info, indent=2))

            else:
                return ToolResult(name=name, result=None, error=f"Unknown tool: {name}")

        except Exception as e:
            return ToolResult(name=tool_call.name, result=None, error=str(e))

    def run(
        self,
        model: str,
        market_context: str,
        max_tool_rounds: int = 3,
        max_tokens: int = 1200,
    ) -> Dict[str, Any]:
        """
        Run the trading agent.

        Args:
            model: Cerebras model to use
            market_context: Pre-formatted market data (price, indicators)
            max_tool_rounds: Maximum rounds of tool calling
            max_tokens: Max tokens for AI response

        Returns:
            Dict with final_response, tool_calls, and executed_action
        """
        tools = self.get_available_tools()
        tool_prompt = format_tools_for_prompt(tools)

        system_prompt = f"""You are an AI trading agent managing a portfolio.
Your goal is to maximize profit by making smart trading decisions.

{market_context}

{tool_prompt}

INSTRUCTIONS:
1. First, call get_portfolio to see your current position and cash balance
2. Analyze the market data provided above
3. If Membit tools are available, optionally search for news/sentiment
4. Make a trading decision: buy (specify USD amount), sell (specify asset amount), or hold
5. You decide HOW MUCH to trade based on your confidence level

Remember: You don't have to go all-in. Scale your position based on conviction.
"""

        user_message = f"Analyze the {self.symbol} market and execute your trading decision."

        tool_calls_made = []
        conversation = []
        executed_action = None

        # Initial call
        response = call_cerebras(CallOptions(
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            max_tokens=max_tokens,
        ))

        current_response = response.content
        conversation.append({"role": "assistant", "content": current_response})

        # Tool calling loop
        for round_num in range(max_tool_rounds):
            tool_calls = parse_tool_calls(current_response)
            if not tool_calls:
                break

            # Execute tools
            tool_results = []
            for tc in tool_calls:
                print(f"    [Tool] {tc.name}({json.dumps(tc.arguments)})")
                result = self.execute_tool(tc)
                tool_results.append(result)
                tool_calls_made.append({
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "result": result.result,
                    "error": result.error,
                })

                # Track executed trading action
                if tc.name in ["buy", "sell", "hold"] and not result.error:
                    executed_action = {
                        "action": tc.name,
                        "arguments": tc.arguments,
                        "result": result.result,
                    }

            # Format results
            results_text = "\n\n".join([
                f"TOOL_RESULT ({r.name}):\n{r.result if not r.error else f'Error: {r.error}'}"
                for r in tool_results
            ])

            # Check if a trade was executed - if so, we're done
            if executed_action:
                conversation.append({"role": "tool_results", "content": results_text})
                break

            # Continue conversation with tool results
            follow_up = f"Tool results:\n\n{results_text}\n\nContinue your analysis and make a trading decision."

            response = call_cerebras(CallOptions(
                system_prompt=system_prompt,
                user_message=f"{user_message}\n\n{follow_up}",
                model=model,
                max_tokens=max_tokens,
            ))

            current_response = response.content
            conversation.append({"role": "tool_results", "content": results_text})
            conversation.append({"role": "assistant", "content": current_response})

        return {
            "final_response": current_response,
            "tool_calls": tool_calls_made,
            "conversation": conversation,
            "executed_action": executed_action,
        }
````

### Step 5.2: Update main.py to Use TradingAgent

Update `python/src/examples/main.py`:

```python
"""
AI Trading Assistant - Single entry point with interactive selection.
Uses TradingAgent with Exchange MCP and optional Membit tools.
"""
import sys
from dotenv import load_dotenv

from ..agent import TradingAgent
from ..price_client import PriceContext, fetch_price, format_price_context
from ..indicators_client import fetch_all_indicators, format_indicators_context

# Available models
MODELS = {
    "1": ("llama3.1-8b", "Fast, efficient"),
    "2": ("llama-3.3-70b", "Latest Llama, recommended"),
    "3": ("qwen-3-32b", "Qwen 32B"),
}

# Available symbols (from Band Protocol)
SYMBOLS = ["BTC", "ETH", "SOL", "AVAX", "LINK", "ATOM"]


def get_state_filename(model: str, symbol: str, use_membit: bool) -> str:
    """Generate unique state filename based on configuration."""
    membit_suffix = "_membit" if use_membit else "_basic"
    model_slug = model.replace(".", "_").replace("-", "_")
    return f"{model_slug}_{symbol.lower()}{membit_suffix}.json"


def select_model() -> str:
    """Interactive model selection."""
    print("\n=== Select Model ===")
    for key, (model, desc) in MODELS.items():
        print(f"  {key}. {model} - {desc}")

    while True:
        choice = input("\nEnter choice (1-3) [2]: ").strip() or "2"
        if choice in MODELS:
            return MODELS[choice][0]
        print("Invalid choice. Please enter 1, 2, or 3.")


def select_symbol() -> str:
    """Interactive symbol selection."""
    print("\n=== Select Symbol ===")
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"  {i}. {symbol}")

    while True:
        choice = input(f"\nEnter choice (1-{len(SYMBOLS)}) [1]: ").strip() or "1"
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(SYMBOLS):
                return SYMBOLS[idx]
        except ValueError:
            pass
        print(f"Invalid choice. Please enter 1-{len(SYMBOLS)}.")


def select_membit() -> bool:
    """Interactive Membit tools selection."""
    print("\n=== Enable Membit Tools? ===")
    print("  1. No  - AI uses only price + technical indicators")
    print("  2. Yes - AI can call Membit tools for news/sentiment")

    while True:
        choice = input("\nEnter choice (1-2) [1]: ").strip() or "1"
        if choice == "1":
            return False
        elif choice == "2":
            return True
        print("Invalid choice. Please enter 1 or 2.")


def main():
    load_dotenv()

    print("=" * 60)
    print("  AI Trading Assistant (with Exchange MCP)")
    print("=" * 60)

    # Step 1: Select configuration
    model = select_model()
    symbol = select_symbol()
    use_membit = select_membit()

    state_file = get_state_filename(model, symbol, use_membit)

    print(f"\n--- Configuration ---")
    print(f"Model: {model}")
    print(f"Symbol: {symbol}")
    print(f"Membit Tools: {'Enabled' if use_membit else 'Disabled'}")
    print(f"State file: {state_file}")
    print()

    # Step 2: Fetch market data (stored in global PriceContext)
    print(f"Fetching {symbol} price from Band Protocol...")
    price = fetch_price(symbol)  # Fetches and stores in PriceContext
    price_context_str = format_price_context(symbol)
    print(f"{price_context_str}")

    print(f"Fetching {symbol}/USD technical indicators from Twelve Data...")
    indicators = fetch_all_indicators(symbol=f"{symbol}/USD")
    indicators_context = format_indicators_context(indicators, price)
    print(f"{indicators_context}")

    # Step 3: Build market context for agent
    market_context = f"""CURRENT MARKET DATA:
{price_context_str}

{indicators_context}
"""

    # Step 4: Create and run the trading agent
    print(f"\n--- Running Trading Agent ---")
    print(f"Model: {model}")
    print(f"Membit: {'Enabled' if use_membit else 'Disabled'}")
    print()

    agent = TradingAgent(
        state_file=state_file,
        symbol=symbol,
        use_membit=use_membit,
    )

    result = agent.run(
        model=model,
        market_context=market_context,
        max_tool_rounds=3,
        max_tokens=1200,
    )

    # Step 5: Display results
    print(f"\n{'='*60}")
    print("AGENT RESPONSE:")
    print(f"{'='*60}")
    print(result["final_response"][:1000])  # Truncate if too long

    print(f"\n--- Tool Calls ({len(result['tool_calls'])}) ---")
    for tc in result["tool_calls"]:
        status = "✓" if not tc["error"] else f"✗ {tc['error']}"
        print(f"  {tc['name']}: {status}")

    if result["executed_action"]:
        action = result["executed_action"]
        print(f"\n{'='*60}")
        print(f"EXECUTED: {action['action'].upper()}")
        print(f"Result: {action['result']}")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print("NO TRADE EXECUTED")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
```

### Step 5.3: Create Scheduler for Automated Runs

Create `python/src/scheduler.py`:

```python
"""
Scheduled execution comparing Basic vs Membit-tools mode.
Each configuration starts with $10,000 and trades to maximize P&L.
Uses TradingAgent with Exchange MCP for flexible position sizing.
Runs continuously, triggering every hour.
"""
import json
import os
import time
import signal
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv

from .agent import TradingAgent
from .price_client import fetch_price, format_price_context, get_price
from .indicators_client import fetch_all_indicators, format_indicators_context
from .state_manager import load_portfolio, get_portfolio_value

# Configuration
MODELS = ["llama3.1-8b", "llama-3.3-70b", "qwen-3-32b"]
DEFAULT_SYMBOL = "BTC"  # Can be changed to any supported symbol
RESULTS_DIR = ".results"


def get_results_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), RESULTS_DIR)


def get_state_filename(model: str, symbol: str, use_membit: bool) -> str:
    suffix = "_membit" if use_membit else "_basic"
    model_slug = model.replace(".", "_").replace("-", "_")
    return f"{model_slug}_{symbol.lower()}{suffix}.json"


def run_single_agent(
    model: str,
    symbol: str,
    use_membit: bool,
    market_context: str,
) -> Dict[str, Any]:
    """Run a single trading agent and return results."""
    state_file = get_state_filename(model, symbol, use_membit)

    agent = TradingAgent(
        state_file=state_file,
        symbol=symbol,
        use_membit=use_membit,
    )

    result = agent.run(
        model=model,
        market_context=market_context,
        max_tool_rounds=3,
        max_tokens=1200,
    )

    # Get updated portfolio info
    portfolio = load_portfolio(state_file)
    current_price = agent.exchange.get_price(symbol)
    portfolio_value = get_portfolio_value(portfolio, current_price)

    return {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "symbol": symbol,
        "mode": "membit" if use_membit else "basic",
        "price": current_price,
        "portfolio_value": portfolio_value,
        "executed_action": result["executed_action"],
        "tool_calls_count": len(result["tool_calls"]),
        "response_excerpt": result["final_response"][:500],
    }


def run_once(symbol: str = DEFAULT_SYMBOL):
    """Run a single trading simulation cycle for all configurations."""
    print(f"\n{'='*60}")
    print(f"  Trading Simulation Run: {datetime.now().isoformat()}")
    print(f"  Symbol: {symbol} | Starting Capital: $10,000")
    print(f"{'='*60}\n")

    # Fetch market data once for all agents (stored in global PriceContext)
    price = fetch_price(symbol)  # Fetches and stores in PriceContext
    indicators = fetch_all_indicators(symbol=f"{symbol}/USD")

    price_context_str = format_price_context(symbol)
    indicators_context = format_indicators_context(indicators, price)

    market_context = f"""CURRENT MARKET DATA:
{price_context_str}

{indicators_context}
"""

    print(f"{symbol} Price: ${price:,.2f}\n")

    results = []

    for model in MODELS:
        for use_membit in [False, True]:
            mode = "membit" if use_membit else "basic"
            state_file = get_state_filename(model, symbol, use_membit)
            portfolio = load_portfolio(state_file)
            portfolio_value = get_portfolio_value(portfolio, price)

            print(f"[{model}] ({mode}) - Portfolio: ${portfolio_value:,.2f}")

            try:
                result = run_single_agent(model, symbol, use_membit, market_context)
                results.append(result)

                action_info = "no action"
                if result["executed_action"]:
                    action = result["executed_action"]
                    action_info = f"{action['action'].upper()}"

                tool_info = f" | {result['tool_calls_count']} tools" if result['tool_calls_count'] else ""
                print(f"  -> {action_info}{tool_info}")

            except Exception as e:
                print(f"  -> ERROR: {e}")
                results.append({
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "symbol": symbol,
                    "mode": mode,
                    "error": str(e)
                })

    # Save results
    results_dir = get_results_dir()
    os.makedirs(results_dir, exist_ok=True)
    filepath = os.path.join(results_dir, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(filepath, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {filepath}")

    # Print leaderboard
    print_leaderboard(symbol, price_data.price)

    return results


def print_leaderboard(symbol: str, current_price: float):
    """Print the current leaderboard sorted by portfolio value."""
    print(f"\n{'='*60}")
    print(f"  LEADERBOARD ({symbol})")
    print(f"{'='*60}")
    print(f"{'Config':<30} {'Value':<12} {'P&L':<12} {'Return':<10}")
    print("-" * 64)

    leaderboard = []
    for model in MODELS:
        for use_membit in [False, True]:
            mode = "membit" if use_membit else "basic"
            state_file = get_state_filename(model, symbol, use_membit)
            portfolio = load_portfolio(state_file)
            portfolio_value = get_portfolio_value(portfolio, current_price)
            pnl = portfolio_value - portfolio.starting_capital
            pnl_percent = (pnl / portfolio.starting_capital) * 100
            leaderboard.append((f"{model} ({mode})", portfolio_value, pnl, pnl_percent))

    leaderboard.sort(key=lambda x: x[1], reverse=True)
    for i, (config, value, pnl, pnl_pct) in enumerate(leaderboard, 1):
        print(f"{i}. {config:<28} ${value:>10,.2f} ${pnl:>+10,.2f} {pnl_pct:>+8.2f}%")

    print(f"\n  WINNER: {leaderboard[0][0]} with ${leaderboard[0][2]:+,.2f} ({leaderboard[0][3]:+.2f}%)")


def main():
    """Run scheduler continuously, triggering every hour."""
    load_dotenv()

    # Get symbol from command line or use default
    symbol = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SYMBOL
    INTERVAL_SECONDS = 60 * 60  # 1 hour

    def signal_handler(sig, frame):
        print("\n\nScheduler stopped by user.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 60)
    print("  AI TRADING SIMULATION SCHEDULER")
    print(f"  Symbol: {symbol} | 6 Configs | $10,000 Each | Hourly")
    print("=" * 60)
    print(f"\nInterval: Every {INTERVAL_SECONDS // 60} minutes")
    print("Press Ctrl+C to stop\n")

    run_count = 0
    while True:
        run_count += 1
        print(f"\n{'#'*60}")
        print(f"  RUN #{run_count}")
        print(f"{'#'*60}")

        try:
            run_once(symbol)
        except Exception as e:
            print(f"Error during run: {e}")

        # Calculate next run time
        next_run = datetime.now().replace(microsecond=0) + timedelta(seconds=INTERVAL_SECONDS)
        print(f"\nNext run at: {next_run.isoformat()}")
        print(f"Sleeping for {INTERVAL_SECONDS // 60} minutes...")

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
```

### Step 5.4: Update .gitignore

Add:

```gitignore
python/.results/
```

### Step 5.5: Usage

**Interactive mode (single run):**

```bash
cd python
uv run python -m src.examples.main
```

**Continuous scheduler (runs every hour):**

```bash
cd python
uv run python -m src.scheduler
```

This will:

1. Run immediately on startup
2. Print leaderboard after each run
3. Sleep for 1 hour
4. Repeat indefinitely
5. Press `Ctrl+C` to stop

**Example output:**

```
============================================================
  AI TRADING SIMULATION SCHEDULER
  6 Configurations | $10,000 Each | Hourly Updates
============================================================

Interval: Every 60 minutes
Press Ctrl+C to stop

############################################################
  RUN #1
############################################################

============================================================
  Trading Simulation Run: 2025-01-15T14:00:00
  Starting Capital per Config: $10,000
============================================================

BTC Price: $98,500.00

[llama3.1-8b] (basic) - Portfolio: $10,000.00
  -> BUY | opened_position
[llama3.1-8b] (membit) - Portfolio: $10,000.00
  -> DO_NOTHING | no_change | 1 tools
...

============================================================
  LEADERBOARD
============================================================
Config                         Value        P&L          Return
----------------------------------------------------------------
1. llama-3.3-70b (membit)      $10,250.00   $+250.00     +2.50%
2. qwen-3-32b (membit)         $10,150.00   $+150.00     +1.50%
3. llama3.1-8b (basic)         $10,100.00   $+100.00     +1.00%
4. llama3.1-8b (membit)        $10,000.00   $+0.00       +0.00%
5. llama-3.3-70b (basic)       $9,950.00    $-50.00      -0.50%
6. qwen-3-32b (basic)          $9,900.00    $-100.00     -1.00%

  WINNER: llama-3.3-70b (membit) with $+250.00 (+2.50%)

Next run at: 2025-01-15T15:00:00
Sleeping for 60 minutes...
```

**Run in background (optional):**

```bash
cd python
nohup uv run python -m src.scheduler > scheduler.log 2>&1 &
```

---

## Implementation Checklist

- [x] **Phase 1: Restructure**

  - [x] Create `node/` directory
  - [x] Move existing Node.js files to `node/`
  - [x] Update `.gitignore` for monorepo
  - [x] Test Node.js project still works from new location

- [x] **Phase 2: Python Setup**

  - [x] Create `python/` directory structure
  - [x] Create `pyproject.toml`
  - [x] Implement `types.py`
  - [x] Implement `cerebras_client.py`
  - [x] Implement `membit_client.py` (corrected API usage)
  - [x] Implement `price_client.py` (with symbol support)
  - [x] Implement `indicators_client.py`
  - [x] Implement `state_manager.py` (with Portfolio dataclass)
  - [x] Create `__init__.py` files

- [x] **Phase 3: Data Clients & Exchange MCP**

  - [x] Implement `price_client.py` with `fetch_price(symbol)` for any asset
  - [x] Implement `indicators_client.py` with symbol support
  - [x] Implement `state_manager.py` with `Portfolio` and flexible `Position`
  - [x] Implement `exchange_mcp.py` with MCP-style tools:
    - [x] `get_portfolio` - Get portfolio status
    - [x] `buy` - Buy with specified USD amount (flexible sizing)
    - [x] `sell` - Sell specified asset amount (flexible sizing)
    - [x] `hold` - Do nothing (keep position unchanged)
  - [ ] Test Exchange MCP tools

- [x] **Phase 4: Documentation**

  - [x] Create `python/README.md`
  - [x] Create `.env.example` files
  - [x] Create root `README.md`
  - [ ] Update `CLAUDE.md` for monorepo structure

- [x] **Phase 5: Agent & Scheduler**
  - [x] Create `agent.py` with `TradingAgent` class
    - [x] Exchange MCP tools (buy/sell/hold with flexible amounts)
    - [x] Membit MCP tools (optional news/sentiment)
    - [x] Symbol-agnostic design
  - [x] Update `main.py` to use `TradingAgent`
    - [x] Interactive model/symbol/membit selection
    - [x] Display executed trades and tool calls
  - [x] Create `scheduler.py` with built-in hourly loop
    - [x] Symbol configurable via command line
    - [x] Leaderboard after each run
  - [x] Update `.gitignore` to exclude `.results/`
  - [ ] Run comparison over multiple days

---

## References

- [Cerebras Cloud SDK (Python)](https://github.com/Cerebras/cerebras-cloud-sdk-python)
- [Cerebras Inference Docs](https://inference-docs.cerebras.ai/integrations)
- [Membit Python SDK](https://github.com/bandprotocol/membit-python)
- [Band Protocol Price API](https://laozi3.bandchain.org/api/feeds/v1beta1/all_prices)
- [Twelve Data API](https://twelvedata.com/docs)
