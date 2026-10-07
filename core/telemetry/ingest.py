"""core/telemetry/ingest.py: OTLP Ingestion Service and payload parser."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from core.models.schema import AgentEvent, Span
from core.telemetry.normalizer import SpanNormalizer


class OTLPIngestService:
    """Parses standard OTLP JSON trace payloads into Spans and AgentEvents."""

    @staticmethod
    def _parse_time(timestamp_val: Any) -> datetime:
        if isinstance(timestamp_val, (int, float)):
            # Nanoseconds (OTel default) or seconds
            if timestamp_val > 1e15:
                return datetime.fromtimestamp(timestamp_val / 1e9, tz=timezone.utc)
            return datetime.fromtimestamp(timestamp_val, tz=timezone.utc)
        elif isinstance(timestamp_val, str):
            try:
                return datetime.fromisoformat(timestamp_val.replace("Z", "+00:00"))
            except Exception:
                pass
        return datetime.now(timezone.utc)

    @classmethod
    def parse_otlp_json(cls, payload: Dict[str, Any]) -> List[Span]:
        spans: List[Span] = []
        resource_spans = payload.get("resourceSpans", [])

        for r_span in resource_spans:
            scope_spans = r_span.get("scopeSpans", [])
            for s_span in scope_spans:
                for raw in s_span.get("spans", []):
                    span_id = raw.get("spanId") or raw.get("span_id", "")
                    trace_id = raw.get("traceId") or raw.get("trace_id", "")
                    parent_span_id = raw.get("parentSpanId") or raw.get("parent_span_id")
                    name = raw.get("name", "unnamed_span")
                    start_time = cls._parse_time(raw.get("startTimeUnixNano", raw.get("start_time")))
                    end_time = cls._parse_time(raw.get("endTimeUnixNano", raw.get("end_time")))

                    status = raw.get("status", {})
                    status_code = status.get("code", "OK")
                    if status_code in (2, "STATUS_CODE_ERROR", "ERROR"):
                        status_code = "ERROR"
                    else:
                        status_code = "OK"

                    attributes: Dict[str, Any] = {}
                    raw_attrs = raw.get("attributes", [])
                    if isinstance(raw_attrs, list):
                        for attr in raw_attrs:
                            key = attr.get("key")
                            val = attr.get("value", {})
                            if key:
                                # OTel value envelope
                                parsed_val = (
                                    val.get("stringValue")
                                    or val.get("intValue")
                                    or val.get("boolValue")
                                    or val.get("doubleValue")
                                    or val
                                )
                                attributes[key] = parsed_val
                    elif isinstance(raw_attrs, dict):
                        attributes = raw_attrs

                    spans.append(
                        Span(
                            span_id=span_id,
                            trace_id=trace_id,
                            parent_span_id=parent_span_id,
                            name=name,
                            start_time=start_time,
                            end_time=end_time,
                            status_code=status_code,
                            attributes=attributes,
                        )
                    )
        return spans

    @classmethod
    def process_trace(cls, spans: List[Span]) -> List[AgentEvent]:
        # Sort chronologically by start_time
        sorted_spans = sorted(spans, key=lambda s: s.start_time)
        return [SpanNormalizer.normalize_span(s) for s in sorted_spans]
