"""tests/test_trajectory.py: Tests for Trajectory reconstruction and graph operations."""

from datetime import datetime, timezone
from core.models.schema import AgentEvent, EventType, Span, ToolCall
from core.trajectory.builder import TrajectoryBuilder
from core.trajectory.graph import TrajectoryGraphService


def test_trajectory_builder_and_data_flow():
    now = datetime.now(timezone.utc)
    ev1 = AgentEvent(
        trace_id="t-1",
        span_id="s1",
        event_type=EventType.TOOL_CALL,
        timestamp=now,
        tool_call=ToolCall(
            tool_name="get_account_id",
            input_args={"username": "alice"},
            output_result="acct_8849",
            execution_time_ms=50.0,
        ),
    )
    ev2 = AgentEvent(
        trace_id="t-1",
        span_id="s2",
        event_type=EventType.TOOL_CALL,
        timestamp=now,
        tool_call=ToolCall(
            tool_name="fetch_balance",
            input_args={"account_id": "acct_8849"},
            output_result="1500.00",
            execution_time_ms=80.0,
        ),
    )
    ev3 = AgentEvent(
        trace_id="t-1",
        span_id="s3",
        event_type=EventType.FINAL_OUTCOME,
        timestamp=now,
        content="Alice has a balance of $1500.00",
    )

    trajectory = TrajectoryBuilder.build_trajectory([ev1, ev2, ev3])
    assert len(trajectory.nodes) == 3
    assert trajectory.total_latency_ms == 130.0

    # Verify data-flow edge detection: ev2 referenced output "acct_8849" from ev1!
    data_edges = [e for e in trajectory.edges if e.edge_type == "data_dependency"]
    assert len(data_edges) >= 1
    assert data_edges[0].source_node_id == trajectory.nodes[0].node_id
    assert data_edges[0].target_node_id == trajectory.nodes[1].node_id


def test_trajectory_graph_service_networkx():
    now = datetime.now(timezone.utc)
    ev1 = AgentEvent(trace_id="t-2", span_id="s1", event_type=EventType.PLAN, timestamp=now)
    ev2 = AgentEvent(trace_id="t-2", span_id="s2", event_type=EventType.TOOL_CALL, timestamp=now)
    ev3 = AgentEvent(trace_id="t-2", span_id="s3", event_type=EventType.FINAL_OUTCOME, timestamp=now)

    raw_spans = [
        Span(span_id="s1", trace_id="t-2", name="plan", start_time=now, end_time=now),
        Span(span_id="s2", trace_id="t-2", parent_span_id="s1", name="tool", start_time=now, end_time=now),
        Span(span_id="s3", trace_id="t-2", parent_span_id="s1", name="outcome", start_time=now, end_time=now),
    ]

    trajectory = TrajectoryBuilder.build_trajectory([ev1, ev2, ev3], raw_spans=raw_spans)
    g = TrajectoryGraphService.to_networkx(trajectory)

    order = TrajectoryGraphService.get_topological_order(g)
    assert len(order) == 3
    assert order[0] == trajectory.nodes[0].node_id

    ancestors = TrajectoryGraphService.find_ancestors(g, trajectory.nodes[2].node_id)
    assert len(ancestors) >= 1

    path = TrajectoryGraphService.find_shortest_causal_path(
        g, trajectory.nodes[0].node_id, trajectory.nodes[2].node_id
    )
    assert len(path) >= 2
