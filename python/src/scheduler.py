"""
Scheduled execution comparing Basic vs Membit-tools mode.
Each configuration starts with $10,000 and trades to maximize P&L.
Uses TradingAgent with Exchange MCP for flexible position sizing.
Runs continuously, triggering every hour.
"""
import argparse
import json
import os
import time
import signal
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv

from .agent import TradingAgent
from .price_client import fetch_price, format_price_context
from .indicators_client import fetch_all_indicators, format_indicators_context
from .state_manager import load_portfolio, get_portfolio_value

# Configuration
MODELS = ["llama3.1-8b", "llama-3.3-70b", "qwen-3-32b"]
DEFAULT_SYMBOL = "BTC"  # Can be changed to any supported symbol
RESULTS_DIR = ".results"


def get_results_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), RESULTS_DIR)


def get_state_filename(model: str, symbol: str, use_membit: bool) -> str:
    suffix = "_membit" if use_membit else "_basic"
    model_slug = model.replace(".", "_").replace("-", "_")
    return f"{model_slug}_{symbol.lower()}{suffix}.json"


def run_single_agent(
    model: str,
    symbol: str,
    use_membit: bool,
    market_context: str,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run a single trading agent and return results."""
    state_file = get_state_filename(model, symbol, use_membit)

    agent = TradingAgent(
        state_file=state_file,
        symbol=symbol,
        use_membit=use_membit,
        verbose=verbose,
    )

    result = agent.run(
        model=model,
        market_context=market_context,
        max_tool_rounds=3,
        max_tokens=1200,
    )

    # Get updated portfolio info
    portfolio = load_portfolio(state_file)
    current_price = agent.exchange.get_price(symbol)
    portfolio_value = get_portfolio_value(portfolio, current_price)

    return {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "symbol": symbol,
        "mode": "membit" if use_membit else "basic",
        "price": current_price,
        "portfolio_value": portfolio_value,
        "executed_action": result["executed_action"],
        "tool_calls_count": len(result["tool_calls"]),
        "response_excerpt": result["final_response"][:1000],
    }


def run_once(symbol: str = DEFAULT_SYMBOL, verbose: bool = False):
    """Run a single trading simulation cycle for all configurations."""
    print(f"\n{'='*60}")
    print(f"  Trading Simulation Run: {datetime.now().isoformat()}")
    print(f"  Symbol: {symbol} | Starting Capital: $10,000")
    print(f"{'='*60}\n")

    # Fetch market data once for all agents (stored in global PriceContext)
    price = fetch_price(symbol)  # Fetches and stores in PriceContext
    indicators = fetch_all_indicators(symbol=f"{symbol}/USD")

    price_context_str = format_price_context(symbol)
    indicators_context = format_indicators_context(indicators, price)

    market_context = f"""CURRENT MARKET DATA:
{price_context_str}

{indicators_context}
"""

    print(f"{symbol} Price: ${price:,.2f}\n")

    results = []

    for model in MODELS:
        for use_membit in [False, True]:
            mode = "membit" if use_membit else "basic"
            state_file = get_state_filename(model, symbol, use_membit)
            portfolio = load_portfolio(state_file)
            portfolio_value = get_portfolio_value(portfolio, price)

            print(f"[{model}] ({mode}) - Portfolio: ${portfolio_value:,.2f}")

            try:
                result = run_single_agent(model, symbol, use_membit, market_context, verbose)
                results.append(result)

                action_info = "no action"
                if result["executed_action"]:
                    action = result["executed_action"]
                    action_info = f"{action['action'].upper()}"

                tool_info = f" | {result['tool_calls_count']} tools" if result['tool_calls_count'] else ""
                print(f"  -> {action_info}{tool_info}")

            except Exception as e:
                print(f"  -> ERROR: {e}")
                results.append({
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "symbol": symbol,
                    "mode": mode,
                    "error": str(e)
                })

    # Save results
    results_dir = get_results_dir()
    os.makedirs(results_dir, exist_ok=True)
    filepath = os.path.join(results_dir, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(filepath, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {filepath}")

    # Print action summary table
    print_action_summary(results)

    # Print leaderboard
    print_leaderboard(symbol, price)

    return results


def print_action_summary(results: List[Dict[str, Any]]):
    """Print a summary table of each model's action in this run."""
    print(f"\n{'='*110}")
    print(f"  RUN SUMMARY - Actions Taken")
    print(f"{'='*110}")
    print(f"{'Model':<20} {'Mode':<8} {'Action':<8} {'Details':<50} {'Fee':<10} {'Tools':<6}")
    print("-" * 110)

    for result in results:
        model = result.get("model", "?")
        mode = result.get("mode", "?")
        symbol = result.get("symbol", "BTC")
        price = result.get("price", 0)

        fee = "-"
        if "error" in result:
            action = "ERROR"
            details = result["error"][:48]
            tools = "-"
        else:
            executed = result.get("executed_action")
            if executed:
                action = executed["action"].upper()
                args = executed.get("arguments", {})

                if action == "BUY":
                    usd = args.get("usd_amount", 0)
                    fee_amt = usd * 0.001  # 0.10% fee
                    fee = f"${fee_amt:.2f}"
                    if price > 0:
                        asset_bought = usd / price
                        details = f"${usd:,.0f} @ ${price:,.0f} -> {asset_bought:.6f} {symbol}"
                    else:
                        details = f"${usd:,.2f}"

                elif action == "SELL":
                    amt = args.get("asset_amount", 0)
                    gross = amt * price if price > 0 else 0
                    fee_amt = gross * 0.001  # 0.10% fee
                    fee = f"${fee_amt:.2f}"
                    usd_received = gross - fee_amt
                    # Get remaining position from portfolio
                    state_file = get_state_filename(model, symbol, mode == "membit")
                    portfolio = load_portfolio(state_file)
                    if portfolio.position:
                        remaining = portfolio.position.asset_amount
                        details = f"Sold {amt:.6f} {symbol} -> ${usd_received:,.0f}, remaining: {remaining:.6f}"
                    else:
                        details = f"Sold {amt:.6f} {symbol} -> ${usd_received:,.0f}, closed"

                elif action == "HOLD":
                    # Get current position info
                    state_file = get_state_filename(model, symbol, mode == "membit")
                    portfolio = load_portfolio(state_file)
                    if portfolio.position:
                        pos_value = portfolio.position.asset_amount * price
                        details = f"Holding {portfolio.position.asset_amount:.6f} {symbol} (${pos_value:,.0f})"
                    else:
                        details = f"Holding cash: ${portfolio.current_capital:,.0f}"
                else:
                    details = str(args)[:56]
            else:
                action = "NONE"
                details = "No trade executed"

            tools = str(result.get("tool_calls_count", 0))

        # Truncate model name if too long
        model_short = model[:18] if len(model) > 18 else model
        details_short = details[:48] if len(details) > 48 else details
        print(f"{model_short:<20} {mode:<8} {action:<8} {details_short:<50} {fee:<10} {tools:<6}")

    print(f"{'='*110}")


def print_leaderboard(symbol: str, current_price: float):
    """Print the current leaderboard sorted by portfolio value."""
    print(f"\n{'='*60}")
    print(f"  LEADERBOARD ({symbol})")
    print(f"{'='*60}")
    print(f"{'Config':<30} {'Value':<12} {'P&L':<12} {'Return':<10}")
    print("-" * 64)

    leaderboard = []
    for model in MODELS:
        for use_membit in [False, True]:
            mode = "membit" if use_membit else "basic"
            state_file = get_state_filename(model, symbol, use_membit)
            portfolio = load_portfolio(state_file)
            portfolio_value = get_portfolio_value(portfolio, current_price)
            pnl = portfolio_value - portfolio.starting_capital
            pnl_percent = (pnl / portfolio.starting_capital) * 100
            leaderboard.append((f"{model} ({mode})", portfolio_value, pnl, pnl_percent))

    leaderboard.sort(key=lambda x: x[1], reverse=True)
    for i, (config, value, pnl, pnl_pct) in enumerate(leaderboard, 1):
        print(f"{i}. {config:<28} ${value:>10,.2f} ${pnl:>+10,.2f} {pnl_pct:>+8.2f}%")

    print(f"\n  WINNER: {leaderboard[0][0]} with ${leaderboard[0][2]:+,.2f} ({leaderboard[0][3]:+.2f}%)")


def main():
    """Run scheduler continuously, triggering every hour."""
    load_dotenv()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="AI Trading Simulation Scheduler")
    parser.add_argument("symbol", nargs="?", default=DEFAULT_SYMBOL, help="Trading symbol (default: BTC)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging for tool calls and Membit responses")
    args = parser.parse_args()

    symbol = args.symbol
    verbose = args.verbose
    INTERVAL_SECONDS = 60 * 60  # 1 hour

    def signal_handler(sig, frame):
        print("\n\nScheduler stopped by user.")
        raise SystemExit(0)

    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 60)
    print("  AI TRADING SIMULATION SCHEDULER")
    print(f"  Symbol: {symbol} | 6 Configs | $10,000 Each | Hourly")
    print("=" * 60)
    print(f"\nInterval: Every {INTERVAL_SECONDS // 60} minutes")
    print("Press Ctrl+C to stop\n")

    run_count = 0
    while True:
        run_count += 1
        print(f"\n{'#'*60}")
        print(f"  RUN #{run_count}")
        print(f"{'#'*60}")

        try:
            run_once(symbol, verbose)
        except Exception as e:
            print(f"Error during run: {e}")

        # Calculate next run time
        next_run = datetime.now().replace(microsecond=0) + timedelta(seconds=INTERVAL_SECONDS)
        print(f"\nNext run at: {next_run.isoformat()}")
        print(f"Sleeping for {INTERVAL_SECONDS // 60} minutes...")

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
