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
from typing import Dict, Any, Optional, List
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

    TRADING_FEE_RATE: float = 0.0010  # 0.10% flat fee on all trades

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
            "total_fees_paid": round(portfolio.total_fees_paid, 2),
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
                        Must be > 0 and <= available cash (after 0.10% fee).
            symbol: Asset symbol to buy (default: configured symbol)

        Returns:
            TradeResult with success status and details.
        """
        symbol = symbol or self.default_symbol
        portfolio = load_portfolio(self.state_file)
        current_price = self.get_price(symbol)

        # Calculate fee
        fee = usd_amount * self.TRADING_FEE_RATE
        total_cost = usd_amount + fee

        # Validation
        if usd_amount <= 0:
            return TradeResult(
                success=False,
                action="buy",
                message="USD amount must be greater than 0.",
            )

        if total_cost > portfolio.current_capital:
            return TradeResult(
                success=False,
                action="buy",
                message=f"Insufficient funds. Available: ${portfolio.current_capital:,.2f}, Required (incl. 0.10% fee): ${total_cost:,.2f}",
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

        # Deduct cash (usd_amount + fee)
        portfolio.current_capital -= total_cost

        # Track fee
        portfolio.total_fees_paid += fee

        # Record trade
        portfolio.trade_history.append({
            "type": "buy",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "usd_amount": usd_amount,
            "asset_amount": asset_to_buy,
            "price": current_price,
            "fee": fee,
        })

        save_portfolio(portfolio, self.state_file)

        return TradeResult(
            success=True,
            action="buy",
            message=f"Bought {asset_to_buy:.8f} {symbol} for ${usd_amount:,.2f} at ${current_price:,.2f} (fee: ${fee:.2f})",
            details={
                "symbol": symbol,
                "asset_bought": round(asset_to_buy, 8),
                "usd_spent": round(usd_amount, 2),
                "fee": round(fee, 2),
                "total_cost": round(total_cost, 2),
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
                          A 0.10% fee is deducted from proceeds.
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
                message="No position to sell.",
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

        # Calculate sale proceeds and fee
        gross_proceeds = asset_amount * current_price
        fee = gross_proceeds * self.TRADING_FEE_RATE
        net_proceeds = gross_proceeds - fee

        # Calculate P&L for this portion (based on gross proceeds before fee)
        portion_ratio = asset_amount / portfolio.position.asset_amount
        portion_cost = portfolio.position.capital_used * portion_ratio
        pnl = gross_proceeds - portion_cost
        pnl_percent = (pnl / portion_cost) * 100 if portion_cost > 0 else 0

        # Update position
        portfolio.position.asset_amount -= asset_amount
        portfolio.position.capital_used -= portion_cost

        # Add net proceeds to cash (after fee)
        portfolio.current_capital += net_proceeds

        # Track fee
        portfolio.total_fees_paid += fee

        # Update realized P&L
        portfolio.total_realized_pnl += pnl

        # Record trade
        portfolio.trade_history.append({
            "type": "sell",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "asset_amount": asset_amount,
            "gross_proceeds": gross_proceeds,
            "fee": fee,
            "usd_received": net_proceeds,
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
            message=f"Sold {asset_amount:.8f} {symbol} for ${net_proceeds:,.2f} at ${current_price:,.2f} (fee: ${fee:.2f}). P&L: ${pnl:+,.2f} ({pnl_percent:+.2f}%)",
            details={
                "symbol": symbol,
                "asset_sold": round(asset_amount, 8),
                "gross_proceeds": round(gross_proceeds, 2),
                "fee": round(fee, 2),
                "usd_received": round(net_proceeds, 2),
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

def get_exchange_tools(symbol: str = "BTC") -> List[Dict[str, Any]]:
    """
    Get MCP tool definitions for the exchange.
    Symbol is used in descriptions for clarity.

    Note: get_portfolio and hold are removed:
    - Portfolio data is pre-injected into the system prompt
    - Hold is implicit: if no tool is called, position is held
    """
    return [
        {
            "name": "buy",
            "description": f"Buy {symbol} with a specified USD amount. A 0.10% fee is charged on top of the purchase amount. You decide how much to spend based on your analysis and risk tolerance. You don't have to use all your cash.",
            "parameters": {
                "type": "object",
                "properties": {
                    "usd_amount": {
                        "type": "number",
                        "description": "Amount of USD to spend (0.10% fee charged on top). Must be > 0 and total cost <= available cash."
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
            "description": f"Sell a specified amount of {symbol}. A 0.10% fee is deducted from the sale proceeds. You decide how much to sell based on your analysis. You don't have to sell your entire position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_amount": {
                        "type": "number",
                        "description": "Amount of asset to sell (0.10% fee deducted from proceeds). Must be > 0 and <= current holdings."
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
    ]
