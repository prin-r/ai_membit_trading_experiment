# Logging System Improvements Plan

## Overview

Add a `--verbose` / `-v` CLI flag to control log output across the trading agent system. When disabled (default), the agent runs without printing debug/progress information.

---

## Current State

Logs are scattered across files using `print()` statements:

| File | Log Types |
|------|-----------|
| `agent.py` | Tool call notifications (`[Tool] get_portfolio(...)`) |
| `membit_client.py` | Raw API responses, result counts (`[Membit] cluster_search(...)`) |
| `scheduler.py` | Run headers, portfolio values, action summaries, leaderboard |
| `examples/*.py` | User-facing interactive output |

---

## Requirements

1. **Add a `--verbose` CLI flag** to control whether logs are printed
2. **Include Membit's response** in verbose output (already present, just needs flag control)

---

## CLI Usage

```bash
# Normal mode (quiet agent internals)
uv run python -m src.scheduler BTC

# Verbose mode (show tool calls, Membit responses)
uv run python -m src.scheduler BTC --verbose
uv run python -m src.scheduler BTC -v
```

---

## Implementation Plan

### 1. Update CLI Argument Parsing in Scheduler

**File:** `python/src/scheduler.py`

Replace manual `sys.argv` parsing with `argparse`:

```python
import argparse

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="AI Trading Simulation Scheduler")
    parser.add_argument("symbol", nargs="?", default=DEFAULT_SYMBOL, help="Trading symbol (default: BTC)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging for tool calls and Membit responses")
    args = parser.parse_args()

    symbol = args.symbol
    verbose = args.verbose
    # ... rest of main()
```

---

### 2. Pass `verbose` Through the Call Chain

**File:** `python/src/scheduler.py`

Update `run_once()` and `run_single_agent()` to accept and pass `verbose`:

```python
def run_single_agent(
    model: str,
    symbol: str,
    use_membit: bool,
    market_context: str,
    verbose: bool = False,  # NEW
) -> Dict[str, Any]:
    agent = TradingAgent(
        state_file=state_file,
        symbol=symbol,
        use_membit=use_membit,
        verbose=verbose,  # Pass through
    )

def run_once(symbol: str = "BTC", verbose: bool = False):  # NEW param
    # ... pass verbose to run_single_agent calls
```

---

### 3. Add `verbose` Parameter to `TradingAgent`

**File:** `python/src/agent.py`

```python
class TradingAgent:
    def __init__(
        self,
        state_file: str,
        symbol: str = "BTC",
        use_membit: bool = False,
        verbose: bool = False,  # NEW (default False)
    ):
        self.verbose = verbose
        # ...
        self.membit = MembitWrapper(verbose=self.verbose) if use_membit else None
```

Update print statements to check `self.verbose` and include response data:

```python
# Line ~292 - get_portfolio with response
if self.verbose:
    print(f"    [Tool] get_portfolio({{\"symbol\": \"{self.symbol}\"}})")
portfolio_result = self.execute_tool(portfolio_call)
if self.verbose:
    print(f"    [Tool] get_portfolio -> {portfolio_result.result}")

# Line ~329 - other tool calls with response
if self.verbose:
    print(f"    [Tool] {tc.name}({json.dumps(tc.arguments)})")
result = self.execute_tool(tc)
if self.verbose:
    if result.error:
        print(f"    [Tool] {tc.name} -> ERROR: {result.error}")
    else:
        print(f"    [Tool] {tc.name} -> {result.result}")
```

**Verbose output example:**
```
    [Tool] get_portfolio({"symbol": "BTC"})
    [Tool] get_portfolio -> {
      "available_cash": 8500.00,
      "holdings": {"BTC": 0.015},
      "total_value": 10234.50,
      ...
    }
    [Tool] buy({"usd_amount": 500, "symbol": "BTC"})
    [Tool] buy -> Bought 0.0053 BTC for $500.00 (fee: $0.50)
```

---

### 4. Add `verbose` Parameter to `MembitWrapper`

**File:** `python/src/membit_client.py`

```python
class MembitWrapper:
    def __init__(self, api_key: Optional[str] = None, verbose: bool = False):
        self.verbose = verbose
        # ...

    def search_clusters(self, query: str, limit: int = 5) -> List[Any]:
        response = self.client.cluster_search(query, limit=limit)
        if self.verbose:
            print(f"    [Membit] cluster_search('{query}') raw response: {response}")
        # ...
        if self.verbose:
            print(f"    [Membit] Found {len(clusters)} clusters")
        return clusters
```

Apply same pattern to:
- `search_posts()` (lines 44, 48)
- `get_cluster_info()` (line 55)

---

## Files to Modify

| File | Changes |
|------|---------|
| `python/src/scheduler.py` | Add argparse, pass `verbose` through call chain |
| `python/src/agent.py` | Add `verbose` param, wrap 2 print statements, pass to MembitWrapper |
| `python/src/membit_client.py` | Add `verbose` param, wrap 3 print statements |

---

## Notes

- Scheduler's own output (headers, leaderboard, summaries) remains always-on
- Only agent internals (tool calls, Membit responses) are controlled by `--verbose`
- Default is quiet mode (`verbose=False`) for cleaner output
- Examples (`examples/*.py`) are interactive and keep their output as-is
