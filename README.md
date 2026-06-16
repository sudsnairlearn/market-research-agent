# Market Research Agent — Competitor Analysis (LangChain + LangGraph)

An autonomous agent that takes a **company or product name**, researches its
competitors with live web search, extracts structured insights (pricing, features,
positioning, recent news), and writes a formatted **competitive analysis briefing**.

Built on **LangGraph** (stateful multi-step graph) + **LangChain** tools, powered by
**Nebius AI Studio** (OpenAI-compatible open models). This is the agent every strategy team, PM, and founder wishes
they had running weekly.

---

## How it works

```
        ┌──────────────────┐
START → │ plan_competitors │   LLM picks the N most relevant direct competitors
        └────────┬─────────┘
                 │  Send() fan-out (one branch per competitor)
                 ▼
        ┌────────────────────┐   For each competitor, runs several web_search
        │ research_competitor│   queries (pricing / features / positioning / news),
        │   (mapped, ∥)      │   then the LLM extracts a structured CompetitorInsight
        └────────┬───────────┘
                 │  results merged via operator.add reducers
                 ▼
        ┌─────────────────────┐  LLM writes the executive briefing + comparison
        │ synthesize_briefing │  table + strategic implications, appends sources
        └────────┬────────────┘
                 ▼
                END
```

Key LangGraph building blocks used:

| Concept | Where |
|---|---|
| `StateGraph` + typed `AgentState` | `competitor_agent/state.py`, `graph.py` |
| Parallel fan-out with `Send` | `dispatch_research` in `graph.py` |
| Concurrent-safe state merges (`Annotated[..., operator.add]`) | `state.py` |
| Structured outputs (`with_structured_output`) | `plan_competitors`, `research_competitor` |
| Tools (`@tool web_search`) | `competitor_agent/tools.py` |
| Checkpointer (`MemorySaver`) for pause/resume | `build_graph` in `graph.py` |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in NEBIUS_API_KEY and TAVILY_API_KEY
```

- **NEBIUS_API_KEY** — powers the agent (open models via Nebius). https://studio.nebius.com
- **TAVILY_API_KEY** — web search tool. Free tier at https://tavily.com

## Run

```bash
python main.py "Notion"
python main.py "Apple" --out briefings/apple.md
```

The briefing is written to `briefings/<target>-<date>.md`. A real sample produced by
this workflow lives in [`sample_output/apple-competitive-briefing.md`](sample_output/apple-competitive-briefing.md).

## Web UI (Streamlit)

A visual dashboard wraps the agent with charts, competitor cards, and the briefing.

```bash
streamlit run app.py
```

- **Demo mode** (default) — loads instantly with **no API keys**, rendering the bundled
  Apple analysis: revenue, flagship-pricing, AI-metric and customer-satisfaction charts,
  a research-coverage radar, per-competitor cards, and the full briefing.
- **Live mode** — paste your `NEBIUS_API_KEY` + `TAVILY_API_KEY` in the sidebar, enter
  any company, and the LangGraph agent runs end-to-end; charts and cards update from the
  agent's structured output.

The UI has three tabs — **Charts**, **Competitor cards**, **Briefing** (with a download
button). Chart data for Demo mode lives in `competitor_agent/demo_data.py`.

## Use as a library

```python
from competitor_agent import run_analysis
state = run_analysis("Linear")
print(state["briefing"])
```

## Extending (engineers)

- **Add data sources:** register more LangChain tools or **custom MCP integrations**
  (Crunchbase, internal pricing DB, news API) in `competitor_agent/tools.py` by
  appending to `RESEARCH_TOOLS`, and reference them from `research_competitor`.
- **Human-in-the-loop:** swap `MemorySaver` for `SqliteSaver` and add an `interrupt`
  before `synthesize_briefing` to let an analyst approve/curate the chosen competitors.
- **Tracing & evals:** set `LANGSMITH_API_KEY` / `LANGSMITH_TRACING=true` to trace
  every node in LangSmith and write evals against the structured `CompetitorInsight`
  outputs.
- **Schedule it:** wrap `run_analysis` in a cron/worker to produce a fresh briefing
  weekly.

## Project layout

```
competitor-analysis-agent/
├── main.py                     # CLI
├── app.py                      # Streamlit UI (charts + cards + briefing)
├── requirements.txt
├── .env.example
├── competitor_agent/
│   ├── __init__.py
│   ├── state.py                # AgentState + Pydantic schemas
│   ├── tools.py                # web_search tool (Tavily) + tool registry
│   ├── prompts.py              # prompt templates
│   ├── demo_data.py            # structured data powering the UI demo mode
│   └── graph.py                # the LangGraph state machine
└── sample_output/
    └── apple-competitive-briefing.md
```
