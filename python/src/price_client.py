"""
Price data client using Band Protocol price feeds.
https://laozi3.bandchain.org/api/feeds/v1beta1/all_prices
Free API, no authentication required.

Includes PriceContext singleton for sharing price data across modules.
"""

import requests
from datetime import datetime
from typing import Any, Optional, Dict

BAND_PROTOCOL_API_URL = "https://laozi3.bandchain.org/api/feeds/v1beta1/all_prices"


class PriceContext:
    """
    Singleton for managing price data across a single decision cycle.

    Fetches prices from Band Protocol and stores them for use by:
    - System prompt (market data for AI)
    - ExchangeMCP (trade calculations)

    This ensures price consistency within a cycle while staying fresh between cycles.

    Usage:
        ctx = PriceContext.get_instance()
        ctx.fetch(symbol)           # Fetch and store price
        ctx.get_price(symbol)       # Get stored price
        ctx.format_for_prompt()     # Format for AI prompt
    """

    _instance: Optional["PriceContext"] = None

    def __init__(self):
        self._prices: Dict[str, float] = {}
        self._timestamps: Dict[str, str] = {}
        self._raw: Dict[str, Any] = {}

    @classmethod
    def get_instance(cls) -> "PriceContext":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def fetch(self, symbol: str) -> float:
        """
        Fetch price for a symbol from Band Protocol and store it.
        Returns the price.
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

        # Store in context
        self._prices[symbol] = price
        self._timestamps[symbol] = datetime.now().isoformat()
        self._raw[symbol] = symbol_data

        return price

    def get_price(self, symbol: str) -> float:
        """Get stored price for a symbol. Must call fetch() first."""
        if symbol not in self._prices:
            raise ValueError(f"Price for {symbol} not fetched. Call fetch() first.")
        return self._prices[symbol]

    def has_price(self, symbol: str) -> bool:
        """Check if price is available for symbol."""
        return symbol in self._prices

    def format_for_prompt(self, symbol: str) -> str:
        """Format price as context for AI prompt."""
        price = self.get_price(symbol)
        return f"Current {symbol} Price: ${price:,.2f}"

    def clear(self) -> None:
        """Clear all stored prices (call at end of decision cycle)."""
        self._prices.clear()
        self._timestamps.clear()
        self._raw.clear()


# Convenience functions


def fetch_price(symbol: str = "BTC") -> float:
    """Fetch price and store in global context. Returns the price."""
    ctx = PriceContext.get_instance()
    return ctx.fetch(symbol)


def get_price(symbol: str) -> float:
    """Get price from global context. Must call fetch_price() first."""
    ctx = PriceContext.get_instance()
    return ctx.get_price(symbol)


def format_price_context(symbol: str) -> str:
    """Format price from global context for AI prompt."""
    ctx = PriceContext.get_instance()
    return ctx.format_for_prompt(symbol)
