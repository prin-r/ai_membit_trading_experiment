"""
AI Trading Assistant - Single entry point with interactive selection.
Uses TradingAgent with Exchange MCP and optional Membit tools.
"""
from dotenv import load_dotenv

from ..agent import TradingAgent
from ..price_client import fetch_price, format_price_context
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
        status = "OK" if not tc["error"] else f"Error: {tc['error']}"
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
