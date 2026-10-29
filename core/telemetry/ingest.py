"""core/telemetry/ingest.py: OTLP Ingestion Service and payload parser."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from core.models.schema import AgentEvent, Span
from core.telemetry.normalizer import SpanNormalizer


class StreamChunkAggregator:
    """Aggregates streaming token chunks into unified, fully-grounded spans."""

    @staticmethod
    def is_stream_chunk(span: Span) -> bool:
        attrs = span.attributes
        name_lower = span.name.lower()
        kind = str(attrs.get("openinference.span.kind", "")).upper()
        return (
            "chunk" in name_lower
            or bool(attrs.get("llm.stream_id"))
            or bool(attrs.get("gen_ai.chunk"))
            or bool(attrs.get("stream_chunk"))
            or kind in ("LLM_CHUNK", "STREAM_CHUNK")
        )

    @classmethod
    def stitch_chunks(cls, spans: List[Span]) -> List[Span]:
        """Stitches streaming chunk spans sharing a stream_id or parent_span_id into unified spans."""
        stitched: List[Span] = []
        chunk_groups: Dict[str, List[Span]] = {}

        for span in spans:
            if cls.is_stream_chunk(span):
                attrs = span.attributes
                stream_key = (
                    attrs.get("llm.stream_id")
                    or attrs.get("stream.id")
                    or attrs.get("gen_ai.stream_id")
                    or (f"{span.trace_id}:{span.parent_span_id}" if span.parent_span_id else span.span_id)
                )
                chunk_groups.setdefault(str(stream_key), []).append(span)
            else:
                stitched.append(span)

        for stream_key, chunks in chunk_groups.items():
            if not chunks:
                continue
            chunks.sort(key=lambda c: c.start_time)
            first_chunk = chunks[0]
            last_chunk = chunks[-1]

            combined_texts = []
            total_tokens = 0
            for c in chunks:
                c_attrs = c.attributes
                chunk_text = (
                    c_attrs.get("output.value")
                    or c_attrs.get("llm.chunk_text")
                    or c_attrs.get("gen_ai.completion.chunk")
                    or ""
                )
                if chunk_text:
                    combined_texts.append(str(chunk_text))
                tokens = (
                    c_attrs.get("llm.token_count.completion")
                    or c_attrs.get("gen_ai.usage.completion_tokens")
                    or c_attrs.get("tokens")
                    or 0
                )
                if isinstance(tokens, (int, float)):
                    total_tokens += int(tokens)

            full_text = "".join(combined_texts)
            merged_attrs = dict(first_chunk.attributes)
            merged_attrs["openinference.span.kind"] = "LLM"
            merged_attrs["output.value"] = full_text
            if total_tokens > 0:
                merged_attrs["llm.token_count.total"] = total_tokens
                merged_attrs["gen_ai.usage.total_tokens"] = total_tokens
            merged_attrs["stream.chunk_count"] = len(chunks)

            clean_name = first_chunk.name.replace("_chunk", "").replace("chunk", "generation")
            stitched_span = Span(
                span_id=first_chunk.parent_span_id or first_chunk.span_id,
                trace_id=first_chunk.trace_id,
                parent_span_id=first_chunk.parent_span_id,
                name=clean_name if clean_name else "llm_generation",
                start_time=first_chunk.start_time,
                end_time=last_chunk.end_time,
                status_code="ERROR" if any(c.status_code == "ERROR" for c in chunks) else "OK",
                attributes=merged_attrs,
            )
            stitched.append(stitched_span)

        return sorted(stitched, key=lambda s: s.start_time)


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
        # Stitch streaming chunks into unified spans
        processed_spans = StreamChunkAggregator.stitch_chunks(spans)
        # Sort chronologically by start_time
        sorted_spans = sorted(processed_spans, key=lambda s: s.start_time)
        return [SpanNormalizer.normalize_span(s) for s in sorted_spans]
