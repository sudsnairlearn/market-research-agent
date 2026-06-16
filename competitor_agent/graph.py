"""LangGraph state machine for autonomous competitor analysis.

Flow:

    plan_competitors                     (LLM picks competitors)
          |
          v
    dispatch_research  --fan out-->  research_competitor  (one per competitor)
          |                                   |
          |                              (web_search tool calls + structured extract)
          v                                   |
    synthesize_briefing  <-----  collect  <---/
          |
          v
        END

State is checkpointed so a run can be paused/resumed, and the dispatch step uses
LangGraph `Send` to fan out research across competitors in parallel.
"""
from __future__ import annotations

import json
import os
from typing import List

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph

from .prompts import (
    EXTRACT_HUMAN,
    EXTRACT_SYSTEM,
    PLANNER_HUMAN,
    PLANNER_SYSTEM,
    SYNTH_HUMAN,
    SYNTH_SYSTEM,
)
from .state import AgentState, CompetitorInsight, CompetitorList
from .tools import web_search


# Nebius AI Studio exposes an OpenAI-compatible API, so we drive it via ChatOpenAI.
NEBIUS_DEFAULT_BASE_URL = "https://api.studio.nebius.com/v1/"


def _llm(temperature: float = 0.2, max_tokens: int = 8000) -> ChatOpenAI:
    return ChatOpenAI(
        model=os.environ.get("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct"),
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=os.environ.get("NEBIUS_API_KEY"),
        base_url=os.environ.get("NEBIUS_BASE_URL", NEBIUS_DEFAULT_BASE_URL),
    )


# --------------------------------------------------------------------------- #
# Node 1: plan competitors
# --------------------------------------------------------------------------- #
def plan_competitors(state: AgentState) -> dict:
    max_competitors = int(os.environ.get("MAX_COMPETITORS", 3))
    llm = _llm(max_tokens=1024).with_structured_output(CompetitorList)
    msg = [
        ("system", PLANNER_SYSTEM.format(max_competitors=max_competitors)),
        ("human", PLANNER_HUMAN.format(target=state["target"])),
    ]
    result: CompetitorList = llm.invoke(msg)
    competitors = result.competitors[:max_competitors]
    return {
        "competitors": competitors,
        "plan_rationale": result.rationale,
        "research_queue": [{"name": c} for c in competitors],
    }


# --------------------------------------------------------------------------- #
# Dispatcher: fan out one research node per competitor
# --------------------------------------------------------------------------- #
def dispatch_research(state: AgentState) -> List[Send]:
    return [
        Send("research_competitor", {"target": state["target"], "competitor": task["name"]})
        for task in state.get("research_queue", [])
    ]


# --------------------------------------------------------------------------- #
# Node 2 (mapped): research a single competitor
# --------------------------------------------------------------------------- #
def research_competitor(payload: dict) -> dict:
    target = payload["target"]
    competitor = payload["competitor"]
    n_searches = int(os.environ.get("SEARCHES_PER_COMPETITOR", 4))

    queries = [
        f"{competitor} pricing plans cost 2026",
        f"{competitor} key features product lineup 2026",
        f"{competitor} market positioning strategy vs {target}",
        f"{competitor} latest news 2026",
    ][:n_searches]

    evidence = []
    sources = []
    errors = []
    for q in queries:
        try:
            res = web_search.invoke({"query": q, "max_results": 5})
        except Exception as e:  # keep the run alive if one search fails
            errors.append(f"search failed for '{q}': {e}")
            continue
        if res.get("answer"):
            evidence.append({"query": q, "answer": res["answer"]})
        for r in res.get("results", []):
            evidence.append({"query": q, **r})
            if r.get("url"):
                sources.append({"title": r.get("title", ""), "url": r["url"]})

    # Structured extraction. Wrapped so one competitor's failure (e.g. a truncated
    # response) doesn't abort the whole graph run.
    llm = _llm(max_tokens=8000).with_structured_output(CompetitorInsight)
    try:
        insight: CompetitorInsight = llm.invoke(
            [
                ("system", EXTRACT_SYSTEM),
                (
                    "human",
                    EXTRACT_HUMAN.format(
                        target=target,
                        competitor=competitor,
                        evidence=json.dumps(evidence)[:12000],
                    ),
                ),
            ]
        )
    except Exception as e:
        errors.append(f"extraction failed for {competitor}: {type(e).__name__}: {e}")
        insight = CompetitorInsight(
            name=competitor,
            positioning="Structured extraction was truncated or failed; see the sources below.",
        )

    # dedupe sources by url
    seen, deduped = set(), []
    for s in sources:
        if s["url"] not in seen:
            seen.add(s["url"])
            deduped.append(s)

    return {"insights": [insight], "sources": deduped, "errors": errors}


# --------------------------------------------------------------------------- #
# Node 3: synthesize the briefing
# --------------------------------------------------------------------------- #
def synthesize_briefing(state: AgentState) -> dict:
    insights = state.get("insights", [])
    insights_json = json.dumps([i.model_dump() for i in insights], indent=2)
    llm = _llm(temperature=0.3, max_tokens=8000)
    resp = llm.invoke(
        [
            ("system", SYNTH_SYSTEM),
            ("human", SYNTH_HUMAN.format(target=state["target"], insights=insights_json)),
        ]
    )
    briefing = resp.content if isinstance(resp.content, str) else str(resp.content)

    # append a sources appendix
    srcs = state.get("sources", [])
    if srcs:
        lines = ["\n\n---\n\n## Sources\n"]
        for s in srcs:
            title = s.get("title") or s.get("url")
            lines.append(f"- [{title}]({s['url']})")
        briefing += "\n".join(lines)
    return {"briefing": briefing}


# --------------------------------------------------------------------------- #
# Graph assembly
# --------------------------------------------------------------------------- #
def build_graph(checkpointer=None):
    g = StateGraph(AgentState)
    g.add_node("plan_competitors", plan_competitors)
    g.add_node("research_competitor", research_competitor)
    g.add_node("synthesize_briefing", synthesize_briefing)

    g.add_edge(START, "plan_competitors")
    g.add_conditional_edges("plan_competitors", dispatch_research, ["research_competitor"])
    g.add_edge("research_competitor", "synthesize_briefing")
    g.add_edge("synthesize_briefing", END)

    return g.compile(checkpointer=checkpointer or MemorySaver())


def run_analysis(target: str, thread_id: str = "default") -> AgentState:
    """Convenience wrapper: run the full graph for a target and return final state."""
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke({"target": target}, config=config)
