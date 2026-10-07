"""tests/test_evaluators.py: Tests for 4-layer Evaluators and Gated Pipeline."""

from datetime import datetime, timezone
import pytest
from core.evaluators.deterministic import DeterministicEvaluator
from core.evaluators.llm_judge import LLMJudgeEvaluator
from core.evaluators.pipeline import EvaluatorPipeline
from core.evaluators.semantic import SemanticEvaluator
from core.evaluators.trajectory_eval import TrajectoryGraphEvaluator
from core.models.schema import AgentEvent, EventType, ToolCall
from core.trajectory.builder import TrajectoryBuilder


@pytest.mark.asyncio
async def test_deterministic_evaluator_catches_tool_error():
    now = datetime.now(timezone.utc)
    ev = AgentEvent(
        trace_id="t-eval-1",
        span_id="s1",
        event_type=EventType.TOOL_CALL,
        timestamp=now,
        tool_call=ToolCall(
            tool_name="database_exec",
            is_error=True,
            error_message="Table 'users' does not exist",
        ),
    )
    traj = TrajectoryBuilder.build_trajectory([ev])
    evaluator = DeterministicEvaluator()

    res = await evaluator.evaluate_node(traj.nodes[0], traj)
    assert res is not None
    assert res.passed is False
    assert res.score == 0.0
    assert "Table 'users' does not exist" in res.rationale


@pytest.mark.asyncio
async def test_pipeline_short_circuits_llm_judge():
    now = datetime.now(timezone.utc)
    ev_broken_tool = AgentEvent(
        trace_id="t-eval-2",
        span_id="s1",
        event_type=EventType.TOOL_CALL,
        timestamp=now,
        tool_call=ToolCall(
            tool_name="faulty_api",
            is_error=True,
            error_message="500 Internal Server Error",
        ),
    )
    ev_outcome = AgentEvent(
        trace_id="t-eval-2",
        span_id="s2",
        event_type=EventType.FINAL_OUTCOME,
        timestamp=now,
        content="I failed to complete the task.",
    )
    traj = TrajectoryBuilder.build_trajectory([ev_broken_tool, ev_outcome])
    pipeline = EvaluatorPipeline()

    result = await pipeline.run(traj)
    assert result["fatal_short_circuit"] is True
    assert len(result["failures"]) >= 1

    # Node 0 had a fatal deterministic failure, so LLM judge should NOT have evaluated node 0!
    judge_node_evals = [
        ev
        for ev in result["evaluations"]
        if ev.target_node_id == traj.nodes[0].node_id and ev.evaluator_layer == "llm_judge"
    ]
    assert len(judge_node_evals) == 0
