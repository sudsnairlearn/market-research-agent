"""Typed state and structured-output schemas for the competitor analysis graph."""
from __future__ import annotations

import operator
from typing import Annotated, List

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# ----- Structured outputs the LLM is asked to return --------------------------

class CompetitorList(BaseModel):
    """Output of the planning node."""
    competitors: List[str] = Field(
        description="Direct competitors to the target company, most relevant first."
    )
    rationale: str = Field(
        description="One or two sentences on how these competitors were chosen."
    )


class PricePoint(BaseModel):
    """A single numeric price for charting (plan, product, or tier)."""
    item: str = Field(description="Plan / product / tier name, e.g. 'Plus' or 'Galaxy S26'.")
    price_usd: float = Field(description="Price in USD as a number (no currency symbol).")
    period: str = Field(
        default="",
        description="Billing period if relevant: 'mo', 'yr', or '' for one-time.",
    )


class Metric(BaseModel):
    """A numeric headline metric for charting (revenue, users, seats, etc.)."""
    label: str = Field(description="What the number measures, e.g. 'Monthly active users'.")
    value: float = Field(description="The numeric value (no units).")
    unit: str = Field(default="", description="Unit, e.g. 'M', 'B', '$B', '%'.")


class CompetitorInsight(BaseModel):
    """Structured insight extracted for a single competitor."""
    name: str
    positioning: str = Field(description="One-paragraph market positioning summary.")
    pricing: List[str] = Field(
        default_factory=list,
        description="Concrete pricing data points as text (product -> price).",
    )
    price_points: List[PricePoint] = Field(
        default_factory=list,
        description="Numeric prices for charting, extracted from the sources when available.",
    )
    metrics: List[Metric] = Field(
        default_factory=list,
        description="Numeric headline metrics for charting (revenue, users, seats, growth %).",
    )
    key_features: List[str] = Field(
        default_factory=list, description="Differentiating features or capabilities."
    )
    recent_news: List[str] = Field(
        default_factory=list,
        description="Notable developments in the last ~12 months, each dated if possible.",
    )
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)


# ----- Graph state ------------------------------------------------------------

class ResearchTask(TypedDict):
    """A single competitor queued for research."""
    name: str


class SourceRef(TypedDict):
    title: str
    url: str


class AgentState(TypedDict, total=False):
    """The full state threaded through the LangGraph.

    `operator.add` reducers let map-style nodes append concurrently without
    clobbering each other.
    """
    target: str                                   # company/product under analysis
    competitors: List[str]                        # chosen by the planner
    plan_rationale: str
    research_queue: List[ResearchTask]
    insights: Annotated[List[CompetitorInsight], operator.add]
    sources: Annotated[List[SourceRef], operator.add]
    briefing: str                                 # final markdown deliverable
    errors: Annotated[List[str], operator.add]
    docs_used: Annotated[List[str], operator.add]  # local-doc filenames used
