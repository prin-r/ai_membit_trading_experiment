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
    action: str  # "buy"
    price: float  # Entry price per unit
    timestamp: str  # ISO format timestamp
    symbol: str = "BTC"  # Asset symbol (e.g., "BTC", "ETH")
    asset_amount: float = 0.0  # How much asset was bought
    capital_used: float = 0.0  # How much USD was spent


@dataclass
class Portfolio:
    starting_capital: float = STARTING_CAPITAL
    current_capital: float = STARTING_CAPITAL
    position: Optional[Position] = None
    trade_history: List[Dict[str, Any]] = field(default_factory=list)
    total_realized_pnl: float = 0.0
    total_fees_paid: float = 0.0


def get_state_dir() -> str:
    """Get the path to the states directory (in python/ directory)."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), STATE_DIR)


def get_state_file_path(state_file: str = DEFAULT_STATE_FILE) -> str:
    """Get the path to the state file (in python/.states/ directory)."""
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
                total_fees_paid=data.get("total_fees_paid", 0.0),
            )
    except (json.JSONDecodeError, KeyError, TypeError):
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
        "total_fees_paid": portfolio.total_fees_paid,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_portfolio_value(portfolio: Portfolio, current_price: float) -> float:
    """Calculate current portfolio value."""
    if portfolio.position:
        position_value = portfolio.position.asset_amount * current_price
        return portfolio.current_capital + position_value
    return portfolio.current_capital


def format_portfolio_context(portfolio: Portfolio, current_price: float) -> str:
    """Format portfolio status for AI prompt."""
    portfolio_value = get_portfolio_value(portfolio, current_price)
    total_pnl = portfolio_value - portfolio.starting_capital
    pnl_percent = (total_pnl / portfolio.starting_capital) * 100
    pnl_sign = "+" if total_pnl >= 0 else ""

    if portfolio.position:
        unrealized_pnl = (
            current_price - portfolio.position.price
        ) * portfolio.position.asset_amount
        unrealized_sign = "+" if unrealized_pnl >= 0 else ""
        position_status = f"""OPEN POSITION:
- {portfolio.position.symbol} Holdings: {portfolio.position.asset_amount:.6f} {portfolio.position.symbol}
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
- Total Fees Paid: ${portfolio.total_fees_paid:,.2f}
- Trades Completed: {len(portfolio.trade_history)}

{position_status}

GOAL: Maximize P&L through smart trading decisions."""


# Legacy functions for backward compatibility
def load_position(state_file: str = DEFAULT_STATE_FILE) -> Optional[Position]:
    """Load current position from persistent state (legacy)."""
    portfolio = load_portfolio(state_file)
    return portfolio.position


def save_position(position: Position, state_file: str = DEFAULT_STATE_FILE) -> None:
    """Save position to persistent state (legacy)."""
    portfolio = load_portfolio(state_file)
    portfolio.position = position
    save_portfolio(portfolio, state_file)


def clear_position(state_file: str = DEFAULT_STATE_FILE) -> None:
    """Clear the current position (legacy)."""
    portfolio = load_portfolio(state_file)
    portfolio.position = None
    save_portfolio(portfolio, state_file)


def format_position_context(position: Optional[Position], current_price: float) -> str:
    """Format current position as context for AI prompt (legacy)."""
    if position is None:
        return "CURRENT POSITION: None (no open position)"

    pnl = current_price - position.price
    pnl_percent = (pnl / position.price) * 100
    pnl_sign = "+" if pnl >= 0 else ""

    return f"""CURRENT POSITION:
- Status: LONG (bought)
- Entry Price: ${position.price:,.2f}
- Entry Time: {position.timestamp}
- Current P&L: {pnl_sign}${pnl:,.2f} ({pnl_sign}{pnl_percent:.2f}%)"""
