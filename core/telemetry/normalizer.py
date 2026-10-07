"""core/telemetry/normalizer.py: Normalize heterogeneous spans into Canonical AgentEvents."""

import json
from typing import Any, Dict, Optional
from core.models.schema import (
    AgentEvent,
    EventType,
    MemoryEvent,
    Span,
    ToolCall,
)


class SpanNormalizer:
    """Normalizes OpenTelemetry / OpenInference spans into typed AgentEvents."""

    @staticmethod
    def normalize_span(span: Span) -> AgentEvent:
        attrs = span.attributes
        kind = attrs.get("openinference.span.kind", "").upper()
        genai_op = attrs.get("gen_ai.operation.name", "").lower()
        span_name = span.name.lower()

        event_type = EventType.REASONING
        tool_call: Optional[ToolCall] = None
        memory_event: Optional[MemoryEvent] = None
        content: Optional[str] = attrs.get("output.value") or attrs.get("llm.output_messages")

        # 1. Tool Call Detection
        if kind == "TOOL" or "tool" in span_name or "tool.name" in attrs:
            event_type = EventType.TOOL_CALL
            tool_name = attrs.get("tool.name") or span.name
            raw_input = attrs.get("tool.parameters") or attrs.get("input.value") or {}
            if isinstance(raw_input, str):
                try:
                    input_args = json.loads(raw_input)
                except Exception:
                    input_args = {"raw": raw_input}
            elif isinstance(raw_input, dict):
                input_args = raw_input
            else:
                input_args = {"value": raw_input}

            raw_output = attrs.get("tool.output") or attrs.get("output.value")
            is_err = span.status_code == "ERROR" or "error" in attrs
            err_msg = attrs.get("error.message") if is_err else None
            duration_ms = (span.end_time - span.start_time).total_seconds() * 1000.0

            tool_call = ToolCall(
                tool_name=tool_name,
                input_args=input_args,
                output_result=raw_output,
                execution_time_ms=max(0.0, duration_ms),
                is_error=is_err,
                error_message=err_msg,
            )

        # 2. Retriever / Memory Operation Detection
        elif kind == "RETRIEVER" or "memory" in span_name or "retriever" in span_name:
            operation = attrs.get("memory.operation", "query")
            if "write" in span_name or "store" in span_name or operation == "store":
                event_type = EventType.MEMORY_WRITE
            else:
                event_type = EventType.MEMORY_READ

            query_text = attrs.get("input.value") or attrs.get("query.text")
            retrieved_keys = attrs.get("retrieved.keys", [])
            retrieved_content = attrs.get("retrieved.content", [])
            sim_scores = attrs.get("retrieved.scores", [])
            duration_ms = (span.end_time - span.start_time).total_seconds() * 1000.0

            memory_event = MemoryEvent(
                operation=operation,
                query_text=str(query_text) if query_text else None,
                retrieved_keys=list(retrieved_keys) if isinstance(retrieved_keys, list) else [str(retrieved_keys)],
                retrieved_content=list(retrieved_content) if isinstance(retrieved_content, list) else [],
                similarity_scores=[float(s) for s in sim_scores] if isinstance(sim_scores, list) else [],
                latency_ms=max(0.0, duration_ms),
            )

        # 3. Planning Detection
        elif "plan" in span_name or attrs.get("agent.step_type") == "plan":
            event_type = EventType.PLAN

        # 4. Final Outcome Detection
        elif "outcome" in span_name or "final" in span_name or attrs.get("agent.step_type") == "outcome":
            event_type = EventType.FINAL_OUTCOME

        # 5. Observation Detection
        elif "observation" in span_name:
            event_type = EventType.OBSERVATION

        # 6. Default to Reasoning (LLM generation / chain step)
        else:
            event_type = EventType.REASONING

        return AgentEvent(
            trace_id=span.trace_id,
            span_id=span.span_id,
            event_type=event_type,
            timestamp=span.start_time,
            content=str(content) if content is not None else None,
            tool_call=tool_call,
            memory_event=memory_event,
            metadata=attrs,
        )
