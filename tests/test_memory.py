"""tests/test_memory.py: Tests for Long-Horizon Memory Telemetry Auditor."""

from datetime import datetime, timezone
from core.memory.auditor import MemoryTelemetryAuditor
from core.models.schema import AgentEvent, EventType, MemoryEvent, ToolCall
from core.trajectory.builder import TrajectoryBuilder


def test_memory_auditor_causal_usefulness():
    now = datetime.now(timezone.utc)
    ev_mem = AgentEvent(
        trace_id="t-mem-1",
        span_id="s1",
        event_type=EventType.MEMORY_READ,
        timestamp=now,
        memory_event=MemoryEvent(
            operation="query",
            query_text="user billing preference",
            retrieved_keys=["user_billing_pref"],
            retrieved_content=[{"currency": "EUR", "tax_id": "DE123456"}],
            similarity_scores=[0.92],
        ),
    )
    # Downstream tool DOES use "EUR"
    ev_tool = AgentEvent(
        trace_id="t-mem-1",
        span_id="s2",
        event_type=EventType.TOOL_CALL,
        timestamp=now,
        tool_call=ToolCall(
            tool_name="generate_invoice",
            input_args={"currency": "EUR", "amount": 250},
        ),
    )
    traj = TrajectoryBuilder.build_trajectory([ev_mem, ev_tool])
    audit = MemoryTelemetryAuditor.audit_trajectory(traj)

    assert audit.has_memory_events is True
    assert audit.retrieval_relevance_score >= 0.90
    assert audit.causal_usefulness_score > 0.50
    assert audit.passed is True


def test_memory_auditor_flags_ignored_memory():
    now = datetime.now(timezone.utc)
    ev_mem = AgentEvent(
        trace_id="t-mem-2",
        span_id="s1",
        event_type=EventType.MEMORY_READ,
        timestamp=now,
        memory_event=MemoryEvent(
            operation="query",
            query_text="user currency",
            retrieved_keys=["pref_currency"],
            retrieved_content=[{"currency": "JPY"}],
            similarity_scores=[0.88],
        ),
    )
    # Downstream tool completely ignores JPY and sends USD
    ev_tool = AgentEvent(
        trace_id="t-mem-2",
        span_id="s2",
        event_type=EventType.TOOL_CALL,
        timestamp=now,
        tool_call=ToolCall(
            tool_name="generate_invoice",
            input_args={"currency": "USD", "amount": 100},
        ),
    )
    traj = TrajectoryBuilder.build_trajectory([ev_mem, ev_tool])
    audit = MemoryTelemetryAuditor.audit_trajectory(traj)

    assert audit.has_memory_events is True
    assert audit.causal_usefulness_score == 0.0
    assert any("ignored by downstream tools" in f for f in audit.findings)
