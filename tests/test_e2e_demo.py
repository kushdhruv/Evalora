"""tests/test_e2e_demo.py: End-to-end integration test asserting full platform pipeline."""

import pytest
from core.causal.analyzer import CausalFailureAnalyzer
from core.evaluators.pipeline import EvaluatorPipeline
from core.models.schema import FailureCategory, GateDecision
from core.regression.analyzer import RegressionAnalyzer
from core.regression.dataset import DatasetCurationService
from core.regression.runner import ExperimentRunner
from demo_agent.agent_v1 import run_agent_v1
from demo_agent.agent_v2 import run_agent_v2


@pytest.mark.asyncio
async def test_full_platform_pipeline_e2e():
    prompt = "Check the overdue balance for customer acct_982 and email the summary to their billing address."
    pipeline = EvaluatorPipeline()

    # 1. Run Flawed Agent V1
    traj_v1 = await run_agent_v1(prompt)
    assert len(traj_v1.nodes) == 4

    # 2. Evaluate V1
    eval_res_v1 = await pipeline.run(traj_v1)
    assert eval_res_v1["passed"] is False
    assert len(eval_res_v1["failures"]) >= 2

    # 3. Root Cause Isolation
    causal_analyzer = CausalFailureAnalyzer(traj_v1)
    root_cause = causal_analyzer.identify_root_cause(eval_res_v1["failures"])
    assert root_cause is not None
    assert root_cause.primary_failure_node_id == traj_v1.nodes[1].node_id
    assert root_cause.primary_category == FailureCategory.TOOL

    # 4. Curate to regression dataset
    item = DatasetCurationService.create_item_from_trajectory(
        trajectory=traj_v1,
        dataset_id="ci_regression_test_suite",
        custom_input_prompt=prompt,
    )
    assert item.dataset_id == "ci_regression_test_suite"

    # 5. Run Candidate Agent V2 on dataset
    runner = ExperimentRunner(pipeline=pipeline)
    candidate_exp = await runner.run_experiment(
        name="Candidate V2 Run",
        dataset_id="ci_regression_test_suite",
        dataset_items=[item],
        agent_callable=run_agent_v2,
        agent_version="2.0.0",
    )
    assert candidate_exp.passed_samples == 1
    assert candidate_exp.mean_score >= 0.85

    # 6. Baseline vs Candidate regression comparison
    baseline_exp = await runner.run_experiment(
        name="Baseline V1 Run",
        dataset_id="ci_regression_test_suite",
        dataset_items=[item],
        agent_callable=run_agent_v1,
        agent_version="1.0.0",
    )

    reg_result = RegressionAnalyzer.compare(candidate=candidate_exp, baseline=baseline_exp)
    assert reg_result.gate_decision == GateDecision.PASS
    assert reg_result.score_delta > 0.30
    assert reg_result.resolved_failures_count == 1
    assert reg_result.new_failures_count == 0
