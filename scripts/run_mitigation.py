"""
Phase 5 runner — execute Auto-Mitigation on failed agent runs.

Usage:
    python -m scripts.run_mitigation
    python -m scripts.run_mitigation --run-id <run_id>
"""

from __future__ import annotations

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

from src.mitigation.engine import MitigationEngine
from src.db.database import get_db

console = Console()


def print_banner() -> None:
    console.print(Panel.fit(
        "[bold cyan]Reliability Cockpit — Closed-Loop Auto-Mitigation Engine[/bold cyan]\n"
        "[dim]Phase 5 — Automated Healing & Explainable Recovery[/dim]",
        border_style="cyan",
    ))


@click.command()
@click.option("--run-id", "-r", default=None, help="Mitigate a specific run ID")
def main(run_id: str) -> None:
    print_banner()

    engine = MitigationEngine()
    db = get_db()

    if run_id:
        res = engine.mitigate_run(run_id)
        console.print(Panel(
            f"[bold]Strategy:[/bold] {res['strategy']}\n"
            f"[bold]Pre-Score:[/bold] [red]{res['pre_score']:.2f}[/red] -> [bold]Post-Score:[/bold] [green]{res['post_score']:.2f}[/green]\n"
            f"[bold]MTTR:[/bold] [magenta]{res['mttr_seconds']}s[/magenta]\n\n"
            f"[bold]Explainable Recovery:[/bold]\n{res['explanation']}",
            title=f"Mitigation Result — {run_id[:8]}",
            border_style="green",
        ))
    else:
        console.print("[bold]Running mitigation on all failed runs...[/bold]")
        count = engine.mitigate_all_failed()
        console.print(f"[green][OK] Mitigated {count} failed runs.[/green]\n")


if __name__ == "__main__":
    main()
