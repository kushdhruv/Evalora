"""core/sdk/tracer.py: Real-time Agent Instrumentation SDK."""

import inspect
import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from core.models.schema import AgentEvent, EventType, Span, ToolCall, Trajectory
from core.trajectory.builder import TrajectoryBuilder


class AgentTracer:
    """Real-time tracer capturing real execution duration, real tool I/O, and real exceptions."""

    def __init__(self, agent_id: str = "production_agent", agent_version: str = "1.0.0"):
        self.agent_id = agent_id
        self.agent_version = agent_version
        self.trace_id = f"trace_{uuid4().hex[:12]}"
        self.spans: List[Span] = []
        self.events: List[AgentEvent] = []
        self.start_wall_time = time.perf_counter()

    def record_plan(self, plan_content: str, steps: List[str]):
        now = datetime.now(timezone.utc)
        span_id = f"span_plan_{uuid4().hex[:8]}"
        self.spans.append(
            Span(
                span_id=span_id,
                trace_id=self.trace_id,
                name="agent_planning",
                start_time=now,
                end_time=now,
                status_code="OK",
                attributes={"agent.step_type": "plan", "output.value": plan_content},
            )
        )
        self.events.append(
            AgentEvent(
                trace_id=self.trace_id,
                span_id=span_id,
                event_type=EventType.PLAN,
                timestamp=now,
                content=plan_content,
                metadata={"planned_steps": steps},
            )
        )

    def execute_tool(self, tool_name: str, tool_fn: Callable, **kwargs) -> Any:
        """Executes a real tool function, measuring real latency and capturing real exceptions."""
        span_id = f"span_tool_{uuid4().hex[:8]}"
        start_dt = datetime.now(timezone.utc)
        start_t = time.perf_counter()

        result = None
        is_error = False
        error_msg = None

        try:
            result = tool_fn(**kwargs)
        except Exception as e:
            is_error = True
            error_msg = f"{type(e).__name__}: {str(e)}"

        elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
        end_dt = datetime.now(timezone.utc)

        attrs = {
            "openinference.span.kind": "TOOL",
            "tool.name": tool_name,
            "tool.parameters": json.dumps(kwargs),
        }
        if is_error:
            attrs["error"] = True
            attrs["error.message"] = error_msg
        else:
            attrs["tool.output"] = str(result)

        self.spans.append(
            Span(
                span_id=span_id,
                trace_id=self.trace_id,
                name=f"tool_{tool_name}",
                start_time=start_dt,
                end_time=end_dt,
                status_code="ERROR" if is_error else "OK",
                attributes=attrs,
            )
        )

        self.events.append(
            AgentEvent(
                trace_id=self.trace_id,
                span_id=span_id,
                event_type=EventType.TOOL_CALL,
                timestamp=start_dt,
                tool_call=ToolCall(
                    tool_name=tool_name,
                    input_args=kwargs,
                    output_result=result if not is_error else None,
                    execution_time_ms=elapsed_ms,
                    is_error=is_error,
                    error_message=error_msg,
                ),
            )
        )

        if is_error:
            # Re-raise so agent logic can choose whether to catch or cascade
            raise RuntimeError(error_msg)

        return result

    def record_outcome(self, outcome_text: str, is_success: Optional[bool] = None):
        now = datetime.now(timezone.utc)
        span_id = f"span_outcome_{uuid4().hex[:8]}"
        self.spans.append(
            Span(
                span_id=span_id,
                trace_id=self.trace_id,
                name="agent_final_outcome",
                start_time=now,
                end_time=now,
                status_code="OK",
                attributes={"agent.step_type": "outcome", "output.value": outcome_text},
            )
        )
        self.events.append(
            AgentEvent(
                trace_id=self.trace_id,
                span_id=span_id,
                event_type=EventType.FINAL_OUTCOME,
                timestamp=now,
                content=outcome_text,
            )
        )

    def to_trajectory(self) -> Trajectory:
        """Compiles recorded events into a complete Trajectory DAG."""
        return TrajectoryBuilder.build_trajectory(
            events=self.events,
            raw_spans=self.spans,
            agent_id=self.agent_id,
            agent_version=self.agent_version,
        )

    def to_otlp_payload(self) -> Dict[str, Any]:
        """Exports standard OTLP JSON payload for HTTP ingestion."""
        raw_spans = []
        for s in self.spans:
            raw_spans.append(
                {
                    "traceId": s.trace_id,
                    "spanId": s.span_id,
                    "parentSpanId": s.parent_span_id,
                    "name": s.name,
                    "startTimeUnixNano": int(s.start_time.timestamp() * 1e9),
                    "endTimeUnixNano": int(s.end_time.timestamp() * 1e9),
                    "status": {"code": "ERROR" if s.status_code == "ERROR" else "OK"},
                    "attributes": [
                        {"key": k, "value": {"stringValue": str(v)}} for k, v in s.attributes.items()
                    ],
                }
            )
        return {"resourceSpans": [{"scopeSpans": [{"spans": raw_spans}]}]}


@contextmanager
def trace_agent_execution(agent_id: str = "agent", agent_version: str = "1.0.0"):
    tracer = AgentTracer(agent_id=agent_id, agent_version=agent_version)
    try:
        yield tracer
    finally:
        pass
