"""
Phase 1 runner — execute all 5 happy-path scenarios with the base persona
and print a rich summary table.

Usage:
    python -m scripts.run_happy_path
    python -m scripts.run_happy_path --scenario S01
    python -m scripts.run_happy_path --scenario S01 --persona P02
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

from src.agent.agent import RefundSupportAgent
from src.scenarios.scenarios import SCENARIOS, all_scenarios
from src.db.database import get_db

console = Console()


def print_banner() -> None:
    console.print(Panel.fit(
        "[bold cyan]Reliability Cockpit[/bold cyan]\n"
        "[dim]Phase 1 — Happy Path Baseline Run[/dim]\n"
        "[dim]AgenticLens: observability active[/dim]",
        border_style="cyan",
    ))


def print_run_result(scenario_id: str, persona_id: str, response: str, run) -> None:
    title = f"[green][OK][/green] {scenario_id} | Persona: {persona_id}"
    spans_info = "\n".join(
        f"  [dim]* {s.name}: {s.input_tokens} in {s.output_tokens} out tokens "
        f"| {s.latency_ms:.0f}ms | ${s.cost_usd:.5f}[/dim]"
        for s in run.spans
    )
    console.print(Panel(
        f"[bold]Response:[/bold]\n{response}\n\n"
        f"[bold]Spans:[/bold]\n{spans_info}\n\n"
        f"[bold]Totals:[/bold] "
        f"[yellow]{run.total_tokens} tokens[/yellow] | "
        f"[magenta]${run.total_cost_usd:.5f} USD[/magenta] | "
        f"[cyan]Run ID: {run.run_id[:8]}...[/cyan]",
        title=title,
        border_style="green",
    ))


def print_summary_table(results: list) -> None:
    table = Table(
        title="Baseline Run Summary",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Scenario", style="cyan", no_wrap=True)
    table.add_column("Persona", style="yellow")
    table.add_column("Status", style="bold")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost (USD)", justify="right")
    table.add_column("Spans", justify="right")
    table.add_column("Run ID", style="dim")

    for r in results:
        table.add_row(
            r["scenario_id"],
            r["persona_id"],
            "[green][OK][/green]" if r["success"] else "[red][ERROR][/red]",
            str(r["tokens"]),
            f"${r['cost']:.5f}",
            str(r["spans"]),
            r["run_id"][:8] + "...",
        )

    console.print(table)
    total_cost = sum(r["cost"] for r in results)
    console.print(
        f"\n[bold]Total cost for this run:[/bold] [magenta]${total_cost:.5f} USD[/magenta]"
    )
    console.print(
        f"[dim]Traces persisted to SQLite. "
        f"View with: python -m scripts.show_runs[/dim]"
    )


@click.command()
@click.option("--scenario", "-s", default=None, help="Run a single scenario (e.g. S01)")
@click.option("--persona", "-p", default="P01", help="Persona ID (P01–P05)")
@click.option("--verbose", "-v", is_flag=True, help="Show full agent responses")
def main(scenario: str, persona: str, verbose: bool) -> None:
    print_banner()

    if not os.getenv("GOOGLE_API_KEY"):
        console.print("[red]ERROR: GOOGLE_API_KEY not set. Copy .env.example → .env and add your key.[/red]")
        sys.exit(1)

    agent = RefundSupportAgent()
    db = get_db()

    scenarios_to_run = (
        [SCENARIOS[scenario]] if scenario else all_scenarios()
    )

    results = []
    for sc in scenarios_to_run:
        console.print(f"\n[bold]Running:[/bold] {sc.id} — {sc.name}")
        try:
            response, run = agent.run_scenario(
                scenario_id=sc.id,
                persona_id=persona,
                run_type="baseline",
            )
            results.append({
                "scenario_id": sc.id,
                "persona_id": persona,
                "success": True,
                "tokens": run.total_tokens,
                "cost": run.total_cost_usd,
                "spans": len(run.spans),
                "run_id": run.run_id,
            })
            if verbose:
                print_run_result(sc.id, persona, response, run)
            else:
                console.print(
                    f"  [green][OK][/green] Done | "
                    f"[yellow]{run.total_tokens} tokens[/yellow] | "
                    f"[magenta]${run.total_cost_usd:.5f}[/magenta] | "
                    f"[dim]{run.run_id[:8]}...[/dim]"
                )
        except Exception as e:
            console.print(f"  [red][ERROR]: {e}[/red]")
            results.append({
                "scenario_id": sc.id,
                "persona_id": persona,
                "success": False,
                "tokens": 0,
                "cost": 0.0,
                "spans": 0,
                "run_id": "—",
            })

    console.print()
    print_summary_table(results)


if __name__ == "__main__":
    main()
