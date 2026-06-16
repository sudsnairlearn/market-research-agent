"""Streamlit UI for the Market Research Agent — Competitor Analysis.

Run:
    streamlit run app.py

Two modes:
  • Demo mode  — instant, no API keys; renders the bundled Apple analysis + curated charts.
  • Live mode  — runs the LangGraph agent for any company (needs NEBIUS + TAVILY keys);
                 charts are built from the agent's own extracted numbers.
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from competitor_agent import demo_data as dd

load_dotenv()

st.set_page_config(page_title="Market Research Agent", page_icon="🛰️", layout="wide")

# ---------------------------------------------------------------- styling -----
st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; max-width: 1200px;}
      .hero {background: linear-gradient(110deg,#1d1d3b,#3b2f63 55%,#6d4aff);
             padding: 26px 32px; border-radius: 16px; color: #fff; margin-bottom: 18px;}
      .hero h1 {margin: 0; font-size: 1.85rem;}
      .hero p {margin: 6px 0 0; opacity: .85;}
      .card {background: var(--background-color,#fff); border: 1px solid #e6e6ef;
             border-radius: 14px; padding: 18px 20px; height: 100%;
             box-shadow: 0 2px 10px rgba(20,20,60,.05);}
      .card h3 {margin: 0 0 4px;}
      .good {color:#0f9d58;} .bad {color:#d23f31;}
    </style>
    """,
    unsafe_allow_html=True,
)

DEMO_PALETTE = {"Apple": "#6d4aff", "Samsung": "#1f6feb", "Google": "#ea4335", "Microsoft": "#00a4ef"}
BASE_COLORS = ["#6d4aff", "#1f6feb", "#ea4335", "#00a4ef", "#0f9d58", "#f4b400", "#9c27b0"]


# ------------------------------------------------------------- helpers --------
def insight_to_dict(i):
    """Accept either a Pydantic CompetitorInsight or a plain dict."""
    if hasattr(i, "model_dump"):
        return i.model_dump()
    return dict(i)


def color_map(names):
    return {n: BASE_COLORS[i % len(BASE_COLORS)] for i, n in enumerate(names)}


def coverage_frame(insights):
    rows = []
    for i in insights:
        d = insight_to_dict(i)
        rows.append(
            {
                "Competitor": d["name"],
                "Pricing points": len(d.get("pricing", [])),
                "Features": len(d.get("key_features", [])),
                "Recent news": len(d.get("recent_news", [])),
                "Strengths": len(d.get("strengths", [])),
                "Weaknesses": len(d.get("weaknesses", [])),
            }
        )
    return pd.DataFrame(rows)


def _coverage_and_swot(insights, cmap):
    """Charts that work for ANY company from the structured insight counts."""
    cov = coverage_frame(insights)

    st.markdown("##### Research coverage by competitor")
    metrics = ["Pricing points", "Features", "Recent news", "Strengths", "Weaknesses"]
    radar = go.Figure()
    for _, r in cov.iterrows():
        radar.add_trace(go.Scatterpolar(
            r=[r[m] for m in metrics], theta=metrics, fill="toself", name=r["Competitor"],
            line_color=cmap.get(r["Competitor"])))
    radar.update_layout(height=420, polar=dict(radialaxis=dict(visible=True)))
    st.plotly_chart(radar, width="stretch")

    sw = cov.melt(id_vars="Competitor", value_vars=["Strengths", "Weaknesses"],
                  var_name="Type", value_name="Count")
    fig = px.bar(sw, x="Competitor", y="Count", color="Type", barmode="group",
                 color_discrete_map={"Strengths": "#0f9d58", "Weaknesses": "#d23f31"},
                 title="Strengths vs. weaknesses identified")
    fig.update_layout(height=340)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(cov, width="stretch", hide_index=True)


def _entry_monthly_price(pps):
    """Lowest paid price per competitor, normalized to $/mo for fair comparison."""
    vals = []
    for pp in pps:
        v = pp.get("price_usd")
        if not v or v <= 0:
            continue
        per = (pp.get("period") or "").lower()
        if per.startswith("y"):   # annual -> monthly
            v = v / 12.0
        vals.append(v)
    return min(vals) if vals else None


def render_live_charts(insights, target):
    names = [insight_to_dict(i)["name"] for i in insights]
    cmap = color_map(names)

    # ---- Pricing: one comparable bar per competitor (entry paid plan, $/mo) ----
    prows = []
    for i in insights:
        d = insight_to_dict(i)
        entry = _entry_monthly_price(d.get("price_points", []) or [])
        if entry is not None:
            prows.append({"Competitor": d["name"], "Entry paid plan ($/mo)": round(entry, 2)})

    # ---- Metrics: keep only real quantitative figures, then group by unit ----
    mrows = []
    for i in insights:
        d = insight_to_dict(i)
        for mt in d.get("metrics", []) or []:
            unit = (mt.get("unit") or "").strip()
            val = mt.get("value")
            if val is None:
                continue
            # drop feature-flag-like junk (e.g. value <=1 with no unit)
            if unit == "" and val <= 1:
                continue
            mrows.append({"Competitor": d["name"], "Metric": mt["label"],
                          "Value": val, "Unit": unit or "count"})

    c1, c2 = st.columns(2)
    if prows:
        df = pd.DataFrame(prows)
        fig = px.bar(df, x="Competitor", y="Entry paid plan ($/mo)", color="Competitor",
                     color_discrete_map=cmap, title="Entry paid plan, normalized to $/mo")
        fig.update_layout(height=380, showlegend=False, xaxis_title="")
        c1.plotly_chart(fig, width="stretch")
        c1.caption("Lowest paid tier per competitor (annual prices \u00f7 12). Full pricing in the Competitor cards tab.")
    else:
        c1.info("No numeric pricing was extracted from sources for these competitors.")

    if mrows:
        mdf = pd.DataFrame(mrows)
        units = list(dict.fromkeys(mdf["Unit"]))  # preserve first-seen order
        with c2:
            st.markdown("**Headline metrics** (one chart per unit, so scales stay comparable)")
            for u in units:
                sub = mdf[mdf["Unit"] == u]
                fig = px.bar(sub, x="Value", y="Metric", color="Competitor", orientation="h",
                             color_discrete_map=cmap, title=f"Metrics in {u}")
                fig.update_layout(height=max(180, 60 * len(sub)), yaxis_title="", xaxis_title="",
                                  margin=dict(l=10, r=10, t=46, b=10))
                st.plotly_chart(fig, width="stretch")
    else:
        c2.info("No numeric headline metrics were extracted for these competitors.")

    _coverage_and_swot(insights, cmap)


def render_demo_charts(insights):
    """Curated, hand-checked charts for the bundled Apple analysis."""
    c1, c2 = st.columns(2)
    rev = {k: v for k, v in dd.QUARTERLY_REVENUE_B.items() if v is not None}
    df = pd.DataFrame({"Company": list(rev), "Revenue ($B)": list(rev.values())})
    fig = px.bar(df, x="Company", y="Revenue ($B)", text="Revenue ($B)", color="Company",
                 color_discrete_map=DEMO_PALETTE, title="Latest reported quarterly revenue ($B)")
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, height=360)
    c1.plotly_chart(fig, width="stretch")

    rows = [{"Company": co, "Tier": tier, "Price ($)": price}
            for co, tiers in dd.FLAGSHIP_PRICING.items() for tier, price in tiers.items()]
    df = pd.DataFrame(rows)
    fig = px.bar(df, x="Tier", y="Price ($)", color="Company", barmode="group",
                 color_discrete_map=DEMO_PALETTE, title="Flagship phone pricing by tier ($)")
    fig.update_layout(height=360)
    c2.plotly_chart(fig, width="stretch")

    c3, c4 = st.columns(2)
    df = pd.DataFrame(dd.AI_METRICS)
    fig = px.bar(df, x="value", y="metric", color="company", orientation="h",
                 color_discrete_map=DEMO_PALETTE, title="Headline AI metrics (mixed units)")
    fig.update_layout(height=360, yaxis_title="", xaxis_title="")
    c3.plotly_chart(fig, width="stretch")

    sat, cats = dd.SATISFACTION, list(dd.SATISFACTION.keys())
    fig = go.Figure()
    for brand, color in (("Apple", DEMO_PALETTE["Apple"]), ("Samsung", DEMO_PALETTE["Samsung"])):
        fig.add_bar(name=brand, x=cats, y=[sat[c][brand] for c in cats], marker_color=color)
    fig.update_layout(title="2026 ACSI customer satisfaction (Apple vs Samsung)",
                      barmode="group", height=360, yaxis=dict(range=[70, 90]))
    c4.plotly_chart(fig, width="stretch")

    _coverage_and_swot(insights, DEMO_PALETTE)


def render_cards(insights):
    cols = st.columns(len(insights)) if insights else []
    for col, i in zip(cols, insights):
        d = insight_to_dict(i)
        with col:
            st.markdown(
                f"<div class='card'><h3>{d['name']}</h3>"
                f"<p style='font-size:.86rem;opacity:.8'>{d.get('positioning','')}</p>"
                f"<b>Pricing</b><br>" + ("<br>".join(d.get("pricing", [])[:3]) or "—") +
                f"<br><br><b>Key features</b><ul style='margin:4px 0;padding-left:18px'>" +
                "".join(f"<li>{x}</li>" for x in d.get("key_features", [])[:3]) + "</ul>"
                f"<b>Recent news</b><ul style='margin:4px 0;padding-left:18px'>" +
                "".join(f"<li>{x}</li>" for x in d.get("recent_news", [])[:2]) + "</ul>"
                f"<span class='good'><b>+</b> {', '.join(d.get('strengths', [])[:2])}</span><br>"
                f"<span class='bad'><b>–</b> {', '.join(d.get('weaknesses', [])[:2])}</span>"
                "</div>",
                unsafe_allow_html=True,
            )


# ------------------------------------------------------------- sidebar --------
with st.sidebar:
    st.header("⚙️ Configuration")
    mode = st.radio("Mode", ["Demo (no keys)", "Live (run agent)"], index=0)
    target = st.text_input("Company / product", value="Apple")
    max_comp = st.number_input("Max competitors", min_value=2, max_value=5, value=3, step=1)
    st.divider()
    st.caption("Live mode needs API keys (used only in this session):")
    nebius_key = st.text_input("NEBIUS_API_KEY", type="password",
                               value=os.environ.get("NEBIUS_API_KEY", ""))
    tavily_key = st.text_input("TAVILY_API_KEY", type="password",
                               value=os.environ.get("TAVILY_API_KEY", ""))
    model_name = st.text_input("Model",
                               value=os.environ.get("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct"))
    run = st.button("🚀 Run analysis", type="primary", width="stretch")


# --------------------------------------------------------------- header -------
st.markdown(
    f"<div class='hero'><h1>🛰️ Market Research Agent</h1>"
    f"<p>Autonomous market research • LangGraph + Nebius • analyzing "
    f"<b>{target or '—'}</b></p></div>",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------- state ---------
def _demo_result():
    return {
        "target": dd.DEMO_TARGET,
        "competitors": dd.DEMO_COMPETITORS,
        "insights": dd.DEMO_INSIGHTS,
        "briefing": dd.load_sample_briefing(),
        "demo": True,
    }


if "result" not in st.session_state:
    st.session_state.result = _demo_result()

if run:
    if mode.startswith("Demo"):
        st.session_state.result = _demo_result()
        st.success("Loaded bundled Apple demo analysis.")
    else:
        if not nebius_key or not tavily_key:
            st.error("Live mode needs both NEBIUS_API_KEY and TAVILY_API_KEY.")
            st.stop()
        os.environ["NEBIUS_API_KEY"] = nebius_key
        os.environ["TAVILY_API_KEY"] = tavily_key
        os.environ["MODEL_NAME"] = model_name
        os.environ["MAX_COMPETITORS"] = str(max_comp)
        from competitor_agent import run_analysis  # imported lazily so demo needs no keys
        with st.spinner(f"Agent running: plan → research → synthesize for {target}…"):
            final = run_analysis(target)
        st.session_state.result = {
            "target": target,
            "competitors": final.get("competitors", []),
            "insights": final.get("insights", []),
            "briefing": final.get("briefing", ""),
            "docs_used": final.get("docs_used", []),
            "demo": False,
        }
        st.success(f"Analyzed: {', '.join(st.session_state.result['competitors'])}")

res = st.session_state.result
insights = res["insights"]

# top metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Target", res["target"])
m2.metric("Competitors", len(res["competitors"]))
m3.metric("Insights extracted", len(insights))
m4.metric("Mode", "Demo" if res.get("demo") else "Live")

docs_used = res.get("docs_used", [])
if docs_used:
    from collections import Counter
    _cnt = Counter(docs_used)
    _summary = ", ".join(f"{name} ({c})" for name, c in _cnt.items())
    st.success(f"Local documents used: {_summary}", icon="📄")

if res.get("demo"):
    st.info("Showing the bundled Apple demo. Switch to **Live** mode in the sidebar to run the agent on any company.", icon="💡")

tab_charts, tab_cards, tab_brief = st.tabs(["📊 Charts", "🧩 Competitor cards", "📄 Briefing"])
with tab_charts:
    if res.get("demo"):
        render_demo_charts(insights)
    else:
        render_live_charts(insights, res["target"])
with tab_cards:
    render_cards(insights)
with tab_brief:
    st.markdown(res["briefing"])
    st.download_button("⬇️ Download briefing (.md)", res["briefing"],
                       file_name=f"{res['target'].lower().replace(' ','-')}-briefing.md")
