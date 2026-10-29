"""tests/test_streaming.py: Verification of LLM token stream stitching."""

from datetime import datetime, timezone, timedelta
from core.models.schema import Span
from core.telemetry.ingest import StreamChunkAggregator, OTLPIngestService


class TestStreamChunkAggregator:
    """Verifies that fragmented token streams are stitched into single coherent spans and events."""

    def test_stitch_streaming_llm_chunks(self):
        now = datetime.now(timezone.utc)
        chunks = [
            Span(
                span_id="chunk_1",
                trace_id="trace_stream_1",
                parent_span_id="llm_generation_root",
                name="llm_chunk_1",
                start_time=now,
                end_time=now + timedelta(milliseconds=50),
                status_code="OK",
                attributes={
                    "llm.stream_id": "stream_xyz",
                    "output.value": "Hello ",
                    "llm.token_count.completion": 2,
                },
            ),
            Span(
                span_id="chunk_2",
                trace_id="trace_stream_1",
                parent_span_id="llm_generation_root",
                name="llm_chunk_2",
                start_time=now + timedelta(milliseconds=55),
                end_time=now + timedelta(milliseconds=110),
                status_code="OK",
                attributes={
                    "llm.stream_id": "stream_xyz",
                    "output.value": "World!",
                    "llm.token_count.completion": 3,
                },
            ),
        ]

        stitched = StreamChunkAggregator.stitch_chunks(chunks)
        assert len(stitched) == 1
        span = stitched[0]

        assert span.trace_id == "trace_stream_1"
        assert span.span_id == "llm_generation_root"
        assert span.attributes["output.value"] == "Hello World!"
        assert span.attributes["llm.token_count.total"] == 5
        assert span.attributes["stream.chunk_count"] == 2
        assert span.start_time == now
        assert span.end_time == now + timedelta(milliseconds=110)

        # Ensure OTLPIngestService normalizes it cleanly to REASONING
        events = OTLPIngestService.process_trace(chunks)
        assert len(events) == 1
        assert events[0].content == "Hello World!"

