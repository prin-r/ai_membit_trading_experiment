"""
AI Agent with MCP-style tool support.
Supports both Exchange tools (trading) and Membit tools (sentiment).
The agent decides when and how to use available tools.

Improvements (4 Jan 2026):
- Portfolio data is pre-injected into system prompt (no get_portfolio tool call needed)
- Hold is implicit: if no tool is called, position is held (no hold tool needed)
- Membit search strategy with specific query examples
"""
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .cerebras_client import call_cerebras
from .types import CallOptions
from .exchange_mcp import ExchangeMCP, get_exchange_tools
from .membit_client import MembitWrapper
from .prompts import build_system_prompt, build_portfolio_context


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    name: str
    result: Any
    error: Optional[str] = None


# Membit tools (MCP-style definitions)
MEMBIT_TOOLS = [
    {
        "name": "search_posts",
        "description": "Search for recent social media posts about a topic. Returns current news, sentiment, and discussions. Use this to understand market sentiment before making trading decisions.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g., 'Bitcoin crypto market news')"},
                "limit": {"type": "integer", "description": "Max posts to return", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_clusters",
        "description": "Search for trending topic clusters. Use this to discover what topics are trending.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for trending topics"},
                "limit": {"type": "integer", "description": "Max clusters to return", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_cluster_info",
        "description": "Get detailed info about a specific trending cluster by its label.",
        "parameters": {
            "type": "object",
            "properties": {
                "cluster_label": {"type": "string", "description": "The cluster label to get info for"},
                "limit": {"type": "integer", "description": "Max items to return", "default": 5}
            },
            "required": ["cluster_label"]
        }
    }
]


def format_tools_for_prompt(tools: List[Dict]) -> str:
    """Format tool definitions for the system prompt."""
    if not tools:
        return ""

    lines = [
        "AVAILABLE TOOLS:",
        "You can call these tools to gather information and execute trades.",
        "",
        "IMPORTANT: To call a tool, you MUST use this EXACT format:",
        'TOOL_CALL: {"name": "tool_name", "arguments": {...}}',
        "",
        "Example:",
        'TOOL_CALL: {"name": "search_posts", "arguments": {"query": "BTC market sentiment", "limit": 5}}',
        "",
        "Do NOT use code blocks, variables, or any other format. Just write TOOL_CALL: followed by the JSON.",
        "You may call multiple tools. After gathering information, make your trading decision.",
        ""
    ]

    for tool in tools:
        params = tool.get("parameters", {}).get("properties", {})
        param_list = ", ".join([f"{k}: {v.get('type', 'any')}" for k, v in params.items()])
        lines.append(f"- {tool['name']}({param_list}): {tool['description']}")

    return "\n".join(lines)


def parse_tool_calls(response: str) -> List[ToolCall]:
    """Parse tool calls from AI response."""
    calls = []

    # Primary pattern: TOOL_CALL: followed by JSON
    pattern = r'TOOL_CALL:\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'

    for match in re.finditer(pattern, response, re.IGNORECASE):
        try:
            data = json.loads(match.group(1))
            calls.append(ToolCall(
                name=data.get("name", ""),
                arguments=data.get("arguments", {})
            ))
        except json.JSONDecodeError:
            continue

    # Fallback pattern: catch {"name": "...", "arguments": {...}} without TOOL_CALL prefix
    # Only use if no calls found with primary pattern
    if not calls:
        fallback_pattern = r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[^{}]*\})\s*\}'
        for match in re.finditer(fallback_pattern, response):
            try:
                name = match.group(1)
                arguments = json.loads(match.group(2))
                # Only accept known tool names to avoid false positives
                # Note: get_portfolio and hold are removed - portfolio is pre-injected, hold is implicit
                known_tools = ["search_posts", "search_clusters", "get_cluster_info", "buy", "sell"]
                if name in known_tools:
                    calls.append(ToolCall(name=name, arguments=arguments))
            except json.JSONDecodeError:
                continue

    return calls


class TradingAgent:
    """
    AI Trading Agent with access to Exchange and Membit MCP tools.
    """

    def __init__(
        self,
        state_file: str,
        symbol: str = "BTC",
        use_membit: bool = False,
        verbose: bool = False,
    ):
        self.state_file = state_file
        self.symbol = symbol
        self.use_membit = use_membit
        self.verbose = verbose

        # Initialize Exchange MCP
        self.exchange = ExchangeMCP(state_file=state_file, default_symbol=symbol)

        # Initialize Membit if enabled
        self.membit = MembitWrapper(verbose=verbose) if use_membit else None

    def get_available_tools(self) -> List[Dict]:
        """Get all available tools for this agent."""
        tools = get_exchange_tools(self.symbol)
        if self.use_membit:
            tools.extend(MEMBIT_TOOLS)
        return tools

    def execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a tool call and return the result."""
        try:
            name = tool_call.name
            args = tool_call.arguments

            # Exchange tools (get_portfolio and hold removed - portfolio pre-injected, hold is implicit)
            if name == "buy":
                result = self.exchange.tool_buy(
                    usd_amount=args.get("usd_amount", 0),
                    symbol=args.get("symbol")
                )
                return ToolResult(
                    name=name,
                    result=result.message if result.success else None,
                    error=result.message if not result.success else None
                )

            elif name == "sell":
                result = self.exchange.tool_sell(
                    asset_amount=args.get("asset_amount", 0),
                    symbol=args.get("symbol")
                )
                return ToolResult(
                    name=name,
                    result=result.message if result.success else None,
                    error=result.message if not result.success else None
                )

            # Membit tools - only available if use_membit is enabled
            elif name in ["search_posts", "search_clusters", "get_cluster_info"]:
                if not self.membit:
                    return ToolResult(name=name, result=None, error=f"Tool '{name}' not available (Membit not enabled)")

                if name == "search_posts":
                    posts = self.membit.search_posts(
                        query=args.get("query", self.symbol),
                        limit=args.get("limit", 10)
                    )
                    formatted = self.membit.format_posts_for_prompt(posts)
                    return ToolResult(name=name, result=formatted)

                elif name == "search_clusters":
                    clusters = self.membit.search_clusters(
                        query=args.get("query", self.symbol),
                        limit=args.get("limit", 5)
                    )
                    formatted = self.membit.format_clusters_for_prompt(clusters)
                    return ToolResult(name=name, result=formatted)

                elif name == "get_cluster_info":
                    info = self.membit.get_cluster_info(
                        cluster_name=args.get("cluster_label", ""),
                        limit=args.get("limit", 5)
                    )
                    return ToolResult(name=name, result=json.dumps(info, indent=2))

            else:
                return ToolResult(name=name, result=None, error=f"Unknown tool: {name}")

        except Exception as e:
            return ToolResult(name=tool_call.name, result=None, error=str(e))

    def run(
        self,
        model: str,
        market_context: str,
        max_tool_rounds: int = 3,
        max_tokens: int = 1200,
    ) -> Dict[str, Any]:
        """
        Run the trading agent.

        Args:
            model: Cerebras model to use
            market_context: Pre-formatted market data (price, indicators)
            max_tool_rounds: Maximum rounds of tool calling
            max_tokens: Max tokens for AI response

        Returns:
            Dict with final_response, tool_calls, and executed_action
        """
        tools = self.get_available_tools()
        tool_prompt = format_tools_for_prompt(tools)

        # Pre-fetch portfolio data (no tool call needed - inject directly into prompt)
        portfolio_data = self.exchange.tool_get_portfolio(self.symbol)
        portfolio_context = build_portfolio_context(portfolio_data)

        if self.verbose:
            print(f"    [Pre-fetch] Portfolio data for {self.symbol}")
            print(f"    [Pre-fetch] -> {json.dumps(portfolio_data, indent=2)}")

        # Build system prompt using prompts.py
        system_prompt = build_system_prompt(
            symbol=self.symbol,
            portfolio_context=portfolio_context,
            market_context=market_context,
            tool_prompt=tool_prompt,
            use_membit=self.use_membit,
        )

        tool_calls_made = []
        conversation = []
        executed_action = None

        # Track portfolio fetch as a tool call for logging (but it wasn't an LLM tool call)
        tool_calls_made.append({
            "name": "get_portfolio",
            "arguments": {"symbol": self.symbol},
            "result": json.dumps(portfolio_data, indent=2),
            "error": None,
            "note": "Pre-injected into prompt (not an LLM tool call)",
        })

        # User message - portfolio is already in system prompt
        user_message = f"""Analyze the {self.symbol} market and execute your trading decision.

Your portfolio status is provided in the system context above.
Based on the portfolio data, market analysis, and {"social sentiment" if self.use_membit else "technical indicators"}, make your trading decision.

Remember: If you decide to HOLD, simply explain your reasoning without calling any tool."""

        # Phase 2: Let AI analyze and decide
        response = call_cerebras(CallOptions(
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            max_tokens=max_tokens,
        ))

        current_response = response.content
        conversation.append({"role": "assistant", "content": current_response})

        # Log model response in verbose mode
        if self.verbose:
            print(f"    [Model Response]\n{current_response}\n")

        # Tool calling loop
        for round_num in range(max_tool_rounds):
            tool_calls = parse_tool_calls(current_response)

            # Log membit tool usage decision
            if self.verbose and self.use_membit and round_num == 0:
                membit_tools_called = [tc.name for tc in tool_calls if tc.name in ["search_posts", "search_clusters", "get_cluster_info"]]
                if membit_tools_called:
                    # Extract reasoning before tool call (first 300 chars of response)
                    reasoning_preview = current_response[:1000].replace('\n', ' ').strip()
                    print(f"    [Membit] Called: {membit_tools_called}")
                    print(f"    [Membit] Reasoning: {reasoning_preview}...")
                else:
                    print(f"    [Membit] NOT CALLED - Model reasoning:\n{current_response[:500]}...")

            if not tool_calls:
                break

            # Execute tools
            tool_results = []
            for tc in tool_calls:
                if self.verbose:
                    print(f"    [Tool] {tc.name}({json.dumps(tc.arguments)})")
                result = self.execute_tool(tc)
                if self.verbose:
                    if result.error:
                        print(f"    [Tool] {tc.name} -> ERROR: {result.error}")
                    else:
                        print(f"    [Tool] {tc.name} -> {result.result}")
                tool_results.append(result)
                tool_calls_made.append({
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "result": result.result,
                    "error": result.error,
                })

                # Track executed trading action (hold is no longer a tool)
                if tc.name in ["buy", "sell"] and not result.error:
                    executed_action = {
                        "action": tc.name,
                        "arguments": tc.arguments,
                        "result": result.result,
                    }

            # Format results
            results_text = "\n\n".join([
                f"TOOL_RESULT ({r.name}):\n{r.result if not r.error else f'Error: {r.error}'}"
                for r in tool_results
            ])

            # Check if a trade was executed - if so, we're done
            if executed_action:
                conversation.append({"role": "tool_results", "content": results_text})
                break

            # Continue conversation with tool results
            follow_up = f"Tool results:\n\n{results_text}\n\nContinue your analysis and make a trading decision."

            response = call_cerebras(CallOptions(
                system_prompt=system_prompt,
                user_message=f"{user_message}\n\n{follow_up}",
                model=model,
                max_tokens=max_tokens,
            ))

            current_response = response.content
            conversation.append({"role": "tool_results", "content": results_text})
            conversation.append({"role": "assistant", "content": current_response})

            # Log follow-up model response in verbose mode
            if self.verbose:
                print(f"    [Model Response (Round {round_num + 2})]\n{current_response}\n")

        # If no trade was executed, return virtual HOLD for scheduler compatibility
        if executed_action is None:
            # Get current portfolio state for the hold message
            current_portfolio = self.exchange.tool_get_portfolio(self.symbol)
            if current_portfolio.get('has_position'):
                pos = current_portfolio.get('position', {})
                hold_message = f"Holding position. Current {pos.get('symbol', self.symbol)}: {pos.get('asset_amount', 0):.8f}, Unrealized P&L: ${pos.get('unrealized_pnl', 0):+,.2f}"
            else:
                hold_message = f"Holding position. No position. Cash: ${current_portfolio.get('available_cash', 0):,.2f}"

            executed_action = {
                "action": "hold",
                "arguments": {"symbol": self.symbol},
                "result": hold_message,
                "virtual": True,  # Flag to indicate this was implicit, not a tool call
            }

        return {
            "final_response": current_response,
            "tool_calls": tool_calls_made,
            "conversation": conversation,
            "executed_action": executed_action,
        }
