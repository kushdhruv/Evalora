"""core/trajectory/builder.py: Reconstructs Trajectory DAG from AgentEvents."""

import json
from typing import Any, Dict, List, Optional
from uuid import uuid4
from core.models.schema import (
    AgentEvent,
    EventType,
    Span,
    Trajectory,
    TrajectoryEdge,
    TrajectoryNode,
)


class TrajectoryBuilder:
    """Builds a Trajectory with explicit invocation, sequence, and data-flow edges."""

    @classmethod
    def build_trajectory(
        cls,
        events: List[AgentEvent],
        raw_spans: Optional[List[Span]] = None,
        agent_id: str = "agent_under_test",
        agent_version: str = "1.0.0",
    ) -> Trajectory:
        if not events:
            return Trajectory(trace_id="empty", agent_id=agent_id, agent_version=agent_version)

        trace_id = events[0].trace_id
        nodes: List[TrajectoryNode] = []
        edges: List[TrajectoryEdge] = []
        span_to_node_id: Dict[str, str] = {}
        node_outputs: Dict[str, str] = {}

        total_latency_ms = 0.0
        total_tokens = 0
        total_cost_usd = 0.0
        is_success = True

        # 1. Build Nodes
        for idx, ev in enumerate(events):
            node_id = f"node_{idx+1}_{ev.event_type.value}"
            span_to_node_id[ev.span_id] = node_id

            label = f"{ev.event_type.value.upper()}"
            if ev.tool_call:
                label = f"Tool: {ev.tool_call.tool_name}"
                total_latency_ms += ev.tool_call.execution_time_ms
                if ev.tool_call.is_error:
                    is_success = False
                if ev.tool_call.output_result is not None:
                    node_outputs[node_id] = str(ev.tool_call.output_result)
            elif ev.content:
                label = f"{ev.event_type.value.capitalize()}"
                node_outputs[node_id] = ev.content
            elif ev.memory_event:
                label = f"Memory: {ev.memory_event.operation}"
                total_latency_ms += ev.memory_event.latency_ms

            # Estimate tokens / cost if attributes present
            meta = ev.metadata or {}
            tokens = meta.get("llm.token_count.total") or meta.get("gen_ai.usage.total_tokens") or 0
            if isinstance(tokens, int):
                total_tokens += tokens
                # Standard approximation $0.002 per 1k tokens
                total_cost_usd += (tokens / 1000.0) * 0.002

            payload: Dict[str, Any] = {
                "event_type": ev.event_type.value,
                "content": ev.content,
                "span_id": ev.span_id,
            }
            if ev.tool_call:
                payload["tool_call"] = ev.tool_call.model_dump()
            if ev.memory_event:
                payload["memory_event"] = ev.memory_event.model_dump()

            nodes.append(
                TrajectoryNode(
                    node_id=node_id,
                    event_id=ev.event_id,
                    event_type=ev.event_type,
                    label=label,
                    timestamp=ev.timestamp,
                    payload=payload,
                )
            )

        # 2. Build Chronological Sequence Edges
        for i in range(len(nodes) - 1):
            edges.append(
                TrajectoryEdge(
                    source_node_id=nodes[i].node_id,
                    target_node_id=nodes[i + 1].node_id,
                    edge_type="temporal_sequence",
                )
            )

        # 3. Build Invocation Edges from Raw Spans (if available)
        if raw_spans:
            for s in raw_spans:
                if s.parent_span_id and s.parent_span_id in span_to_node_id and s.span_id in span_to_node_id:
                    parent_node = span_to_node_id[s.parent_span_id]
                    child_node = span_to_node_id[s.span_id]
                    if parent_node != child_node:
                        edges.append(
                            TrajectoryEdge(
                                source_node_id=parent_node,
                                target_node_id=child_node,
                                edge_type="call_parent",
                            )
                        )

        # 4. Build Causal Data-Flow Edges
        # If node B's tool inputs or content references strings/data from node A's output
        for i, target_node in enumerate(nodes):
            target_payload = target_node.payload
            target_text = ""
            if "tool_call" in target_payload:
                target_text = json.dumps(target_payload["tool_call"].get("input_args", {}))
            elif target_payload.get("content"):
                target_text = str(target_payload["content"])

            for j in range(i):
                source_node = nodes[j]
                source_out = node_outputs.get(source_node.node_id, "")
                if source_out and len(source_out) >= 4 and source_out in target_text:
                    edges.append(
                        TrajectoryEdge(
                            source_node_id=source_node.node_id,
                            target_node_id=target_node.node_id,
                            edge_type="data_dependency",
                            metadata={"matched_substring": source_out[:30]},
                        )
                    )

        return Trajectory(
            trace_id=trace_id,
            agent_id=agent_id,
            agent_version=agent_version,
            nodes=nodes,
            edges=edges,
            total_latency_ms=round(total_latency_ms, 2),
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost_usd, 6),
            is_success=is_success,
        )
