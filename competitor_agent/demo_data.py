"""Structured demo dataset for the Apple analysis.

Lets the Streamlit UI render rich charts and a full briefing WITHOUT requiring
API keys (Demo mode). Numbers are sourced from the live research run documented in
sample_output/apple-competitive-briefing.md (mid-2026).
"""
from __future__ import annotations

import pathlib

DEMO_TARGET = "Apple"
DEMO_COMPETITORS = ["Samsung", "Google", "Microsoft"]

# Latest reported quarterly revenue (USD billions). Samsung's Galaxy unit isn't
# broken out comparably, so it's marked None and shown as N/A.
QUARTERLY_REVENUE_B = {
    "Apple": 111.2,      # Q2 FY2026, +17% YoY
    "Samsung": None,     # Galaxy division not separately comparable
    "Google": 109.9,     # Alphabet Q1 2026, +22% YoY
    "Microsoft": 82.9,   # Q3 FY2026, +18% YoY
}

# Flagship entry pricing (USD) by tier.
FLAGSHIP_PRICING = {
    "Apple": {"Base": 799, "Plus/Air": 999, "Pro": 1099},        # iPhone 17 / Air / Pro
    "Samsung": {"Base": 899.99, "Plus/Air": 1099.99, "Pro": 1299.99},  # S26 / S26+ / Ultra
}

# AI-related headline metrics for the comparison.
AI_METRICS = [
    {"company": "Google", "metric": "Gemini monthly users (M)", "value": 750},
    {"company": "Microsoft", "metric": "Paid Copilot seats (M)", "value": 20},
    {"company": "Microsoft", "metric": "AI revenue run-rate ($B)", "value": 37},
    {"company": "Apple", "metric": "Services revenue ($B/qtr)", "value": 30.98},
]

# 2026 ACSI customer-satisfaction scores (Apple vs Samsung).
SATISFACTION = {
    "Overall": {"Apple": 80, "Samsung": 81},
    "Flagship users": {"Apple": 82, "Samsung": 84},
}

# Structured insight cards (mirrors CompetitorInsight shape) for Demo mode.
DEMO_INSIGHTS = [
    {
        "name": "Samsung",
        "positioning": "Premium Android flagship leader competing head-to-head with iPhone; "
        "leaning into flexible on-device + cloud 'Galaxy AI' vs Apple's privacy-first approach.",
        "pricing": ["Galaxy S26: $899.99", "Galaxy S26+: $1,099.99", "Galaxy S26 Ultra: $1,299.99"],
        "key_features": [
            "Three AI engines: Perplexity (search), Google Gemini (agentic), Bixby (conversational)",
            "'Now Nudge' reads on-screen context to suggest next actions",
            "Display and foldable hardware leadership",
        ],
        "recent_news": [
            "Feb 2026: Galaxy S26 series unveiled, framing 'agentic AI'",
            "Took outright ACSI customer-satisfaction lead over Apple for the first time",
        ],
        "strengths": ["AI feature breadth shipping today", "Flagship satisfaction lead", "Hardware/display leadership"],
        "weaknesses": ["Price hikes squeeze value perception", "Relies on Google's Gemini for agentic features", "Weaker ecosystem lock-in than Apple"],
    },
    {
        "name": "Google",
        "positioning": "AI-platform challenger embedding Gemini across Android and Cloud — and "
        "now also Apple's AI supplier via a ~$1B/year Gemini deal powering the new Siri.",
        "pricing": ["Pixel 10a value tier", "Gemini consumer subscriptions", "Gemini Enterprise (paid MAUs +40% QoQ)"],
        "key_features": [
            "1.2T-parameter Gemini model",
            "Gemini Live + AI camera features on Pixel",
            "Gemini as AI layer across Android and Workspace",
        ],
        "recent_news": [
            "~$1B/year deal to supply Gemini to Apple for the new Siri",
            "Racing to entrench Gemini in Android ahead of Apple's AI reboot",
            "Q1 2026 revenue $109.9B (+22% YoY)",
        ],
        "strengths": ["Model leadership and reach", "Dual revenue: competes with and supplies Apple", "Gemini ~750M monthly users"],
        "weaknesses": ["Pixel hardware niche vs iPhone", "AI monetization narrative under market scrutiny"],
    },
    {
        "name": "Microsoft",
        "positioning": "Not a direct device rival, but the benchmark for enterprise AI + cloud "
        "monetization that executives use to judge Apple's AI strategy.",
        "pricing": ["Microsoft 365 Copilot per-seat", "Azure consumption", "Surface hardware line"],
        "key_features": [
            "Copilot across Microsoft 365",
            "Azure AI platform + OpenAI partnership",
            "Surface devices (margin competition with Mac/iPad)",
        ],
        "recent_news": [
            "Q3 FY2026 revenue $82.9B (+18%); Microsoft Cloud $54.5B (+29%)",
            "AI run-rate surpassed $37B (+123% YoY)",
            "20M+ paid Copilot seats (up from 15M in Jan 2026)",
        ],
        "strengths": ["Best-in-class AI monetization", "Enterprise distribution"],
        "weaknesses": ["Minimal consumer-device/mobile presence", "Not a threat to iPhone directly"],
    },
]

_HERE = pathlib.Path(__file__).resolve().parent.parent
SAMPLE_BRIEFING_PATH = _HERE / "sample_output" / "apple-competitive-briefing.md"


def load_sample_briefing() -> str:
    try:
        return SAMPLE_BRIEFING_PATH.read_text(encoding="utf-8")
    except Exception:
        return "_Sample briefing file not found._"
