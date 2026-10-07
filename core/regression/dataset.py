"""core/regression/dataset.py: Curates Traces into Structured Dataset Items."""

from typing import Any, Dict, List, Optional
from uuid import uuid4
from core.models.schema import DatasetItem, EventType, Trajectory


class DatasetCurationService:
    """Extracts test fixtures and assertions from recorded production trajectories."""

    @classmethod
    def create_item_from_trajectory(
        cls,
        trajectory: Trajectory,
        dataset_id: str = "default_regression_set",
        custom_input_prompt: Optional[str] = None,
        expected_outcome: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> DatasetItem:
        # 1. Infer input prompt from first node or argument
        first_node = trajectory.nodes[0] if trajectory.nodes else None
        input_prompt = custom_input_prompt or "Execute workflow"
        if first_node:
            content = first_node.payload.get("content")
            if content:
                input_prompt = str(content)

        # 2. Extract tools and success criteria
        tool_names = [
            n.payload.get("tool_call", {}).get("tool_name")
            for n in trajectory.nodes
            if n.event_type == EventType.TOOL_CALL
        ]

        assertions: Dict[str, Any] = {
            "expected_tools": [t for t in tool_names if t],
            "min_score": 0.80,
            "forbid_tool_errors": True,
            "max_latency_ms": max(3000.0, trajectory.total_latency_ms * 1.5),
        }

        # 3. Outcome
        if not expected_outcome:
            outcome_node = next(
                (n for n in reversed(trajectory.nodes) if n.event_type == EventType.FINAL_OUTCOME),
                None,
            )
            if outcome_node:
                expected_outcome = str(outcome_node.payload.get("content", ""))

        return DatasetItem(
            item_id=uuid4(),
            dataset_id=dataset_id,
            source_trace_id=trajectory.trace_id,
            input_prompt=input_prompt,
            expected_outcome=expected_outcome,
            expected_trajectory_schema={"node_count": len(trajectory.nodes)},
            assertions=assertions,
            tags=tags or ["regression_test", f"agent:{trajectory.agent_id}"],
        )
