"""tests/test_schemas.py: Unit tests for core data models and serialization."""

from datetime import datetime, timezone
from uuid import uuid4
import pytest
from core.models.schema import (
    EventType,
    FailureCategory,
    GateDecision,
    Span,
    ToolCall,
    MemoryEvent,
    AgentEvent,
    TrajectoryNode,
    TrajectoryEdge,
    Trajectory,
    Evaluation,
    Failure,
    RootCause,
    DatasetItem,
    Experiment,
    RegressionResult,
)


def test_span_model():
    now = datetime.now(timezone.utc)
    span = Span(
        span_id="span-123",
        trace_id="trace-abc",
        name="run_tool",
        start_time=now,
        end_time=now,
        status_code="OK",
        attributes={"openinference.span.kind": "TOOL", "tool.name": "calculator"},
    )
    assert span.span_id == "span-123"
    assert span.attributes["tool.name"] == "calculator"


def test_agent_event_and_tool_call():
    tc = ToolCall(
        tool_name="sql_query",
        input_args={"query": "SELECT 1"},
        output_result="1",
        execution_time_ms=12.5,
    )
    event = AgentEvent(
        trace_id="trace-abc",
        span_id="span-123",
        event_type=EventType.TOOL_CALL,
        tool_call=tc,
    )
    assert event.event_type == EventType.TOOL_CALL
    assert event.tool_call.tool_name == "sql_query"
    data = event.model_dump()
    assert data["trace_id"] == "trace-abc"


def test_trajectory_model():
    now = datetime.now(timezone.utc)
    n1 = TrajectoryNode(
        node_id="n1",
        event_id=uuid4(),
        event_type=EventType.PLAN,
        label="Generate Plan",
        timestamp=now,
        payload={"plan": ["step 1", "step 2"]},
    )
    n2 = TrajectoryNode(
        node_id="n2",
        event_id=uuid4(),
        event_type=EventType.TOOL_CALL,
        label="Execute Step 1",
        timestamp=now,
        payload={"tool": "search"},
    )
    edge = TrajectoryEdge(source_node_id="n1", target_node_id="n2", edge_type="call_parent")
    traj = Trajectory(
        trace_id="trace-abc",
        agent_id="test_agent",
        agent_version="1.0.0",
        nodes=[n1, n2],
        edges=[edge],
        total_latency_ms=150.0,
        total_tokens=320,
        total_cost_usd=0.0012,
    )
    assert len(traj.nodes) == 2
    assert len(traj.edges) == 1
    assert traj.total_tokens == 320


def test_evaluation_and_root_cause_models():
    traj_id = uuid4()
    ev = Evaluation(
        trace_id="trace-abc",
        trajectory_id=traj_id,
        target_node_id="n2",
        evaluator_name="schema_validator",
        evaluator_layer="deterministic",
        score=1.0,
        confidence=1.0,
        passed=True,
    )
    rc = RootCause(
        trajectory_id=traj_id,
        primary_failure_node_id="n2",
        primary_category=FailureCategory.TOOL,
        confidence_score=0.92,
        propagation_chain=["n2", "n3"],
        explanation="Root cause tool failure",
    )
    assert ev.passed is True
    assert rc.primary_category == FailureCategory.TOOL


def test_regression_result_model():
    res = RegressionResult(
        experiment_id=uuid4(),
        baseline_experiment_id=uuid4(),
        score_delta=0.15,
        cost_delta_usd=-0.002,
        latency_delta_ms=-25.0,
        new_failures_count=0,
        resolved_failures_count=2,
        gate_decision=GateDecision.PASS,
        summary_markdown="### Quality Gate PASS",
    )
    assert res.gate_decision == GateDecision.PASS
    assert res.score_delta == 0.15
