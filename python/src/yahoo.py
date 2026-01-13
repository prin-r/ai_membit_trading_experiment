"""
Price data client using yfinance for US Stocks.
Fetches real-time(ish) data from Yahoo Finance.
Free API, no authentication required.

Includes PriceContext singleton for sharing price data across modules.
"""

import yfinance as yf
from datetime import datetime
from typing import Any, Optional, Dict, List

# Top 10 US Stocks by Market Cap (approximate)
TOP_10_SYMBOLS = [
    "AAPL",
    "NVDA",
    "MSFT",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "BRK-B",
    "LLY",
    "AVGO",
]


class PriceContext:
    """
    Singleton for managing price data across a single decision cycle.

    Fetches prices from Yahoo Finance and stores them for use by:
    - System prompt (market data for AI)
    - Trading Logic (calculations)

    Usage:
        ctx = PriceContext.get_instance()
        ctx.fetch("AAPL")           # Fetch single
        ctx.fetch_all_top_10()      # Fetch all top 10 efficiently
        ctx.get_price("AAPL")       # Get stored price
        ctx.format_for_prompt("AAPL")
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
        Fetch price for a single symbol from yfinance and store it.
        Returns the price.
        """
        try:
            ticker = yf.Ticker(symbol)

            # fast_info is generally faster and more reliable for current price than .info
            # It avoids downloading the huge full metadata JSON.
            if hasattr(ticker, "fast_info"):
                price = ticker.fast_info["last_price"]
            else:
                # Fallback for older versions
                data = ticker.history(period="1d")
                if data.empty:
                    raise ValueError(f"No price data found for {symbol}")
                price = data["Close"].iloc[-1]

            # Store in context
            self._prices[symbol] = float(price)
            self._timestamps[symbol] = datetime.now().isoformat()
            self._raw[symbol] = {"source": "yfinance", "status": "ok"}

            return self._prices[symbol]

        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            raise ValueError(f"Could not fetch price for {symbol}")

    def fetch_all_top_10(self) -> Dict[str, float]:
        """
        Convenience method to fetch all Top 10 stocks.
        Uses a loop to be safe against API quirks, or could use yf.Tickers for bulk.
        """
        results = {}
        print(f"Fetching data for: {', '.join(TOP_10_SYMBOLS)}...")

        # We loop here to use the safe logic defined in fetch()
        for sym in TOP_10_SYMBOLS:
            try:
                price = self.fetch(sym)
                results[sym] = price
            except ValueError:
                continue
        return results

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
        try:
            price = self.get_price(symbol)
            return f"Current {symbol} Price: ${price:,.2f}"
        except ValueError:
            return f"Current {symbol} Price: [Unavailable]"

    def get_all_prices_formatted(self) -> str:
        """Returns a string block of all currently stored prices."""
        lines = []
        for sym, price in self._prices.items():
            lines.append(f"- {sym}: ${price:,.2f}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all stored prices (call at end of decision cycle)."""
        self._prices.clear()
        self._timestamps.clear()
        self._raw.clear()


# --- Convenience functions ---


def fetch_price(symbol: str) -> float:
    """Fetch price and store in global context. Returns the price."""
    ctx = PriceContext.get_instance()
    return ctx.fetch(symbol)


def fetch_top_10() -> Dict[str, float]:
    """Fetch all top 10 stocks into global context."""
    ctx = PriceContext.get_instance()
    return ctx.fetch_all_top_10()


def get_price(symbol: str) -> float:
    """Get price from global context. Must call fetch_price() first."""
    ctx = PriceContext.get_instance()
    return ctx.get_price(symbol)


def format_price_context(symbol: str) -> str:
    """Format price from global context for AI prompt."""
    ctx = PriceContext.get_instance()
    return ctx.format_for_prompt(symbol)


# --- Example Usage (if run directly) ---
if __name__ == "__main__":
    try:
        # 1. Initialize
        ctx = PriceContext.get_instance()

        # 2. Fetch all top 10 stocks
        fetch_top_10()

        # 3. Print formatted output (simulating AI Prompt Context)
        print("\n--- AI Context Block ---")
        print(ctx.get_all_prices_formatted())

        # 4. Demonstrate single access
        print("\n--- Specific Check ---")
        print(format_price_context("NVDA"))

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        print(
            "Reminder: Ensure you do not have a file named 'yfinance.py' in this folder!"
        )
