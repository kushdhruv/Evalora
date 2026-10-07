"""tests/test_regression.py: Tests for Dataset curation, Experiment runner, and Regression gating."""

from datetime import datetime, timezone
from uuid import uuid4
import pytest
from core.models.schema import (
    AgentEvent,
    EventType,
    Experiment,
    GateDecision,
    ToolCall,
    Trajectory,
)
from core.regression.analyzer import RegressionAnalyzer
from core.regression.dataset import DatasetCurationService
from core.regression.runner import ExperimentRunner
from core.trajectory.builder import TrajectoryBuilder


def test_dataset_curation_from_trajectory():
    now = datetime.now(timezone.utc)
    ev_plan = AgentEvent(
        trace_id="t-curate-1",
        span_id="s1",
        event_type=EventType.PLAN,
        timestamp=now,
        content="Plan for user task",
    )
    ev_tool = AgentEvent(
        trace_id="t-curate-1",
        span_id="s2",
        event_type=EventType.TOOL_CALL,
        timestamp=now,
        tool_call=ToolCall(tool_name="calculator", input_args={"expr": "2+2"}),
    )
    ev_out = AgentEvent(
        trace_id="t-curate-1",
        span_id="s3",
        event_type=EventType.FINAL_OUTCOME,
        timestamp=now,
        content="Result is 4",
    )
    traj = TrajectoryBuilder.build_trajectory([ev_plan, ev_tool, ev_out])

    item = DatasetCurationService.create_item_from_trajectory(
        trajectory=traj,
        dataset_id="math_tasks",
    )
    assert item.dataset_id == "math_tasks"
    assert item.source_trace_id == "t-curate-1"
    assert "calculator" in item.assertions["expected_tools"]
    assert item.expected_outcome == "Result is 4"


@pytest.mark.asyncio
async def test_experiment_runner_and_regression_gate():
    item = DatasetCurationService.create_item_from_trajectory(
        trajectory=Trajectory(trace_id="dummy", agent_id="dummy"),
        dataset_id="math_suite",
        custom_input_prompt="Calculate 10+20",
    )

    # Mock agent callable that produces high-scoring trajectory
    async def mock_candidate_agent(prompt: str) -> Trajectory:
        now = datetime.now(timezone.utc)
        ev1 = AgentEvent(
            trace_id="t-run-1",
            span_id="s1",
            event_type=EventType.TOOL_CALL,
            timestamp=now,
            tool_call=ToolCall(
                tool_name="calculator",
                input_args={"expr": "10+20"},
                output_result="30",
            ),
        )
        ev2 = AgentEvent(
            trace_id="t-run-1",
            span_id="s2",
            event_type=EventType.FINAL_OUTCOME,
            timestamp=now,
            content="The answer is 30.",
        )
        return TrajectoryBuilder.build_trajectory([ev1, ev2])

    runner = ExperimentRunner()
    candidate_exp = await runner.run_experiment(
        name="Candidate Run",
        dataset_id="math_suite",
        dataset_items=[item],
        agent_callable=mock_candidate_agent,
        agent_version="2.0.0",
    )
    assert candidate_exp.passed_samples == 1
    assert candidate_exp.mean_score >= 0.80

    # Create baseline experiment with lower score
    baseline_exp = Experiment(
        experiment_id=uuid4(),
        name="Baseline Run",
        dataset_id="math_suite",
        agent_id="test_agent",
        agent_version="1.0.0",
        total_samples=1,
        passed_samples=0,
        mean_score=0.40,
        mean_cost_usd=0.005,
        mean_latency_ms=250.0,
    )

    # Compare
    reg_result = RegressionAnalyzer.compare(candidate=candidate_exp, baseline=baseline_exp)
    assert reg_result.gate_decision == GateDecision.PASS
    assert reg_result.score_delta > 0.30
    assert reg_result.resolved_failures_count == 1
    assert "Agent CI/CD Quality Gate: PASS" in reg_result.summary_markdown


def test_regression_analyzer_blocks_on_degradation():
    baseline_exp = Experiment(
        name="Baseline",
        dataset_id="set_1",
        agent_id="agent",
        agent_version="1.0",
        total_samples=5,
        passed_samples=5,
        mean_score=0.92,
        mean_cost_usd=0.01,
        mean_latency_ms=100.0,
    )
    degraded_candidate = Experiment(
        name="Degraded Candidate",
        dataset_id="set_1",
        agent_id="agent",
        agent_version="1.1",
        total_samples=5,
        passed_samples=3,  # 2 new failures!
        mean_score=0.70,   # Score dropped!
        mean_cost_usd=0.01,
        mean_latency_ms=110.0,
    )

    res = RegressionAnalyzer.compare(candidate=degraded_candidate, baseline=baseline_exp)
    assert res.gate_decision == GateDecision.BLOCK
    assert res.new_failures_count == 2
    assert res.score_delta < -0.10
