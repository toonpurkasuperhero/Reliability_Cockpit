"""
Master Runner — Complete End-to-End Pipeline Execution.

Executes:
1. Baseline Happy Path Runs (Phase 1)
2. Persona Matrix Simulation Runs (Phase 2)
3. Agentic-Chaos & Adversarial Fault Injections (Phase 3)
4. Structured LLM-as-Judge Evaluation (Phase 4)
5. Closed-Loop Auto-Mitigation Engine (Phase 5)
6. Reliability Nutrition Label Export (Phase 6)

Usage:
    python -m scripts.run_all
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

load_dotenv()

from src.agent.agent import RefundSupportAgent
from src.scenarios.scenarios import all_scenarios
from src.agent.personas import all_personas
from src.chaos.runner import ChaosRunner
from src.chaos.faults import all_faults
from src.judge.judge import StructuredJudge
from src.mitigation.engine import MitigationEngine
from src.reporting.label import ReliabilityLabelGenerator

console = Console()


def main():
    console.print(Panel.fit(
        "[bold cyan]RELIABILITY COCKPIT — MASTER PIPELINE RUNNER[/bold cyan]\n"
        "[dim]Powered by DeepAgentLabs Ecosystem: AgenticLens & Agentic-Chaos[/dim]",
        border_style="cyan",
    ))

    if not os.getenv("GOOGLE_API_KEY"):
        console.print("[red]ERROR: GOOGLE_API_KEY is not set in environment.[/red]")
        sys.exit(1)

    # 1. Baseline Run
    console.print("\n[bold cyan]STEP 1: Executing Phase 1 Baseline Runs...[/bold cyan]")
    agent = RefundSupportAgent()
    scenarios = all_scenarios()
    for sc in scenarios[:2]:  # Quick run
        console.print(f"  * Baseline: {sc.id}")
        agent.run_scenario(sc.id, persona_id="P01", run_type="baseline")
    console.print("  [green][OK] Phase 1 Baseline complete.[/green]")

    # 2. Persona Matrix
    console.print("\n[bold cyan]STEP 2: Executing Phase 2 Persona Simulations...[/bold cyan]")
    personas = all_personas()
    for p in personas[1:3]:
        console.print(f"  * Persona: {p.id} ({p.name})")
        agent.run_scenario("S01", persona_id=p.id, run_type="persona")
    console.print("  [green][OK] Phase 2 Persona matrix complete.[/green]")

    # 3. Agentic-Chaos Fault Injection
    console.print("\n[bold red]STEP 3: Executing Phase 3 Agentic-Chaos Fault Injections...[/bold red]")
    chaos_runner = ChaosRunner()
    faults = all_faults()
    for flt in faults[:3]:
        console.print(f"  [CHAOS] Fault: {flt.id} ({flt.name})")
        chaos_runner.run_chaos_scenario("S01", persona_id="P01", fault_id=flt.id)
    console.print("  [green][OK] Phase 3 Chaos testing complete.[/green]")

    # 4. Structured LLM-as-Judge
    console.print("\n[bold green]STEP 4: Executing Phase 4 Structured LLM-as-Judge...[/bold green]")
    judge = StructuredJudge()
    judged_count = judge.judge_all_pending()
    console.print(f"  [green][OK] Phase 4 complete. Evaluated {judged_count} runs.[/green]")

    # 5. Closed-Loop Auto-Mitigation
    console.print("\n[bold yellow]STEP 5: Executing Phase 5 Closed-Loop Auto-Mitigation...[/bold yellow]")
    engine = MitigationEngine()
    mitigated_count = engine.mitigate_all_failed()
    console.print(f"  [green][OK] Phase 5 complete. Dispatched {mitigated_count} mitigations.[/green]")

    # 6. Reliability Nutrition Label
    console.print("\n[bold magenta]STEP 6: Generating Phase 6 Reliability Nutrition Label...[/bold magenta]")
    label_gen = ReliabilityLabelGenerator()
    lbl = label_gen.generate_label()
    html_path = label_gen.export_html_label(lbl)
    console.print(f"  [green][OK] Phase 6 complete. Label grade: {lbl.certification_grade}[/green]")
    console.print(f"  [green][OK] HTML exported to: {html_path}[/green]")

    console.print(Panel(
        f"[bold green]ALL PIPELINE PHASES COMPLETED SUCCESSFULLY![/bold green]\n\n"
        f"[bold]To launch the interactive dashboard:[/bold]\n"
        f"python -m dashboard.app",
        title="Pipeline Execution Summary",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
