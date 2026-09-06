"""
Phase 4 runner — evaluate all unjudged runs using Structured LLM-as-Judge.

Usage:
    python -m scripts.run_judge
    python -m scripts.run_judge --run-id <run_id>
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

load_dotenv()

from src.judge.judge import StructuredJudge
from src.db.database import get_db

console = Console()


def print_banner() -> None:
    console.print(Panel.fit(
        "[bold green]Reliability Cockpit — LLM-as-Judge Evaluator[/bold green]\n"
        "[dim]Phase 4 — Structured State Verification, MTTR & Failure Fingerprinting[/dim]",
        border_style="green",
    ))


@click.command()
@click.option("--run-id", "-r", default=None, help="Evaluate a specific run ID")
def main(run_id: str) -> None:
    print_banner()

    if not os.getenv("GOOGLE_API_KEY"):
        console.print("[red]ERROR: GOOGLE_API_KEY not set.[/red]")
        sys.exit(1)

    judge = StructuredJudge()
    db = get_db()

    if run_id:
        console.print(f"[bold]Evaluating Run ID:[/bold] {run_id}")
        verdict = judge.judge_run(run_id)
        console.print(Panel(
            f"[bold]Verdict:[/bold] {'[green]PASSED[/green]' if verdict['passed'] else '[red]FAILED[/red]'}\n"
            f"[bold]Score:[/bold] {verdict['score']:.2f} / 1.0\n"
            f"[bold]Failure Category:[/bold] {verdict['failure_category']}\n"
            f"[bold]Root Cause Step:[/bold] {verdict['root_cause_step']}\n"
            f"[bold]Reasoning:[/bold] {verdict['reasoning']}",
            title=f"Judge Verdict — {run_id[:8]}",
            border_style="green" if verdict['passed'] else "red",
        ))
    else:
        console.print("[bold]Evaluating all unjudged runs...[/bold]")
        count = judge.judge_all_pending()
        console.print(f"[green][OK] Judged {count} pending runs.[/green]\n")

    # Display fingerprint summary
    fp = db.get_fingerprint()
    table = Table(
        title="System Fingerprint & Failure Frequency",
        box=box.ROUNDED,
        header_style="bold green",
    )
    table.add_column("Fault Type", style="cyan")
    table.add_column("Outcome", style="yellow")
    table.add_column("Count", justify="right", style="magenta")

    for f in fp["fault_frequency"]:
        table.add_row(f["fault_type"], f["outcome"], str(f["count"]))

    console.print(table)
    console.print(f"\n[bold]Overall System Pass Rate:[/bold] [green]{fp['overall_pass_rate'] * 100:.1f}%[/green]")
    if fp['avg_mttr_seconds']:
        console.print(f"[bold]Average MTTR:[/bold] [cyan]{fp['avg_mttr_seconds']:.2f} seconds[/cyan]")


if __name__ == "__main__":
    main()
