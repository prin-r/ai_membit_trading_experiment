# TradingAgent Improvement Plan

## Comparison: Your Agent vs. Reference (nof1.ai-alpha-arena)

This document outlines improvements to align with and exceed the reference implementation.

---

## 1. System Prompt Improvements

### Current State

Your system prompt is basic:

```
You are an AI trading agent managing a portfolio.
Your goal is to maximize profit by making smart trading decisions.
```

### Reference Approach

The reference uses a highly detailed, structured system prompt with:

- **Role definition**: "rigorous QUANTITATIVE TRADER and interdisciplinary MATHEMATICIAN-ENGINEER"
- **Core policies**: Low-churn, position-aware, hysteresis rules
- **Decision discipline**: Clear action enumeration (buy/sell/hold)
- **Output contract**: Strict JSON schema enforcement

### Recommended Improvements

```python
SYSTEM_PROMPT = """You are a rigorous QUANTITATIVE TRADER optimizing risk-adjusted returns.

CONTEXT:
- Asset: {symbol}
- Current time: {timestamp}

CORE POLICIES (minimize churn, maximize edge):

1) RESPECT PRIOR PLANS: If an active trade has an exit_plan with explicit invalidation,
   DO NOT close or flip early unless that invalidation has occurred.

2) HYSTERESIS: Require stronger evidence to CHANGE a decision than to keep it.
   - Only flip direction if BOTH conditions met:
     a) Higher-timeframe structure supports the new direction
     b) Intraday structure confirms with decisive break + momentum alignment
   - Otherwise, prefer HOLD or adjust TP/SL.

3) COOLDOWN: After opening/adding/reducing/flipping, impose self-cooldown of at least
   3 bars before another direction change, unless hard invalidation occurs.

4) OVERBOUGHT/OVERSOLD ≠ REVERSAL: Treat RSI extremes as risk-of-pullback only.
   Need structure + momentum confirmation to bet against trend.

5) PREFER ADJUSTMENTS OVER EXITS: If thesis weakens but not invalidated:
   - First consider: tighten stop, trail TP, or reduce size
   - Flip only on hard invalidation + fresh confluence

DECISION RULES (per asset):
- Choose one: BUY / SELL / HOLD
- You control allocation_usd (scale based on conviction)
- TP/SL sanity:
  • BUY: tp_price > current_price, sl_price < current_price
  • SELL: tp_price < current_price, sl_price > current_price

REASONING RECIPE (first principles):
1. Structure: trend, EMAs slope/cross, HH/HL vs LH/LL
2. Momentum: MACD regime, RSI slope
3. Liquidity/volatility: ATR, volume
4. Sentiment: news/social signals (if available)

OUTPUT CONTRACT:
Return a JSON object with:
{
  "reasoning": "detailed step-by-step analysis",
  "action": "buy" | "sell" | "hold",
  "allocation_usd": <number>,
  "tp_price": <number | null>,
  "sl_price": <number | null>,
  "exit_plan": "<invalidation trigger and conditions>",
  "rationale": "<1-2 sentence summary>"
}
"""
```

---

## 2. Structured Output Enforcement

### Decision: SKIP

**Rationale:** The current regex parsing works well in practice:

- No parsing failures observed in trading logs
- Cerebras models consistently follow the `TOOL_CALL: {...}` format
- Tool arguments are simple (2 levels deep), within regex capabilities
- Structured output support in Cerebras API is unverified

**Current State (Working Fine):**

- Uses regex parsing: `TOOL_CALL: {...}`
- Silent failure mode exists but hasn't caused issues
- Models cooperate with format instructions

**Optional Future Enhancement:**

- Add debug logging to detect any parsing failures
- Revisit if Cerebras confirms `response_format` support
- Consider if adding complex parameters (TP/SL, exit plans) causes issues

~~### Reference Approach~~
~~- Uses OpenAI-compatible `response_format` with strict JSON schema~~
~~- Fallback sanitizer model for malformed outputs~~
~~- Multiple retry attempts with graceful degradation~~

~~### Recommended Improvements~~

```python
# Add response schema definition
TRADE_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string"},
        "action": {"type": "string", "enum": ["buy", "sell", "hold"]},
        "allocation_usd": {"type": "number", "minimum": 0},
        "tp_price": {"type": ["number", "null"]},
        "sl_price": {"type": ["number", "null"]},
        "exit_plan": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["reasoning", "action", "allocation_usd", "rationale"],
    "additionalProperties": False,
}

# Add sanitizer for fallback parsing
def sanitize_output(raw_content: str, fallback_model: str = "llama-3.3-70b") -> dict:
    """Use a secondary model to normalize malformed LLM output."""
    # ... implementation
```

---

## 3. Technical Indicators Integration

### Current State

- Exchange tools: get_portfolio, buy, sell, hold
- Membit tools: search_posts, search_clusters, get_cluster_info
- Indicators (SMA, MACD, BBands, RSI) fetched via TwelveData API in `indicators_client.py`
- Indicators are passed to agent via `market_context` in the system prompt

### Decision: Keep Current Approach (No MCP Conversion)

**Rationale:** Converting indicators to MCP tools is unnecessary because:

1. We don't have much control over when/how the agent fetches indicators
2. Fetching all indicators upfront and including in system prompt is simpler and more reliable
3. Avoids extra API calls during agent reasoning rounds
4. Reduces latency and potential errors from dynamic fetching

**Current Implementation:**

- `indicators_client.py` fetches indicators from TwelveData API
- `format_indicators_context()` formats them as readable text
- Scheduler calls `fetch_all_indicators()` once at start
- Formatted indicators passed to `agent.run(market_context=...)`
- Agent sees all indicator data in system prompt for immediate analysis

### Missing Indicators to Add

Based on the reference system prompt's "REASONING RECIPE", we need to add:

| Indicator | Purpose                      | TwelveData Endpoint | Parameters                            |
| --------- | ---------------------------- | ------------------- | ------------------------------------- |
| **EMA**   | Trend (slope/cross analysis) | `/ema`              | time_period=9, 21 (short/medium term) |
| **ATR**   | Volatility/Liquidity         | `/atr`              | time_period=14                        |

**Implementation Plan:**

```python
# Add to indicators_client.py:

@dataclass
class EMAData:
    value: float
    timestamp: str
    raw: Any = None

@dataclass
class ATRData:
    value: float
    timestamp: str
    raw: Any = None

def fetch_ema(symbol: str = "BTC/USD", interval: str = "1day", time_period: int = 21) -> EMAData:
    """Fetch Exponential Moving Average (EMA) - Trend indicator with more weight on recent prices."""
    api_key = get_env("TWELVE_DATA_API_KEY")
    response = requests.get(
        f"{TWELVE_DATA_BASE_URL}/ema",
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
        raise ValueError(f"EMA data not available: {data.get('message', 'Unknown error')}")
    latest = data["values"][0]
    return EMAData(value=float(latest["ema"]), timestamp=latest["datetime"], raw=data)

def fetch_atr(symbol: str = "BTC/USD", interval: str = "1day", time_period: int = 14) -> ATRData:
    """Fetch Average True Range (ATR) - Volatility indicator."""
    api_key = get_env("TWELVE_DATA_API_KEY")
    response = requests.get(
        f"{TWELVE_DATA_BASE_URL}/atr",
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
        raise ValueError(f"ATR data not available: {data.get('message', 'Unknown error')}")
    latest = data["values"][0]
    return ATRData(value=float(latest["atr"]), timestamp=latest["datetime"], raw=data)

# Update TechnicalIndicators dataclass:
@dataclass
class TechnicalIndicators:
    sma_200: Optional[SMAData] = None
    ema_9: Optional[EMAData] = None   # NEW
    ema_21: Optional[EMAData] = None  # NEW
    macd: Optional[MACDData] = None
    bbands: Optional[BollingerBandsData] = None
    rsi: Optional[RSIData] = None
    atr: Optional[ATRData] = None     # NEW
    current_price: Optional[float] = None

# Update fetch_all_indicators():
def fetch_all_indicators(symbol: str = "BTC/USD", interval: str = "1day") -> TechnicalIndicators:
    return TechnicalIndicators(
        sma_200=fetch_sma(symbol, interval, time_period=200),
        ema_9=fetch_ema(symbol, interval, time_period=9),
        ema_21=fetch_ema(symbol, interval, time_period=21),
        macd=fetch_macd(symbol, interval),
        bbands=fetch_bbands(symbol, interval),
        rsi=fetch_rsi(symbol, interval),
        atr=fetch_atr(symbol, interval),
    )

# Update format_indicators_context():
def format_indicators_context(indicators: TechnicalIndicators, current_price: float) -> str:
    lines = ["TECHNICAL INDICATORS:"]
    if indicators.sma_200:
        lines.append(f"1. SMA(200): ${indicators.sma_200.value:,.2f}")
    if indicators.ema_9:
        lines.append(f"2. EMA(9): ${indicators.ema_9.value:,.2f}")
    if indicators.ema_21:
        lines.append(f"3. EMA(21): ${indicators.ema_21.value:,.2f}")
    if indicators.macd:
        lines.append(f"4. MACD(12,26,9): MACD={indicators.macd.macd:.2f}, Signal={indicators.macd.macd_signal:.2f}, Histogram={indicators.macd.macd_hist:.2f}")
    if indicators.bbands:
        lines.append(f"5. Bollinger Bands(20,2): Upper=${indicators.bbands.upper_band:,.2f}, Middle=${indicators.bbands.middle_band:,.2f}, Lower=${indicators.bbands.lower_band:,.2f}")
    if indicators.rsi:
        lines.append(f"6. RSI(14): {indicators.rsi.value:.1f}")
    if indicators.atr:
        lines.append(f"7. ATR(14): ${indicators.atr.value:,.2f}")
    return "\n".join(lines)
```

**Note:** This adds 3 more API calls per run (EMA x2 + ATR). TwelveData free tier allows 800 calls/day, so with 6 model configs running hourly, this should still be within limits (6 configs × 24 hours × 7 indicators = 1,008 calls/day - may need to optimize or upgrade plan).

---

## 4. Multi-Asset Support (SKIP FOR NOW)

### Current State

- Single asset per agent instance (`symbol: str = "BTC"`)

### Reference Approach

- Handles multiple assets in a single call: `decide_trade(assets, context)`
- Returns array of decisions, one per asset
- Allows correlation analysis across assets

### Recommended Improvements

```python
def run(
    self,
    model: str,
    assets: List[str],  # Multiple assets
    market_context: Dict[str, str],  # Per-asset context
    max_tool_rounds: int = 3,
) -> Dict[str, Any]:
    """Run trading decisions for multiple assets."""
    # Return: {"reasoning": str, "trade_decisions": List[dict]}
```

---

## 5. Exit Plan & Trade State Tracking

### Decision: SKIP

**Rationale:** Not necessary for current hourly scheduler setup:
- Agent runs every hour and makes fresh decisions based on current conditions
- Can simply call `sell` when it wants to exit - no need for pre-set TP/SL
- No need to persist reasoning between runs
- Adds state management complexity without clear benefit for simulation

**When to reconsider:**
- Moving to real exchange with limit orders
- Less frequent runs (daily instead of hourly)
- Need to track *why* agent entered a trade

~~### Current State~~
~~- No exit plan tracking~~
~~- No position state between runs~~
~~- No TP/SL management~~

~~### Reference Approach~~
~~- `exit_plan` field with explicit invalidation triggers~~
~~- Cooldown tracking encoded in exit plan~~
~~- TP/SL price validation based on direction~~

### Recommended Improvements

```python
@dataclass
class TradeState:
    """Persistent trade state for position tracking."""
    symbol: str
    entry_price: float
    entry_time: str
    direction: str  # "long" | "short"
    size_usd: float
    tp_price: Optional[float]
    sl_price: Optional[float]
    exit_plan: str
    cooldown_until: Optional[str]

class TradingAgent:
    def __init__(self, ...):
        self.active_trades: Dict[str, TradeState] = {}

    def _format_active_trades(self) -> str:
        """Format active trades for LLM context."""
        ...
```

---

## 6. Reasoning/Chain-of-Thought Support

### Current State

- Single response, no explicit reasoning extraction

### Reference Approach

- Explicit `reasoning` field in output
- Optional `reasoning` parameter in API call for models that support it
- Configurable reasoning effort level

### Recommended Improvements

```python
# Add reasoning support in call options
if config.get("reasoning_enabled"):
    request_data["reasoning"] = {
        "enabled": True,
        "effort": config.get("reasoning_effort", "medium"),
    }

# Extract and log reasoning separately
result = {
    "reasoning": parsed.get("reasoning", ""),
    "decision": parsed.get("action"),
    "confidence": extract_confidence(parsed.get("reasoning")),
}
```

---

## 7. Error Handling & Retry Logic

### Current State

- Basic try/except in tool execution
- No retry logic

### Reference Approach

- 6 retry attempts for LLM calls
- Graceful degradation (disable tools → disable structured output)
- Fallback sanitizer model
- Detailed error logging to file

### Recommended Improvements

```python
MAX_RETRIES = 6

async def _call_with_retry(self, messages, tools=None, structured=True):
    """Call LLM with retry and fallback logic."""
    allow_tools = tools is not None
    allow_structured = structured

    for attempt in range(MAX_RETRIES):
        try:
            return await self._make_request(messages,
                tools=tools if allow_tools else None,
                structured=allow_structured)
        except ToolNotSupportedError:
            allow_tools = False
            continue
        except StructuredOutputError:
            allow_structured = False
            continue
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

---

## 8. Leverage Support (For Futures)

### Current State

- Spot trading only (buy/sell amounts)

### Reference Approach

- Perpetual futures with 3-10x leverage
- Leverage adjusted based on volatility/ATR
- Margin awareness in decisions

### Recommended Improvements

```python
# Add leverage to buy/sell tools
{
    "name": "open_position",
    "parameters": {
        "properties": {
            "direction": {"type": "string", "enum": ["long", "short"]},
            "size_usd": {"type": "number"},
            "leverage": {"type": "number", "minimum": 1, "maximum": 10},
            "tp_price": {"type": ["number", "null"]},
            "sl_price": {"type": ["number", "null"]},
        }
    }
}
```

---

## 9. Configuration System

### Current State

- Hardcoded values in constructor

### Reference Approach

- Centralized `CONFIG` object
- Environment-based configuration
- Model-specific settings (reasoning effort, provider config)

### Recommended Improvements

```python
# config.py
@dataclass
class AgentConfig:
    model: str = "llama-3.3-70b"
    max_tool_rounds: int = 3
    max_tokens: int = 2000
    reasoning_enabled: bool = False
    reasoning_effort: str = "medium"
    cooldown_bars: int = 3
    max_leverage: float = 5.0
    sanitize_model: str = "llama-3.3-70b"

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load config from environment variables."""
        ...
```

---

## 10. Logging & Observability

### Current State

- Print statements only

### Reference Approach

- Structured logging with levels
- Request/response logging to file
- Detailed error metadata

### Recommended Improvements

```python
import logging
from datetime import datetime

class TradingAgent:
    def __init__(self, ...):
        self.logger = logging.getLogger(f"TradingAgent.{symbol}")
        self.request_log = open("llm_requests.log", "a")

    def _log_request(self, payload, response):
        """Log LLM request/response for debugging."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": payload.get("model"),
            "tool_calls": len(response.get("tool_calls", [])),
            "tokens_used": response.get("usage", {}),
        }
        self.request_log.write(json.dumps(entry) + "\n")
```

---

## Implementation Priority

| Priority | Feature                           | Effort | Impact                                                     |
| -------- | --------------------------------- | ------ | ---------------------------------------------------------- |
| P0       | Add fee info to system prompt     | Low    | Medium                                                     |
| P0       | Add missing indicators (EMA, ATR) | Low    | Medium                                                     |
| P0       | System prompt overhaul            | Medium | High                                                       |
| P1       | Error handling + retries          | Low    | Medium                                                     |
| P1       | Configuration system              | Low    | Medium                                                     |
| P2       | Multi-asset support               | High   | Medium                                                     |
| P2       | Leverage support                  | Medium | Low                                                        |
| P2       | Reasoning extraction              | Low    | Low                                                        |
| --       | Exit plan tracking / TP/SL        | --     | -- (SKIP - agent runs hourly, can make fresh decisions)    |
| --       | Structured output + schema        | --     | -- (SKIP - current regex works fine)                       |
| --       | Technical indicators (MCP)        | --     | -- (Keep current approach)                                 |

---

## 11. Add Trading Fee Info to System Prompt

### Current State

- 0.10% trading fee is implemented in `exchange_mcp.py`
- Fee is mentioned in tool descriptions only
- Agent may not be aware of fee impact on trading decisions

### Recommended Change

Add explicit fee information to the system prompt so the agent can factor it into decisions:

```python
# In agent.py, add to system_prompt:
system_prompt = f"""You are an AI trading agent managing a portfolio.
Your goal is to maximize profit by making smart trading decisions.

{market_context}

TRADING FEES:
All trades are subject to a 0.10% fee:
- Buy: Fee is added on top of your purchase amount (total cost = amount + 0.10% fee)
- Sell: Fee is deducted from your sale proceeds (you receive = proceeds - 0.10% fee)
Factor this into your trading decisions, especially for small price movements.

{tool_prompt}
...
```

**Rationale:**

- Agent needs to understand that frequent small trades will erode profits
- Fee awareness encourages holding through minor fluctuations
- Helps agent calculate true breakeven price movements (need >0.20% move to profit after buy+sell fees)

---

## Quick Wins (Start Here)

1. ~~**Add fee info to system prompt**~~ ✅ DONE - help agent understand trading costs
2. ~~**Add missing indicators (EMA, ATR)**~~ ✅ DONE - complete technical analysis toolkit
3. ~~**Update system prompt**~~ ✅ DONE - with core policies (hysteresis, cooldown, exit plans)
4. ~~**Add TP/SL fields** to buy/sell actions~~ (SKIP - agent runs hourly, can decide to sell each run)
5. ~~**Add exit_plan** field to trade responses~~ (SKIP - no persistent reasoning between runs needed)
6. ~~**Add JSON output schema** validation~~ (SKIP - current regex works fine)

---

## Files to Modify

| File                             | Changes                                       |
| -------------------------------- | --------------------------------------------- |
| `python/src/agent.py`            | System prompt, structured output, retry logic |
| `python/src/exchange_mcp.py`     | Add TP/SL, leverage params to tools           |
| `python/src/types.py` (new)      | TradeState, AgentConfig dataclasses           |
| `python/src/indicators.py` (new) | Technical indicator tools                     |
| `python/src/config.py` (new)     | Centralized configuration                     |
