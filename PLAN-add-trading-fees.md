# Plan: Add Trading Fees to Exchange MCP

## Overview

Add a flat 0.10% trading fee to the simulated exchange for all spot trades (buy and sell).

## Fee Structure

### Simple Flat Fee

- **Fee Rate**: 0.10% (10 basis points) on all trades
- **Applies to**: Both buy and sell orders equally
- **No maker/taker distinction**: All trades treated the same

### Fee Calculation

**Buy Order:**
```
fee = usd_amount * 0.001
total_cost = usd_amount + fee

Example: Buy $1000 of BTC
- Fee: $1.00
- Total deducted: $1001.00
```

**Sell Order:**
```
fee = (asset_amount * price) * 0.001
net_proceeds = gross_proceeds - fee

Example: Sell $1000 worth of BTC
- Fee: $1.00
- Net received: $999.00
```

## Implementation Steps

### Step 1: Add Fee Tracking to Portfolio

**File**: `python/src/state_manager.py`

```python
@dataclass
class Portfolio:
    # ... existing fields ...
    total_fees_paid: float = 0.0  # NEW
```

### Step 2: Add Fee Constant to ExchangeMCP

**File**: `python/src/exchange_mcp.py`

```python
class ExchangeMCP:
    TRADING_FEE_RATE: float = 0.0010  # 0.10%
```

### Step 3: Modify Buy Operation

**File**: `python/src/exchange_mcp.py` - `tool_buy()`

- Calculate `fee = usd_amount * 0.001`
- Validate `usd_amount + fee <= available_cash`
- Deduct `usd_amount + fee` from cash
- Track fee in `total_fees_paid` and trade history

### Step 4: Modify Sell Operation

**File**: `python/src/exchange_mcp.py` - `tool_sell()`

- Calculate `fee = gross_proceeds * 0.001`
- Credit `gross_proceeds - fee` to cash
- Track fee in `total_fees_paid` and trade history

### Step 5: Update Portfolio Display

**File**: `python/src/exchange_mcp.py` - `tool_get_portfolio()`

- Add `total_fees_paid` to response

### Step 6: Update Tool Descriptions

**File**: `python/src/exchange_mcp.py` - `get_exchange_tools()`

- Mention 0.10% fee in buy/sell descriptions

## Files to Modify

| File | Changes |
|------|---------|
| `python/src/state_manager.py` | Add `total_fees_paid` field |
| `python/src/exchange_mcp.py` | Add fee constant, modify buy/sell, update descriptions |

## Testing Checklist

- [ ] Buy deducts fee from cash
- [ ] Sell deducts fee from proceeds
- [ ] Fee accumulates in `total_fees_paid`
- [ ] Trade history records fees
- [ ] Existing state files work (default `total_fees_paid=0`)
