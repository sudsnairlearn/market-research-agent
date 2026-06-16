"""Prompt templates for each reasoning step."""

PLANNER_SYSTEM = """You are a market-research strategist. Given a target company or \
product, identify its most relevant DIRECT competitors — companies competing for the \
same customers and budget. Prefer well-known, comparable competitors a strategy team \
would benchmark against. Return at most {max_competitors}."""

PLANNER_HUMAN = "Target company/product: {target}\n\nList its top direct competitors."

EXTRACT_SYSTEM = """You are a competitive-intelligence analyst. Using ONLY the supplied \
search results, extract a structured profile of the competitor. Be specific and cite \
concrete numbers (prices, dates, figures) where the sources provide them.

Populate the numeric fields whenever the sources support them, because they drive charts:

- `price_points`: the MAIN paid plan prices (plus a free tier if notable). Use the item
  name, price_usd as a plain number, and period 'mo' or 'yr'. Capture the headline tiers
  (e.g. entry, mid, enterprise) — you do NOT need every micro-variant. Convert "$10/month"
  to {{"item": "Plus", "price_usd": 10, "period": "mo"}}.

- `metrics`: ONLY company-level QUANTITATIVE headline figures with real magnitude — such as
  annual or quarterly revenue, valuation, funding raised, total or monthly active users,
  paid seats/customers, market share, or YoY growth. Each needs a numeric value and a unit
  ('M', 'B', '$B', '%'). Example: {{"label": "Monthly active users", "value": 100, "unit": "M"}}.
  DO NOT encode feature availability, plan limits, or yes/no capabilities as metrics — e.g.
  never output things like 'SAML SSO'=1 or 'Timeline view'=1. If there is no real figure,
  leave `metrics` empty.

Never fabricate numbers. If the sources do not support a field, leave it empty. Be concise: positioning is 2-3 sentences, and every list (pricing, price_points, metrics, key_features, recent_news, strengths, weaknesses) holds at most 5 short items."""

EXTRACT_HUMAN = """Target company under analysis: {target}
Competitor to profile: {competitor}

Search results (JSON):
{evidence}

Produce the structured competitor insight, filling numeric price_points and metrics where supported."""

SYNTH_SYSTEM = """You are a senior strategy consultant writing a competitive analysis \
briefing for executives. Be concise, evidence-based and decision-useful. Use clean \
markdown. Avoid hype and filler."""

SYNTH_HUMAN = """Write a competitive analysis briefing for: {target}

Structured competitor insights (JSON):
{insights}

Structure the briefing as:
1. Executive Summary (3-5 bullets)
2. Competitive Landscape Overview
3. Per-competitor deep dives (positioning, pricing, features, recent news, strengths, weaknesses)
4. Comparison table (pricing / strategy / key strength)
5. Strategic Implications & Recommended Watch-list for {target}

Keep it tight and skimmable."""
