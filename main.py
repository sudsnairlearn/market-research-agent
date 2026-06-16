"""CLI entry point for the competitor analysis agent.

Usage:
    python main.py "Notion"
    python main.py "Apple" --out briefings/apple.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import re

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from competitor_agent import run_analysis

console = Console()


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Autonomous competitor analysis agent.")
    parser.add_argument("target", help="Company or product name to analyze.")
    parser.add_argument("--out", help="Output markdown path.", default=None)
    args = parser.parse_args()

    if not os.environ.get("NEBIUS_API_KEY"):
        console.print("[red]NEBIUS_API_KEY is not set.[/red] Copy .env.example to .env.")
        raise SystemExit(1)

    console.print(Panel.fit(f"Researching competitors for: [bold]{args.target}[/bold]"))
    with console.status("[bold green]Agent running (plan → research → synthesize)..."):
        final = run_analysis(args.target)

    competitors = ", ".join(final.get("competitors", []))
    console.print(f"[green]Competitors analyzed:[/green] {competitors}")
    if final.get("errors"):
        console.print(f"[yellow]{len(final['errors'])} non-fatal issue(s) during research.[/yellow]")

    briefing = final.get("briefing", "")
    out_path = args.out or f"briefings/{slugify(args.target)}-{dt.date.today()}.md"
    path = pathlib.Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"# Competitive Analysis Briefing: {args.target}\n\n*Generated {dt.date.today()} by the Market Research Agent.*\n\n"
    path.write_text(header + briefing, encoding="utf-8")
    console.print(f"[bold green]Briefing written to:[/bold green] {path}")


if __name__ == "__main__":
    main()
