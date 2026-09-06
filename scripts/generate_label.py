"""
Phase 6 runner — generate and export Reliability Nutrition Label.

Usage:
    python -m scripts.generate_label
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

load_dotenv()

from src.reporting.label import ReliabilityLabelGenerator

console = Console()


def main():
    console.print(Panel.fit(
        "[bold magenta]Reliability Cockpit — Nutrition Label Generator[/bold magenta]\n"
        "[dim]Phase 6 — Certification & Business-Impact Translation[/dim]",
        border_style="magenta",
    ))

    gen = ReliabilityLabelGenerator()
    label = gen.generate_label()

    console.print(Panel(
        f"[bold]Grade:[/bold] {label.certification_grade}\n"
        f"[bold]Reliability Score:[/bold] [green]{label.overall_reliability_score}%[/green]\n"
        f"[bold]Pre-Mitigation Pass Rate:[/bold] {label.pre_mitigation_pass_rate}%\n"
        f"[bold]Post-Mitigation Pass Rate:[/bold] [bold green]{label.post_mitigation_pass_rate}%[/bold green]\n"
        f"[bold]Persona Diversity Score:[/bold] [yellow]{label.persona_diversity_score}%[/yellow]\n"
        f"[bold]MTTR:[/bold] [cyan]{label.avg_mttr_seconds} seconds[/cyan]\n\n"
        f"[bold]Business Impact:[/bold]\n{label.business_impact['summary_statement']}",
        title="Reliability Certification Badge",
        border_style="magenta",
    ))

    html_file = gen.export_html_label(label)
    console.print(f"\n[green][OK] HTML Nutrition Label exported to:[/green] [underline]{html_file}[/underline]\n")


if __name__ == "__main__":
    main()
