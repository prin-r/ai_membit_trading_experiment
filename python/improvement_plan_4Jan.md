# Improvement Plan: AI Trading Agent Optimization

**Date**: 2026-01-04
**Based on**: `trading_analysis_report.md`, `membit_blame_analysis.md`

---

## Overview

Three key improvements to enhance AI trading agent performance by reducing noise, simplifying decisions, and optimizing context usage.

---

## Improvement 1: Better Membit Query Strategy

### Problem

Models use generic queries that return non-actionable results:

```
search_clusters("crypto", limit=3)
→ Returns: "Financial Freedom and Crypto" (useless for trading)
```

### Solution

Provide a predefined set of effective search terms in the system prompt.

### Implementation

Add to system prompt:

```
## Membit Search Strategy

When searching for social sentiment, use these specific queries for actionable signals:

### For Posts (search_posts):
- "BTC breaking resistance today"
- "Bitcoin whale selling"
- "BTC pump signal"
- "Bitcoin dump warning"
- "BTC bullish breakout"
- "Bitcoin bearish reversal"
- "BTC trending prediction"
- "Bitcoin price target"

### For Clusters (search_clusters):
- "BTC technical breakout"
- "Bitcoin whale activity"
- "BTC price prediction"
- "Bitcoin market reversal"

DO NOT use generic queries like:
- ❌ "BTC market sentiment"
- ❌ "crypto"
- ❌ "BTC related"
- ❌ "Bitcoin news"

These return generic lifestyle/philosophy content with no trading signal.
```

### Expected Impact

| Metric                 | Before | After  |
| ---------------------- | ------ | ------ |
| Actionable posts       | ~40%   | ~80%   |
| Relevant clusters      | ~30%   | ~70%   |
| Clear sentiment signal | Rare   | Common |

---

## Improvement 2: Simplify to BUY/SELL Only

### Problem

Current 3-option system (BUY, SELL, HOLD) causes:

- Unnecessary tool calls for HOLD
- Decision paralysis → defaults to HOLD
- Wasted API tokens on no-action responses

**Evidence from log:**

```
[Tool] hold({"symbol": "BTC"})
[Tool] hold -> Holding position. No position. Cash: $10,000.00
```

This is a wasted tool call.

### Solution

Remove HOLD tool. If model decides neither BUY nor SELL, simply don't call any trade tool.

### Implementation

**Before (3 tools):**

```python
tools = [
    {"name": "buy", "description": "Buy asset"},
    {"name": "sell", "description": "Sell asset"},
    {"name": "hold", "description": "Hold current position"},  # REMOVE
]
```

**After (2 tools):**

```python
tools = [
    {"name": "buy", "description": "Buy asset"},
    {"name": "sell", "description": "Sell asset"},
]
```

**System prompt update:**

```
## Trading Actions

You have 2 trading tools available:
- buy: Purchase BTC with USD
- sell: Sell BTC for USD

If you decide to hold your current position, simply respond with your analysis
and reasoning. Do NOT call any tool - no action will be taken automatically.

Only call a tool when you have a clear directional conviction.
```

### Expected Impact

| Metric             | Before            | After             |
| ------------------ | ----------------- | ----------------- |
| Tool calls per run | 2-5               | 1-3               |
| HOLD tool calls    | ~40% of actions   | 0%                |
| Decision clarity   | Muddy (3 options) | Clear (2 options) |
| Token usage        | Higher            | Lower             |

---

## Improvement 3: Pre-inject Portfolio Data

### Problem

`get_portfolio` is called every single run, wasting a tool call:

```
[Tool] get_portfolio({"symbol": "BTC"})
[Tool] get_portfolio -> {
  "symbol": "BTC",
  "current_price": 90014.78,
  "portfolio_value": 10000.0,
  "available_cash": 10000.0,
  ...
}
```

The response is short and predictable. Every model calls this first.

### Solution

Fetch portfolio data programmatically and inject into system prompt.

### Implementation

**Before (tool-based):**

```python
tools = [
    {"name": "get_portfolio", "description": "Get current portfolio"},  # REMOVE
    {"name": "buy", ...},
    {"name": "sell", ...},
]

system_prompt = """
You are a trading agent. Use get_portfolio to check your holdings.
"""
```

**After (pre-injected):**

```python
# Fetch portfolio before calling LLM using existing Exchange logic
portfolio = self.exchange.tool_get_portfolio(symbol="BTC")

system_prompt = f"""
You are a trading agent.

## Current Portfolio Status
- Symbol: {portfolio['symbol']}
- Current Price: ${portfolio['current_price']:,.2f}
- Portfolio Value: ${portfolio['portfolio_value']:,.2f}
- Available Cash: ${portfolio['available_cash']:,.2f}
- Total P&L: ${portfolio['total_pnl']:+,.2f} ({portfolio['total_pnl_percent']:+.2f}%)
- Has Position: {portfolio['has_position']}
{f"- Position: {portfolio['position']['asset_amount']:.6f} BTC @ ${portfolio['position']['entry_price']:,.2f}" if portfolio['has_position'] else ""}

## Technical Indicators
- SMA(200): ${indicators['sma_200']:,.2f}
- RSI(14): {indicators['rsi']:.1f}
- MACD: {indicators['macd']:.2f} (Signal: {indicators['macd_signal']:.2f})
- Bollinger Bands: Upper=${indicators['bb_upper']:,.2f}, Lower=${indicators['bb_lower']:,.2f}

Make your trading decision based on the above data and social sentiment.
"""

tools = [
    {"name": "buy", ...},
    {"name": "sell", ...},
    # get_portfolio REMOVED - data is in prompt
]
```

### Expected Impact

| Metric              | Before             | After              |
| ------------------- | ------------------ | ------------------ |
| Tool calls per run  | 2-5                | 1-2                |
| get_portfolio calls | 100% of runs       | 0%                 |
| Context clarity     | Scattered          | Consolidated       |
| First-token latency | Slower (tool call) | Faster (immediate) |

---

## Summary: Before vs After

### Tool Configuration

| Tool              | Before | After     | Reason                          |
| ----------------- | ------ | --------- | ------------------------------- |
| `get_portfolio`   | ✅ Yes | ❌ Remove | Pre-inject into prompt          |
| `buy`             | ✅ Yes | ✅ Keep   | Core action                     |
| `sell`            | ✅ Yes | ✅ Keep   | Core action                     |
| `hold`            | ✅ Yes | ❌ Remove | No-op; just don't call anything |
| `search_posts`    | ✅ Yes | ✅ Keep   | With better query guidance      |
| `search_clusters` | ✅ Yes | ✅ Keep   | With better query guidance      |

### Prompt Changes

| Section              | Change                       |
| -------------------- | ---------------------------- |
| Portfolio data       | Add pre-fetched data block   |
| Technical indicators | Add pre-fetched data block   |
| Membit queries       | Add recommended search terms |
| Trading actions      | Clarify: no tool = hold      |

### Expected Overall Impact

| Metric                    | Before    | After     | Improvement      |
| ------------------------- | --------- | --------- | ---------------- |
| Tool calls per run        | 3-7       | 1-3       | ~50% reduction   |
| Actionable Membit results | ~40%      | ~80%      | 2x better signal |
| Decision clarity          | 3 options | 2 options | Simpler          |
| Wasted HOLD calls         | ~40%      | 0%        | Eliminated       |
| Token usage               | Higher    | Lower     | ~30% reduction   |

---

## Implementation Checklist

- [ ] **Improvement 1**: Create `src/prompts.py` with Membit constants
- [ ] **Improvement 1**: Update system prompt to use imported constants
- [ ] **Improvement 2**: Remove `hold` tool from tool list
- [ ] **Improvement 2**: Update prompt to explain no-tool = hold
- [ ] **Improvement 2**: Implement virtual HOLD return object in `agent.py`
- [ ] **Improvement 3**: Call `exchange.tool_get_portfolio()` before LLM call
- [ ] **Improvement 3**: Remove `get_portfolio` from tool list
- [ ] **Improvement 3**: Add portfolio data block to system prompt
- [ ] **Testing**: Run simulation with new configuration
- [ ] **Comparison**: Compare results vs baseline

---

## Code Sketch

```python
def run_trading_agent(symbol: str, model: str, membit_enabled: bool):
    # Improvement 3: Pre-fetch portfolio using Exchange tool logic
    # Reuse the tool logic to get the exact dict format expected by the prompt
    portfolio_data = self.exchange.tool_get_portfolio(symbol)
    indicators = get_technical_indicators(symbol)

    # Build system prompt with injected data
    # improvement 1: Helper function uses constants from prompts.py
    system_prompt = build_system_prompt(
        portfolio=portfolio_data,
        indicators=indicators,
        membit_enabled=membit_enabled
    )

    # Improvement 2: Only BUY/SELL tools
    tools = [
        {"name": "buy", "description": "Buy {symbol} with USD amount"},
        {"name": "sell", "description": "Sell {symbol} for USD"},
    ]

    # Improvement 1 & 3: Add Membit tools if enabled (no get_portfolio)
    if membit_enabled:
        tools.extend([
            {"name": "search_posts", "description": "Search social posts"},
            {"name": "search_clusters", "description": "Search topic clusters"},
        ])

    # Call LLM
    response = call_llm(
        model=model,
        system_prompt=system_prompt,
        tools=tools
    )

    # If no tool called = HOLD (Improvement 2)
    # If no tool called = HOLD (Improvement 2)
    if not response.tool_calls:
        # Return virtual HOLD result for scheduler compatibility
        return {
            "executed_action": {
                "action": "hold",
                "result": "Holding position (Virtual)"
            },
            # ... other fields
        }

    # Execute tool calls
    for tool_call in response.tool_calls:
        execute_tool(tool_call)
```

---

_Plan created based on analysis of trading_3_jan.log and team discussion_

---

## Technical Refinements (Added 4 Jan)

Based on technical review, the following implementation details will be adjusted:

### 1. Scheduler Compatibility (Virtual HOLD)

- **Issue**: `scheduler.py` expects a specific return format to log actions. If no tool is called, it might report "NONE" or error.
- **Refinement**: If the agent makes no tool calls, `TradingAgent.run()` will construct and return a "virtual" HOLD action object.
  - This ensures `scheduler.py` continues to report `HOLD` in the summary table without requiring an API round-trip.
  - Format: `{"action": "hold", "result": "Holding position..."}`

### 2. Prompt Management

- **Issue**: Embedding large prompt strings in `agent.py` clutters the logic.
- **Refinement**: Move `MEMBIT_SEARCH_STRATEGY` to a new file `src/prompts.py` and import it. This makes it easier to iterate on prompt engineering without touching agent code.

### 3. Efficient Portfolio Context

- **Issue**: Reusing the tool logic for the system prompt efficiently.
- **Refinement**: directly call `self.exchange.tool_get_portfolio()` within `agent.py` (python call, not LLM tool call) to fetch the data dictionary, then format it for the system prompt. This reuses the exact same robust logic used by the tool.
