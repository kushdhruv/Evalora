"""demo_agent/run_demo.py: End-to-end working demonstration of the platform."""

import asyncio
import os
import sys
from uuid import uuid4

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from core.causal.analyzer import CausalFailureAnalyzer
from core.db.repository import default_repository
from core.evaluators.pipeline import EvaluatorPipeline
from core.memory.auditor import MemoryTelemetryAuditor
from core.models.schema import Experiment, GateDecision
from core.regression.analyzer import RegressionAnalyzer
from core.regression.dataset import DatasetCurationService
from core.regression.runner import ExperimentRunner
from demo_agent.agent_v1 import run_agent_v1
from demo_agent.agent_v2 import run_agent_v2


async def main():
    print("=" * 70)
    print("[RUNNING END-TO-END AGENT EVALUATION & CAUSAL REGRESSION DEMO]")
    print("=" * 70)

    prompt = "Check the overdue balance for customer acct_982 and email the summary to their billing address."
    pipeline = EvaluatorPipeline()

    # -------------------------------------------------------------
    # Step 1: Execute Flawed Production Agent (Agent V1)
    # -------------------------------------------------------------
    print("\n[Step 1] Executing Production Agent (V1)...")
    traj_v1 = await run_agent_v1(prompt)
    default_repository.save_trajectory(traj_v1)
    print(f"  * Trace ID: {traj_v1.trace_id}")
    print(f"  * Nodes in DAG: {len(traj_v1.nodes)}")
    print(f"  * Edges in DAG: {len(traj_v1.edges)}")

    # -------------------------------------------------------------
    # Step 2: Run 4-Layer Evaluators on Agent V1
    # -------------------------------------------------------------
    print("\n[Step 2] Running Gated 4-Layer Evaluator Pipeline on V1...")
    eval_res_v1 = await pipeline.run(traj_v1)
    default_repository.save_evaluations(traj_v1.trace_id, eval_res_v1["evaluations"])
    default_repository.save_failures(traj_v1.trace_id, eval_res_v1["failures"])
    print(f"  * Mean Score: {eval_res_v1['mean_score']:.2f}")
    print(f"  * Overall Passed: {eval_res_v1['passed']}")
    print(f"  * Failures Detected: {len(eval_res_v1['failures'])}")

    # -------------------------------------------------------------
    # Step 3: Isolate Primary Root Cause vs Downstream Symptoms
    # -------------------------------------------------------------
    print("\n[Step 3] Running Causal Failure Analyzer & Root-Cause Discovery...")
    causal_analyzer = CausalFailureAnalyzer(traj_v1)
    root_cause = causal_analyzer.identify_root_cause(eval_res_v1["failures"])
    if root_cause:
        default_repository.save_root_cause(traj_v1.trace_id, root_cause)
        print(f"  [!] PRIMARY ROOT CAUSE ISOLATED: Node '{root_cause.primary_failure_node_id}'")
        print(f"     Category: {root_cause.primary_category.value}")
        print(f"     Confidence: {root_cause.confidence_score*100:.1f}%")
        print(f"     Propagation Chain: {' -> '.join(root_cause.propagation_chain)}")
        print(f"     Diagnostic: {root_cause.explanation}")

    # -------------------------------------------------------------
    # Step 4: Curate Failing Trace into Golden Regression Dataset Item
    # -------------------------------------------------------------
    print("\n[Step 4] Curating Failing Production Trace into Regression Test Item...")
    dataset_item = DatasetCurationService.create_item_from_trajectory(
        trajectory=traj_v1,
        dataset_id="billing_cascades_suite",
        custom_input_prompt=prompt,
        expected_outcome="The overdue balance of $450.00 has been verified and emailed to billing@acct982.corp.",
    )
    default_repository.save_dataset_item(dataset_item)
    print(f"  * Test Item ID: {dataset_item.item_id}")
    print(f"  * Dataset: {dataset_item.dataset_id}")
    print(f"  * Assertions Inferred: {dataset_item.assertions}")

    # -------------------------------------------------------------
    # Step 5: Run Candidate Agent V2 across Dataset
    # -------------------------------------------------------------
    print("\n[Step 5] Running Fixed Candidate Agent (V2) on Regression Dataset...")
    runner = ExperimentRunner(pipeline=pipeline)
    candidate_exp = await runner.run_experiment(
        name="Candidate V2 Regression Run",
        dataset_id="billing_cascades_suite",
        dataset_items=[dataset_item],
        agent_callable=run_agent_v2,
        agent_id="billing_support_agent",
        agent_version="2.0.0",
    )
    print(f"  * V2 Mean Score: {candidate_exp.mean_score:.2f}")
    print(f"  * V2 Pass Rate: {candidate_exp.passed_samples}/{candidate_exp.total_samples}")

    # -------------------------------------------------------------
    # Step 6: Create Baseline Experiment Record for V1
    # -------------------------------------------------------------
    baseline_exp = Experiment(
        experiment_id=uuid4(),
        name="Baseline V1 Run",
        dataset_id="billing_cascades_suite",
        agent_id="billing_support_agent",
        agent_version="1.0.0",
        total_samples=1,
        passed_samples=0,
        mean_score=eval_res_v1["mean_score"],
        mean_cost_usd=traj_v1.total_cost_usd,
        mean_latency_ms=traj_v1.total_latency_ms,
    )

    # -------------------------------------------------------------
    # Step 7: Compare Experiments & Evaluate CI/CD Quality Gate
    # -------------------------------------------------------------
    print("\n[Step 7] Evaluating CI/CD Quality Gate Decision (V1 vs V2)...")
    regression_res = RegressionAnalyzer.compare(
        candidate=candidate_exp,
        baseline=baseline_exp,
    )
    print(regression_res.summary_markdown)

    assert regression_res.gate_decision == GateDecision.PASS
    print("\n[SUCCESS] Candidate Agent V2 PASSED all CI quality gates and resolved root cause!")


if __name__ == "__main__":
    asyncio.run(main())
