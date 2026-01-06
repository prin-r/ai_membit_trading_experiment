"""
Membit client wrapper for fetching contextual data.
https://docs.membit.ai/api-usage/python
"""

import os
import re
from typing import Optional, List, Any
from membit import MembitClient


def strip_url_lines(text: str) -> str:
    """Remove lines containing **URL**: from Membit LLM output."""
    lines = text.split("\n")
    filtered = [line for line in lines if not re.match(r"^\*\*URL\*\*:", line.strip())]
    return "\n".join(filtered)


def get_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise ValueError(f"Missing: {key}")
    return value


class MembitWrapper:
    """Wrapper around Membit SDK for fetching contextual data."""

    def __init__(self, api_key: Optional[str] = None, verbose: bool = False):
        self.api_key = api_key or get_env("MEMBIT_API_KEY")
        self.client = MembitClient(api_key=self.api_key)
        self.verbose = verbose

    def search_clusters(self, query: str, limit: int = 5) -> List[Any]:
        """Search for trending topic clusters.

        Returns list of cluster objects from the 'clusters' key in the response.
        """
        response = self.client.cluster_search(query, limit=limit)
        # Response is a dict with 'clusters' key containing the list
        if isinstance(response, dict):
            clusters = response.get("clusters", [])
            return clusters
        return []

    def search_posts(self, query: str, limit: int = 10) -> str:
        """Search for individual posts.

        Returns LLM-formatted string from Membit API (with URLs stripped).
        """
        response = self.client.post_search(query, limit=limit, output_format="llm")
        # With output_format="llm", response is a pre-formatted string
        if isinstance(response, str):
            result = strip_url_lines(response)
        elif isinstance(response, dict):
            content = response.get("content", str(response))
            result = strip_url_lines(content)
        else:
            result = strip_url_lines(str(response)) if response else "No posts found."

        return result

    def get_cluster_info(self, cluster_name: str, limit: int = 5) -> str:
        """Get detailed info about a specific cluster."""
        response = self.client.cluster_info(
            cluster_name, limit=limit, output_format="llm"
        )
        # With output_format="llm", response is a pre-formatted string
        if isinstance(response, str):
            result = strip_url_lines(response)
        elif isinstance(response, dict):
            content = response.get("content", str(response))
            result = strip_url_lines(content)
        else:
            result = (
                strip_url_lines(str(response)) if response else "No cluster info found."
            )

        return result

    def format_context_for_prompt(self, posts: List[Any]) -> str:
        """Format Membit search results as context for AI prompt."""
        if not posts:
            return ""

        context_parts = ["Here is relevant context from recent posts:\n"]
        for i, post in enumerate(posts, 1):
            # Handle both string and dict responses
            if isinstance(post, dict):
                content = post.get("content", str(post))
            else:
                content = str(post)
            context_parts.append(f"{i}. {content}\n")

        return "\n".join(context_parts)

    def format_posts_for_prompt(self, posts: List[Any]) -> str:
        """Format posts search results for AI prompt."""
        if not posts:
            return "No posts found."

        lines = ["Recent posts:\n"]
        for i, post in enumerate(posts, 1):
            if isinstance(post, dict):
                content = post.get("content", post.get("text", str(post)))
                source = post.get("source", "")
                timestamp = post.get("timestamp", post.get("created_at", ""))
                line = f"{i}. {content}"
                if source:
                    line += f" (source: {source})"
                if timestamp:
                    line += f" [{timestamp}]"
                lines.append(line)
            else:
                lines.append(f"{i}. {post}")

        return "\n".join(lines)

    def format_clusters_for_prompt(self, clusters: List[Any]) -> str:
        """Format cluster search results for AI prompt."""
        if not clusters:
            return "No trending clusters found."

        lines = ["Trending topic clusters:\n"]
        for i, cluster in enumerate(clusters, 1):
            if isinstance(cluster, dict):
                label = cluster.get("label", cluster.get("name", str(cluster)))
                count = cluster.get("count", cluster.get("size", ""))
                summary = cluster.get("summary", "")
                line = f"{i}. {label}"
                if count:
                    line += f" ({count} posts)"
                if summary:
                    line += f": {summary}"
                lines.append(line)
            else:
                lines.append(f"{i}. {cluster}")

        return "\n".join(lines)
