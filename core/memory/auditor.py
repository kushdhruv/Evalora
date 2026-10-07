"""core/memory/auditor.py: In-situ Memory Telemetry Auditor inspired by AMA-Bench."""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from core.models.schema import EventType, Trajectory


class MemoryAuditResult(BaseModel):
    has_memory_events: bool
    retrieval_relevance_score: float = Field(ge=0.0, le=1.0, default=1.0)
    prompt_retention_score: float = Field(ge=0.0, le=1.0, default=1.0)
    causal_usefulness_score: float = Field(ge=0.0, le=1.0, default=1.0)
    staleness_detected: bool = False
    findings: List[str] = Field(default_factory=list)
    passed: bool = True


class MemoryTelemetryAuditor:
    """Audits live memory telemetry across relevance, retention, staleness, and causal usefulness."""

    @classmethod
    def audit_trajectory(cls, trajectory: Trajectory) -> MemoryAuditResult:
        memory_nodes = [
            n for n in trajectory.nodes if n.event_type in (EventType.MEMORY_READ, EventType.MEMORY_WRITE)
        ]
        if not memory_nodes:
            return MemoryAuditResult(
                has_memory_events=False,
                findings=["No memory events present in this trajectory."],
            )

        findings: List[str] = []
        retrieval_scores: List[float] = []
        retention_scores: List[float] = []
        usefulness_scores: List[float] = []
        staleness_detected = False

        # Gather subsequent tools and content
        subsequent_tool_args: List[str] = []
        subsequent_content: List[str] = []

        for node in trajectory.nodes:
            if node.event_type == EventType.TOOL_CALL:
                subsequent_tool_args.append(
                    json.dumps(node.payload.get("tool_call", {}).get("input_args", {}))
                )
            elif node.payload.get("content"):
                subsequent_content.append(str(node.payload["content"]))

        combined_subsequent_text = " ".join(subsequent_tool_args + subsequent_content).lower()

        # Audit each read event
        for m_node in memory_nodes:
            mem_data = m_node.payload.get("memory_event", {})
            if mem_data.get("operation") in ("query", "read"):
                # 1. Retrieval Relevance
                sim_scores = mem_data.get("similarity_scores", [])
                if sim_scores:
                    avg_sim = sum(sim_scores) / len(sim_scores)
                    retrieval_scores.append(avg_sim)
                    if avg_sim < 0.60:
                        findings.append(f"Low retrieval relevance ({avg_sim:.2f}) at node '{m_node.node_id}'.")
                else:
                    retrieval_scores.append(0.85)

                # 2. Causal Downstream Usefulness & Retention
                retrieved_keys = mem_data.get("retrieved_keys", [])
                retrieved_content = mem_data.get("retrieved_content", [])

                # Check if retrieved entity values appear in subsequent actions
                used_count = 0
                for item in retrieved_content:
                    if isinstance(item, dict):
                        # Extract the actual values (e.g. "JPY", "EUR", "DE123456")
                        values_to_check = [str(v).lower() for v in item.values() if len(str(v)) >= 2]
                    else:
                        values_to_check = [str(item).lower()]

                    if any(val in combined_subsequent_text for val in values_to_check):
                        used_count += 1

                total_items = max(1, len(retrieved_content))
                use_ratio = used_count / total_items if retrieved_content else 1.0
                usefulness_scores.append(use_ratio)
                retention_scores.append(min(1.0, use_ratio + 0.2))

                if use_ratio < 0.2 and retrieved_content:
                    findings.append(
                        f"Memory retrieved at '{m_node.node_id}' was ignored by downstream tools (Causal usefulness = 0.0)."
                    )

            # 3. Staleness / Mutation check
            if mem_data.get("operation") == "query":
                keys = mem_data.get("retrieved_keys", [])
                if any("deprecated" in k.lower() or "stale" in k.lower() for k in keys):
                    staleness_detected = True
                    findings.append(f"Stale memory key detected in query at node '{m_node.node_id}'.")

        avg_rel = sum(retrieval_scores) / max(1, len(retrieval_scores))
        avg_ret = sum(retention_scores) / max(1, len(retention_scores))
        avg_use = sum(usefulness_scores) / max(1, len(usefulness_scores))

        passed = avg_rel >= 0.50 and avg_use >= 0.30 and not staleness_detected

        return MemoryAuditResult(
            has_memory_events=True,
            retrieval_relevance_score=round(avg_rel, 3),
            prompt_retention_score=round(avg_ret, 3),
            causal_usefulness_score=round(avg_use, 3),
            staleness_detected=staleness_detected,
            findings=findings,
            passed=passed,
        )
