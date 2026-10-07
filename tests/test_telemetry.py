"""tests/test_telemetry.py: Tests for OTLP Ingestion and Span Normalization."""

from datetime import datetime, timezone
from core.models.schema import EventType, Span
from core.telemetry.ingest import OTLPIngestService
from core.telemetry.normalizer import SpanNormalizer


def test_span_normalizer_tool():
    now = datetime.now(timezone.utc)
    span = Span(
        span_id="s1",
        trace_id="t1",
        name="execute_sql",
        start_time=now,
        end_time=now,
        status_code="OK",
        attributes={
            "openinference.span.kind": "TOOL",
            "tool.name": "sql_query",
            "tool.parameters": '{"query": "SELECT * FROM users"}',
            "tool.output": '[{"id": 1}]',
        },
    )
    event = SpanNormalizer.normalize_span(span)
    assert event.event_type == EventType.TOOL_CALL
    assert event.tool_call is not None
    assert event.tool_call.tool_name == "sql_query"
    assert event.tool_call.input_args["query"] == "SELECT * FROM users"
    assert event.tool_call.output_result == '[{"id": 1}]'
    assert event.tool_call.is_error is False


def test_span_normalizer_retriever_memory():
    now = datetime.now(timezone.utc)
    span = Span(
        span_id="s2",
        trace_id="t1",
        name="retrieve_context",
        start_time=now,
        end_time=now,
        attributes={
            "openinference.span.kind": "RETRIEVER",
            "input.value": "user account preferences",
            "retrieved.keys": ["pref_1", "pref_2"],
            "retrieved.scores": [0.89, 0.74],
        },
    )
    event = SpanNormalizer.normalize_span(span)
    assert event.event_type == EventType.MEMORY_READ
    assert event.memory_event is not None
    assert event.memory_event.query_text == "user account preferences"
    assert event.memory_event.retrieved_keys == ["pref_1", "pref_2"]
    assert event.memory_event.similarity_scores == [0.89, 0.74]


def test_otlp_json_payload_ingest():
    payload = {
        "resourceSpans": [
            {
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "trace-999",
                                "spanId": "span-001",
                                "name": "agent_plan",
                                "startTimeUnixNano": 1710000000000000000,
                                "endTimeUnixNano": 1710000000500000000,
                                "attributes": [
                                    {"key": "agent.step_type", "value": {"stringValue": "plan"}}
                                ],
                            },
                            {
                                "traceId": "trace-999",
                                "spanId": "span-002",
                                "name": "tool_database",
                                "startTimeUnixNano": 1710000001000000000,
                                "endTimeUnixNano": 1710000001500000000,
                                "attributes": [
                                    {"key": "openinference.span.kind", "value": {"stringValue": "TOOL"}},
                                    {"key": "tool.name", "value": {"stringValue": "database"}},
                                ],
                            },
                        ]
                    }
                ]
            }
        ]
    }
    spans = OTLPIngestService.parse_otlp_json(payload)
    assert len(spans) == 2
    assert spans[0].trace_id == "trace-999"

    events = OTLPIngestService.process_trace(spans)
    assert len(events) == 2
    assert events[0].event_type == EventType.PLAN
    assert events[1].event_type == EventType.TOOL_CALL
