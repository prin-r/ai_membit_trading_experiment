"""
Scenario 2: Cerebras chat with full context.
Combines price data, technical indicators, AND Membit news/sentiment.
Tracks position state persistently.
"""
import re
from datetime import datetime
from dotenv import load_dotenv

from ..cerebras_client import call_cerebras
from ..price_client import fetch_bitcoin_price, format_price_context
from ..indicators_client import fetch_all_indicators, format_indicators_context
from ..state_manager import load_position, save_position, clear_position, format_position_context, Position
from ..membit_client import MembitWrapper
from ..types import CallOptions


def parse_action(response_content: str) -> str:
    """Parse the AI response to extract the recommended action."""
    content_lower = response_content.lower()

    # Look for explicit action keywords
    if "action: buy" in content_lower or "recommendation: buy" in content_lower:
        return "buy"
    elif "action: sell" in content_lower or "recommendation: sell" in content_lower:
        return "sell"
    elif "action: do nothing" in content_lower or "recommendation: do nothing" in content_lower:
        return "do_nothing"

    # Fallback: look for action words in context
    if re.search(r'\b(buy|enter|open.+position)\b', content_lower):
        return "buy"
    elif re.search(r'\b(sell|exit|close.+position)\b', content_lower):
        return "sell"

    return "do_nothing"


def main():
    load_dotenv()

    # Initialize clients
    membit = MembitWrapper()

    # Step 1: Check existing position
    print("Checking existing position...")
    current_position = load_position()

    # Step 2: Fetch real-time price data from Band Protocol
    print("Fetching current Bitcoin price from Band Protocol...")
    price_data = fetch_bitcoin_price()
    price_context = format_price_context(price_data)
    print(f"{price_context}")

    # Step 3: Format position context
    position_context = format_position_context(current_position, price_data.price)
    print(f"{position_context}")

    # Step 4: Fetch technical indicators from Twelve Data
    print("Fetching technical indicators from Twelve Data...")
    indicators = fetch_all_indicators(symbol="BTC/USD")
    indicators_context = format_indicators_context(indicators, price_data.price)
    print(f"{indicators_context}")

    # Step 5: Fetch news/sentiment from Membit
    print("Fetching current Bitcoin news and sentiment from Membit...")
    posts = membit.search_posts("Bitcoin BTC crypto market", limit=10)
    clusters = membit.search_clusters("Bitcoin price sentiment", limit=3)

    print(f"\nMembit Posts ({len(posts)} found):")
    for i, post in enumerate(posts[:5], 1):  # Show first 5
        if isinstance(post, dict):
            content = post.get("content", post.get("text", str(post)))[:100]
        else:
            content = str(post)[:100]
        print(f"  {i}. {content}...")

    print(f"\nMembit Clusters ({len(clusters)} found):")
    for i, cluster in enumerate(clusters, 1):
        if isinstance(cluster, dict):
            label = cluster.get("label", str(cluster))[:100]
        else:
            label = str(cluster)[:100]
        print(f"  {i}. {label}...")

    membit_context = membit.format_context_for_prompt(posts)
    print()

    # Step 6: Determine available actions based on position
    if current_position:
        available_actions = "SELL (close position) or DO NOTHING (hold current position)"
        user_question = "Based on my current position, market data, and news sentiment, should I sell or do nothing?"
    else:
        available_actions = "BUY (open position) or DO NOTHING (wait)"
        user_question = "Based on current market data and news sentiment, should I buy Bitcoin now or do nothing?"

    # Step 7: Create enhanced system prompt with ALL data sources
    system_prompt = f"""You are a financial analyst AI with access to comprehensive real-time market data.

{position_context}

CURRENT PRICE DATA:
{price_context}

{indicators_context}

CURRENT NEWS & SOCIAL SENTIMENT (from Membit - real-time social data):
{membit_context}

AVAILABLE ACTIONS: {available_actions}

Based on this comprehensive data (price, technical indicators, and news/sentiment), provide your analysis and recommendation.
End your response with a clear "ACTION: [BUY/SELL/DO NOTHING]" line.
Always include a disclaimer that this is not financial advice and users should do their own research."""

    # Step 8: Call Cerebras with enriched context
    print("Analyzing with Cerebras AI...\n")
    response = call_cerebras(CallOptions(
        system_prompt=system_prompt,
        user_message=user_question,
        max_tokens=1200,
    ))

    print(f"Provider: {response.provider}")
    print(f"\nANALYSIS:\n{response.content}")

    # Step 9: Parse action and update state
    action = parse_action(response.content)
    print(f"\n{'='*50}")
    print(f"PARSED ACTION: {action.upper()}")

    if action == "buy" and current_position is None:
        new_position = Position(
            action="buy",
            price=price_data.price,
            timestamp=datetime.now().isoformat(),
            symbol="BTC",
        )
        save_position(new_position)
        print(f"Position OPENED at ${price_data.price:,.2f}")
    elif action == "sell" and current_position is not None:
        pnl = price_data.price - current_position.price
        pnl_percent = (pnl / current_position.price) * 100
        clear_position()
        print(f"Position CLOSED at ${price_data.price:,.2f}")
        print(f"P&L: ${pnl:,.2f} ({pnl_percent:+.2f}%)")
    else:
        print("No position change.")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
