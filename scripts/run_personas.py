"""
Phase 2 runner — execute persona-simulation runs across all 5 personas × 5 scenarios.

Usage:
    python -m scripts.run_personas
    python -m scripts.run_personas --persona P02
    python -m scripts.run_personas --scenario S01
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
from src.agent.personas import PERSONAS, all_personas
from src.scenarios.scenarios import SCENARIOS, all_scenarios
from src.scenarios.persona_generator import generate_persona_message
from src.db.database import get_db

console = Console()


def print_banner() -> None:
    console.print(Panel.fit(
        "[bold cyan]Reliability Cockpit — Persona Simulation[/bold cyan]\n"
        "[dim]Phase 2 — Multi-Persona Behavioral Tracing (Inclusive AI Testing)[/dim]\n"
        "[dim]5 Scenarios × 5 Personas = 25 Test Combinations[/dim]",
        border_style="cyan",
    ))


@click.command()
@click.option("--scenario", "-s", default=None, help="Run a single scenario (e.g. S01)")
@click.option("--persona", "-p", default=None, help="Run a single persona (e.g. P02)")
@click.option("--verbose", "-v", is_flag=True, help="Show full agent responses")
def main(scenario: str, persona: str, verbose: bool) -> None:
    print_banner()

    if not os.getenv("GOOGLE_API_KEY"):
        console.print("[red]ERROR: GOOGLE_API_KEY not set.[/red]")
        sys.exit(1)

    agent = RefundSupportAgent()

    scenarios_to_run = [SCENARIOS[scenario]] if scenario else all_scenarios()
    personas_to_run = [PERSONAS[persona]] if persona else all_personas()

    results = []

    for sc in scenarios_to_run:
        for p in personas_to_run:
            console.print(f"\n[bold]Running:[/bold] {sc.id} ({sc.name}) x [yellow]{p.id} ({p.name})[/yellow]")

            # Generate or fetch custom user message for this persona
            if p.id == "P01":
                user_msg = sc.user_message
            else:
                try:
                    console.print(f"  [dim]Rewriting message for {p.name}...[/dim]")
                    user_msg, _, _ = generate_persona_message(sc, p)
                except Exception as gen_err:
                    console.print(f"  [yellow][WARNING] Generation fallback: {gen_err}[/yellow]")
                    user_msg = sc.user_message

            try:
                response, run = agent.run_scenario(
                    scenario_id=sc.id,
                    persona_id=p.id,
                    custom_user_message=user_msg,
                    run_type="persona",
                )
                results.append({
                    "scenario_id": sc.id,
                    "persona_id": p.id,
                    "success": True,
                    "tokens": run.total_tokens,
                    "cost": run.total_cost_usd,
                    "spans": len(run.spans),
                    "run_id": run.run_id,
                })
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
                    "persona_id": p.id,
                    "success": False,
                    "tokens": 0,
                    "cost": 0.0,
                    "spans": 0,
                    "run_id": "-",
                })

    # Summary table
    table = Table(
        title="Persona Run Summary Matrix",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Scenario", style="cyan")
    table.add_column("Persona", style="yellow")
    table.add_column("Status", style="bold")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost (USD)", justify="right")
    table.add_column("Run ID", style="dim")

    for r in results:
        table.add_row(
            r["scenario_id"],
            r["persona_id"],
            "[green][OK][/green]" if r["success"] else "[red][ERROR][/red]",
            str(r["tokens"]),
            f"${r['cost']:.5f}",
            r["run_id"][:8] + "...",
        )

    console.print("\n", table)
    total_cost = sum(r["cost"] for r in results)
    console.print(f"[bold]Total Persona Matrix Cost:[/bold] [magenta]${total_cost:.5f} USD[/magenta]\n")


if __name__ == "__main__":
    main()
