"""tests/test_causal.py: Tests for Causal Failure Attribution and Root Cause Analysis."""

from datetime import datetime, timezone
from core.causal.analyzer import CausalFailureAnalyzer
from core.models.schema import (
    AgentEvent,
    EventType,
    Failure,
    FailureCategory,
    ToolCall,
)
from core.trajectory.builder import TrajectoryBuilder


def test_causal_failure_cascade_attribution():
    now = datetime.now(timezone.utc)
    ev_plan = AgentEvent(
        trace_id="t-causal-1", span_id="s1", event_type=EventType.PLAN, timestamp=now
    )
    ev_sql = AgentEvent(
        trace_id="t-causal-1",
        span_id="s2",
        event_type=EventType.TOOL_CALL,
        timestamp=now,
        tool_call=ToolCall(
            tool_name="sqlite",
            is_error=True,
            error_message="no such column: email_address",
        ),
    )
    ev_email = AgentEvent(
        trace_id="t-causal-1",
        span_id="s3",
        event_type=EventType.TOOL_CALL,
        timestamp=now,
        tool_call=ToolCall(
            tool_name="mailer",
            is_error=True,
            error_message="missing recipient",
        ),
    )
    ev_outcome = AgentEvent(
        trace_id="t-causal-1",
        span_id="s4",
        event_type=EventType.FINAL_OUTCOME,
        timestamp=now,
        content="I failed to send the email.",
    )

    traj = TrajectoryBuilder.build_trajectory([ev_plan, ev_sql, ev_email, ev_outcome])

    # Simulate failures recorded along the path
    failures = [
        Failure(
            trajectory_id=traj.trajectory_id,
            node_id=traj.nodes[1].node_id,  # ev_sql
            category=FailureCategory.TOOL,
            subcategory="argument_schema_hallucination",
            severity="FATAL",
            description="Database syntax error: column not found",
            is_terminal=False,
        ),
        Failure(
            trajectory_id=traj.trajectory_id,
            node_id=traj.nodes[2].node_id,  # ev_email
            category=FailureCategory.TOOL,
            subcategory="missing_recipient",
            severity="DEGRADED",
            description="Email called without recipient",
            is_terminal=False,
        ),
        Failure(
            trajectory_id=traj.trajectory_id,
            node_id=traj.nodes[3].node_id,  # ev_outcome
            category=FailureCategory.OUTCOME,
            subcategory="incomplete_task",
            severity="FATAL",
            description="Goal was not achieved",
            is_terminal=True,
        ),
    ]

    analyzer = CausalFailureAnalyzer(traj)
    root_cause = analyzer.identify_root_cause(failures)

    assert root_cause is not None
    # Crucial test: Root cause MUST be the SQL node (node 1), NOT the final email node or outcome!
    assert root_cause.primary_failure_node_id == traj.nodes[1].node_id
    assert root_cause.primary_category == FailureCategory.TOOL
    assert root_cause.confidence_score > 0.80
    assert len(root_cause.propagation_chain) >= 2
    assert traj.nodes[1].node_id in root_cause.propagation_chain
    assert traj.nodes[3].node_id in root_cause.propagation_chain
