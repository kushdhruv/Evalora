"""tests/test_storage.py: Tests for storage repository and health summary."""

from datetime import datetime, timezone
from uuid import uuid4
from core.db.repository import MemoryRepository
from core.models.schema import (
    AgentEvent,
    EventType,
    Failure,
    FailureCategory,
    ToolCall,
)
from core.trajectory.builder import TrajectoryBuilder


def test_repository_health_summary():
    repo = MemoryRepository()
    now = datetime.now(timezone.utc)

    # Add trajectory 1 (Successful)
    ev1 = AgentEvent(
        trace_id="t1",
        span_id="s1",
        event_type=EventType.TOOL_CALL,
        timestamp=now,
        tool_call=ToolCall(tool_name="web_search", execution_time_ms=120.0),
    )
    t1 = TrajectoryBuilder.build_trajectory([ev1])
    repo.save_trajectory(t1)

    # Add trajectory 2 (Failed tool)
    ev2 = AgentEvent(
        trace_id="t2",
        span_id="s2",
        event_type=EventType.TOOL_CALL,
        timestamp=now,
        tool_call=ToolCall(tool_name="database", is_error=True, execution_time_ms=50.0),
    )
    t2 = TrajectoryBuilder.build_trajectory([ev2])
    repo.save_trajectory(t2)
    repo.save_failures(
        "t2",
        [
            Failure(
                trajectory_id=t2.trajectory_id,
                node_id=t2.nodes[0].node_id,
                category=FailureCategory.TOOL,
                subcategory="syntax_error",
                description="Database error",
            )
        ],
    )

    summary = repo.get_health_summary()
    assert summary["total_trajectories"] == 2
    assert summary["success_rate"] == 0.50
    assert summary["tool_usage_counts"]["web_search"] == 1
    assert summary["tool_usage_counts"]["database"] == 1
    assert summary["failure_category_counts"]["tool"] == 1
