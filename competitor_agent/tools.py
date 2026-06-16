"""Research tools available to the agent.

The primary tool is web search (Tavily). The design is deliberately tool-first so
engineers can register additional LangChain tools or custom MCP integrations
(e.g. internal pricing DBs, Crunchbase, news APIs) by appending to RESEARCH_TOOLS.
"""
from __future__ import annotations

import os
from typing import List

from langchain_core.tools import tool

try:
    from tavily import TavilyClient
except Exception:  # pragma: no cover - import guard for environments without tavily
    TavilyClient = None


def _client() -> "TavilyClient":
    if TavilyClient is None:
        raise RuntimeError("tavily-python is not installed. `pip install tavily-python`.")
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY is not set. Add it to your environment/.env.")
    return TavilyClient(api_key=key)


@tool
def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web for recent, factual information.

    Returns a dict with an `answer` (Tavily's synthesized summary) and a list of
    `results`, each containing title, url and a content snippet. Use this to find
    pricing, features, positioning and recent news about a company or product.
    """
    client = _client()
    resp = client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
        include_answer=True,
    )
    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
        }
        for r in resp.get("results", [])
    ]
    return {"answer": resp.get("answer", ""), "results": results}


# Engineers: append custom MCP-backed or API-backed tools here.
RESEARCH_TOOLS: List = [web_search]
