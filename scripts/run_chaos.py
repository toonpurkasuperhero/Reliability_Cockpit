"""
Phase 3 runner — execute Chaos & Adversarial runs using Agentic-Chaos.

Usage:
    python -m scripts.run_chaos
    python -m scripts.run_chaos --fault F01
    python -m scripts.run_chaos --scenario S01 --fault F03
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

from src.chaos.runner import ChaosRunner
from src.chaos.faults import FAULT_CATALOG, all_faults
from src.scenarios.scenarios import SCENARIOS, all_scenarios

console = Console()


def print_banner() -> None:
    console.print(Panel.fit(
        "[bold red]Reliability Cockpit — Agentic-Chaos Harness[/bold red]\n"
        "[dim]Phase 3 — Fault Injection & Adversarial Red-Teaming[/dim]\n"
        "[dim]Agentic-Chaos: Active Fault Injection Active[/dim]",
        border_style="red",
    ))


@click.command()
@click.option("--scenario", "-s", default=None, help="Scenario ID (e.g. S01)")
@click.option("--fault", "-f", default=None, help="Fault ID (F01–F07)")
@click.option("--persona", "-p", default="P01", help="Persona ID (P01–P05)")
def main(scenario: str, fault: str, persona: str) -> None:
    print_banner()

    if not os.getenv("GOOGLE_API_KEY"):
        console.print("[red]ERROR: GOOGLE_API_KEY not set.[/red]")
        sys.exit(1)

    runner = ChaosRunner()

    # ── Predictive Failure Fingerprinting Pre-Check ────────────────────────────
    pred = runner.db.predict_vulnerabilities()
    console.print(f"[bold yellow][PREDICTIVE ANALYSIS][/bold yellow] {pred['message']} (Confidence: {pred['confidence_score']*100:.0f}%)\n")

    scenarios_to_run = [SCENARIOS[scenario]] if scenario else all_scenarios()
    faults_to_run = [FAULT_CATALOG[fault]] if fault else all_faults()

    # Prioritize predicted vulnerable fault first
    if not fault and pred.get("predicted_fault_id"):
        pf_id = pred["predicted_fault_id"]
        faults_to_run.sort(key=lambda f: 0 if f.id == pf_id else 1)

    results = []

    for sc in scenarios_to_run:
        for flt in faults_to_run:
            console.print(f"\n[bold]Chaos Test:[/bold] {sc.id} x [red]{flt.id} ({flt.name})[/red]")
            try:
                response_text, run, f_id = runner.run_chaos_scenario(
                    scenario_id=sc.id,
                    persona_id=persona,
                    fault_id=flt.id,
                )
                cost = run.total_cost_usd if run else 0.0
                tokens = run.total_tokens if run else 0
                run_id = run.run_id if run else "FAILED"

                results.append({
                    "scenario_id": sc.id,
                    "fault_id": flt.id,
                    "fault_name": flt.name,
                    "status": "Handled/Completed" if run else "Crashed",
                    "tokens": tokens,
                    "cost": cost,
                    "run_id": run_id,
                })

                console.print(
                    f"  [green][OK][/green] Done | "
                    f"[yellow]{tokens} tokens[/yellow] | "
                    f"[magenta]${cost:.5f}[/magenta] | "
                    f"[dim]{run_id[:8]}...[/dim]"
                )
            except Exception as e:
                console.print(f"  [red][ERROR] Fault execution failed: {e}[/red]")
                results.append({
                    "scenario_id": sc.id,
                    "fault_id": flt.id,
                    "fault_name": flt.name,
                    "status": f"Error: {e}",
                    "tokens": 0,
                    "cost": 0.0,
                    "run_id": "-",
                })

    # Summary table
    table = Table(
        title="Chaos & Adversarial Test Matrix Results",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold red",
    )
    table.add_column("Scenario", style="cyan")
    table.add_column("Fault ID", style="red")
    table.add_column("Fault Name", style="yellow")
    table.add_column("Status", style="bold")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost (USD)", justify="right")
    table.add_column("Run ID", style="dim")

    for r in results:
        table.add_row(
            r["scenario_id"],
            r["fault_id"],
            r["fault_name"],
            r["status"],
            str(r["tokens"]),
            f"${r['cost']:.5f}",
            r["run_id"][:8] + "...",
        )

    console.print("\n", table)


if __name__ == "__main__":
    main()
