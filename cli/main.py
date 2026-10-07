"""cli/main.py: Command Line Interface for CI Quality Gate and Agent Evaluation."""

import asyncio
import os
import sys
from typing import Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import typer
from rich.console import Console
from rich.table import Table

from core.db.repository import default_repository
from core.models.schema import Experiment, GateDecision
from core.regression.analyzer import RegressionAnalyzer

app = typer.Typer(help="Agent Evaluation, Health Monitoring & CI/CD Quality Gate CLI")
console = Console()


@app.command()
def health():
    """Display Agent Health overview inspired by OpenSearch agent-health."""
    summary = default_repository.get_health_summary()
    table = Table(title="🛡️ Agent Health Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Trajectories", str(summary["total_trajectories"]))
    table.add_row("Health Success Rate", f"{summary['success_rate']*100:.1f}%")
    table.add_row("Total Cost", f"${summary['total_cost_usd']:.4f}")
    table.add_row("Average Latency", f"{summary['avg_latency_ms']:.1f}ms")

    console.print(table)


@app.command()
def gate(
    dataset_id: str = typer.Option("default_regression_set", help="Dataset identifier"),
    candidate_score: float = typer.Option(0.92, help="Candidate agent mean score"),
    baseline_score: float = typer.Option(0.60, help="Baseline agent mean score"),
    candidate_version: str = typer.Option("2.0.0", help="Candidate agent version"),
    baseline_version: str = typer.Option("1.0.0", help="Baseline agent version"),
    cost_delta: float = typer.Option(-0.001, help="Cost delta USD"),
    latency_delta: float = typer.Option(-15.0, help="Latency delta ms"),
    new_failures: int = typer.Option(0, help="Count of new failure cases"),
    resolved_failures: int = typer.Option(1, help="Count of resolved failure cases"),
):
    """Enforces the CI/CD Quality Gate. Exits with code 0 on PASS, 1 on BLOCK."""
    candidate_exp = Experiment(
        name="Candidate Run",
        dataset_id=dataset_id,
        agent_id="agent_under_test",
        agent_version=candidate_version,
        total_samples=10,
        passed_samples=10 if new_failures == 0 else 8,
        mean_score=candidate_score,
        mean_cost_usd=0.004,
        mean_latency_ms=120.0,
    )
    baseline_exp = Experiment(
        name="Baseline Run",
        dataset_id=dataset_id,
        agent_id="agent_under_test",
        agent_version=baseline_version,
        total_samples=10,
        passed_samples=7,
        mean_score=baseline_score,
        mean_cost_usd=0.005,
        mean_latency_ms=135.0,
    )

    result = RegressionAnalyzer.compare(
        candidate=candidate_exp,
        baseline=baseline_exp,
    )

    console.print(result.summary_markdown)

    if result.gate_decision == GateDecision.BLOCK:
        console.print("[bold red]🛑 CI QUALITY GATE BLOCKED: Regression detected![/bold red]")
        raise typer.Exit(code=1)
    elif result.gate_decision == GateDecision.WARN:
        console.print("[bold yellow]⚠️ CI QUALITY GATE WARNING: Cost/Latency elevated.[/bold yellow]")
        raise typer.Exit(code=0)
    else:
        console.print("[bold green]✅ CI QUALITY GATE PASSED: Deployment approved.[/bold green]")
        raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
