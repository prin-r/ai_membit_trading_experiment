"""
Compare Membit vs Basic mode results over time.
Analyzes which mode (with or without Membit tools) gives better trading results per model.
Includes leaderboard showing current portfolio values across all configurations.
"""
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Any

from .state_manager import load_portfolio, get_portfolio_value
from .price_client import fetch_bitcoin_price


RESULTS_DIR = ".results"
MODELS = ["llama3.1-8b", "llama-3.3-70b", "qwen-3-32b"]


@dataclass
class ModeStats:
    total_runs: int = 0
    buy_signals: int = 0
    sell_signals: int = 0
    hold_signals: int = 0
    positions_opened: int = 0
    positions_closed: int = 0
    total_pnl: float = 0.0
    winning_trades: int = 0
    losing_trades: int = 0
    errors: int = 0
    tool_calls: int = 0


@dataclass
class ModelComparison:
    model: str
    basic: ModeStats = field(default_factory=ModeStats)
    membit: ModeStats = field(default_factory=ModeStats)


def get_results_dir() -> str:
    """Get the path to the results directory."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), RESULTS_DIR)


def get_state_filename(model: str, use_tools: bool) -> str:
    """Generate unique state filename based on model and tools setting."""
    suffix = "_membit" if use_tools else "_basic"
    model_slug = model.replace(".", "_").replace("-", "_")
    return f"{model_slug}{suffix}.json"


def load_all_results() -> List[Dict[str, Any]]:
    """Load all result files."""
    results_dir = get_results_dir()
    if not os.path.exists(results_dir):
        return []

    all_results = []
    for filename in sorted(os.listdir(results_dir)):
        if filename.endswith(".json"):
            filepath = os.path.join(results_dir, filename)
            with open(filepath, "r") as f:
                results = json.load(f)
                all_results.extend(results)

    return all_results


def analyze_results(results: List[Dict[str, Any]]) -> Dict[str, ModelComparison]:
    """Analyze results and compute stats per model and mode."""
    comparisons: Dict[str, ModelComparison] = {}

    for r in results:
        model = r.get("model", "unknown")
        mode = r.get("mode", "basic")

        if model not in comparisons:
            comparisons[model] = ModelComparison(model=model)

        stats = comparisons[model].membit if mode == "membit" else comparisons[model].basic

        if "error" in r:
            stats.errors += 1
            continue

        stats.total_runs += 1

        # Count tool calls
        tool_calls = r.get("tool_calls", [])
        stats.tool_calls += len(tool_calls)

        action = r.get("action", "do_nothing")
        if action == "buy":
            stats.buy_signals += 1
        elif action == "sell":
            stats.sell_signals += 1
        else:
            stats.hold_signals += 1

        executed = r.get("executed", "")
        if executed == "opened_position":
            stats.positions_opened += 1
        elif executed == "closed_position":
            stats.positions_closed += 1
            pnl = r.get("pnl", 0)
            stats.total_pnl += pnl
            if pnl > 0:
                stats.winning_trades += 1
            else:
                stats.losing_trades += 1

    return comparisons


def print_stats(label: str, s: ModeStats):
    """Print stats for a mode."""
    win_rate = (s.winning_trades / s.positions_closed * 100) if s.positions_closed > 0 else 0
    print(f"  {label}:")
    print(f"    Runs: {s.total_runs} | Errors: {s.errors}")
    print(f"    Signals: BUY={s.buy_signals} SELL={s.sell_signals} HOLD={s.hold_signals}")
    print(f"    Trades: {s.positions_closed} closed | Win Rate: {win_rate:.1f}%")
    print(f"    Total P&L: ${s.total_pnl:+,.2f}")
    if s.tool_calls > 0:
        print(f"    Tool Calls: {s.tool_calls}")


def print_leaderboard(current_price: float):
    """Print the current leaderboard sorted by portfolio value."""
    print(f"\n{'=' * 70}")
    print("  LEADERBOARD - Current Portfolio Values")
    print(f"{'=' * 70}")
    print(f"\n  BTC Price: ${current_price:,.2f}\n")
    print(f"  {'Rank':<6}{'Config':<32}{'Value':<14}{'P&L':<14}{'Return':<10}")
    print("  " + "-" * 70)

    leaderboard = []
    for model in MODELS:
        for use_tools in [False, True]:
            mode = "membit" if use_tools else "basic"
            state_file = get_state_filename(model, use_tools)
            portfolio = load_portfolio(state_file)
            portfolio_value = get_portfolio_value(portfolio, current_price)
            pnl = portfolio_value - portfolio.starting_capital
            pnl_percent = (pnl / portfolio.starting_capital) * 100
            leaderboard.append({
                "config": f"{model} ({mode})",
                "value": portfolio_value,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "trades": len(portfolio.trade_history),
                "has_position": portfolio.position is not None,
            })

    leaderboard.sort(key=lambda x: x["value"], reverse=True)

    for i, entry in enumerate(leaderboard, 1):
        position_indicator = "*" if entry["has_position"] else " "
        print(f"  {i:<6}{entry['config']:<32}${entry['value']:>12,.2f}  ${entry['pnl']:>+11,.2f}  {entry['pnl_percent']:>+7.2f}%{position_indicator}")

    print("\n  * = has open BTC position")

    if leaderboard:
        winner = leaderboard[0]
        print(f"\n  LEADER: {winner['config']}")
        print(f"          ${winner['value']:,.2f} ({winner['pnl_percent']:+.2f}% return)")


def print_report(comparisons: Dict[str, ModelComparison]):
    """Print comparison report."""
    print("\n" + "=" * 70)
    print("  MEMBIT vs BASIC COMPARISON REPORT")
    print("=" * 70 + "\n")

    if not comparisons:
        print("No results found. Run the scheduler first:")
        print("  uv run python -m src.scheduler")
        return

    # Per-model comparison
    for model, comp in sorted(comparisons.items()):
        print(f"\n{'=' * 50}")
        print(f"  MODEL: {model}")
        print(f"{'=' * 50}")

        print_stats("Basic (Price + Indicators only)", comp.basic)
        print_stats("Membit (+ News/Sentiment tools)", comp.membit)

        # Winner for this model
        basic_pnl = comp.basic.total_pnl
        membit_pnl = comp.membit.total_pnl
        diff = membit_pnl - basic_pnl

        print()
        if diff > 0:
            print(f"    >> MEMBIT wins by ${diff:,.2f}")
        elif diff < 0:
            print(f"    >> BASIC wins by ${-diff:,.2f}")
        else:
            print(f"    >> TIE (both ${basic_pnl:,.2f})")

    # Overall summary
    print("\n" + "=" * 70)
    print("  OVERALL SUMMARY")
    print("=" * 70)

    total_basic_pnl = sum(c.basic.total_pnl for c in comparisons.values())
    total_membit_pnl = sum(c.membit.total_pnl for c in comparisons.values())
    total_basic_trades = sum(c.basic.positions_closed for c in comparisons.values())
    total_membit_trades = sum(c.membit.positions_closed for c in comparisons.values())
    total_tool_calls = sum(c.membit.tool_calls for c in comparisons.values())

    print(f"\n  Total P&L (all models):")
    print(f"    Basic:  ${total_basic_pnl:+,.2f} ({total_basic_trades} trades)")
    print(f"    Membit: ${total_membit_pnl:+,.2f} ({total_membit_trades} trades)")
    print(f"    Membit tool calls: {total_tool_calls}")

    diff = total_membit_pnl - total_basic_pnl
    print()
    if diff > 0:
        print(f"  VERDICT: Membit tools improve results by ${diff:,.2f}")
    elif diff < 0:
        print(f"  VERDICT: Basic mode is better by ${-diff:,.2f}")
    else:
        print(f"  VERDICT: No difference between modes")

    # Best overall configuration
    print("\n" + "-" * 70)
    all_configs = []
    for model, comp in comparisons.items():
        all_configs.append((f"{model} (basic)", comp.basic.total_pnl, comp.basic.positions_closed))
        all_configs.append((f"{model} (membit)", comp.membit.total_pnl, comp.membit.positions_closed))

    # Filter to those with at least one trade
    configs_with_trades = [c for c in all_configs if c[2] > 0]
    if configs_with_trades:
        best = max(configs_with_trades, key=lambda x: x[1])
        print(f"  BEST CONFIGURATION: {best[0]} (P&L: ${best[1]:+,.2f})")
    else:
        print("  BEST CONFIGURATION: No trades completed yet")
    print("-" * 70)


def main():
    """Generate comparison report with leaderboard."""
    print("Fetching current BTC price...")
    price_data = fetch_bitcoin_price()
    print(f"BTC Price: ${price_data.price:,.2f}")

    # Print leaderboard first (current portfolio standings)
    print_leaderboard(price_data.price)

    # Then print historical analysis
    results = load_all_results()
    print(f"\nLoaded {len(results)} historical result entries")

    comparisons = analyze_results(results)
    print_report(comparisons)


if __name__ == "__main__":
    main()
