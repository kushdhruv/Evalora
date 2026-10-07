"""core/evaluators/deterministic.py: Layer 1 Deterministic Evaluator."""

from typing import List, Optional, Set
from core.evaluators.base import BaseEvaluator
from core.models.schema import Evaluation, EventType, Trajectory, TrajectoryNode


class DeterministicEvaluator(BaseEvaluator):
    name: str = "deterministic_rules"
    layer: str = "deterministic"
    version: str = "1.0.0"

    def __init__(
        self,
        forbidden_tools: Optional[Set[str]] = None,
        max_tool_latency_ms: float = 10000.0,
    ):
        self.forbidden_tools = forbidden_tools or {"rm_rf", "execute_system_shell_unrestricted"}
        self.max_tool_latency_ms = max_tool_latency_ms

    async def evaluate_node(
        self, node: TrajectoryNode, trajectory: Trajectory
    ) -> Optional[Evaluation]:
        passed = True
        score = 1.0
        rationale = "Deterministic checks passed."
        details = {}

        if node.event_type == EventType.TOOL_CALL:
            tool_data = node.payload.get("tool_call", {})
            tool_name = tool_data.get("tool_name", "")
            is_error = tool_data.get("is_error", False)
            exec_time = tool_data.get("execution_time_ms", 0.0)
            args = tool_data.get("input_args", {})

            # 1. Forbidden tool check
            if tool_name in self.forbidden_tools:
                passed = False
                score = 0.0
                rationale = f"Forbidden tool '{tool_name}' was invoked."
                details["rule"] = "forbidden_tool"

            # 2. Tool error check
            elif is_error:
                passed = False
                score = 0.0
                err_msg = tool_data.get("error_message") or "Tool execution flagged error"
                rationale = f"Tool '{tool_name}' failed with error: {err_msg}"
                details["rule"] = "tool_execution_error"

            # 3. Missing arguments check (empty required fields)
            elif not args and "read" not in tool_name.lower():
                # Potential empty parameter warning
                details["warning"] = "Empty tool arguments"

            # 4. Latency threshold check
            elif exec_time > self.max_tool_latency_ms:
                passed = False
                score = 0.5
                rationale = f"Tool latency {exec_time}ms exceeded budget {self.max_tool_latency_ms}ms"
                details["rule"] = "latency_budget_exceeded"

            return Evaluation(
                trace_id=trajectory.trace_id,
                trajectory_id=trajectory.trajectory_id,
                target_node_id=node.node_id,
                evaluator_name=self.name,
                evaluator_layer=self.layer,
                evaluator_version=self.version,
                score=score,
                confidence=1.0,  # Deterministic checks always 100% confidence
                passed=passed,
                rationale=rationale,
                details=details,
            )

        return None

    async def evaluate_trajectory(
        self, trajectory: Trajectory
    ) -> Optional[Evaluation]:
        # Overall trajectory check: total latency / status
        passed = trajectory.is_success is not False
        score = 1.0 if passed else 0.0
        return Evaluation(
            trace_id=trajectory.trace_id,
            trajectory_id=trajectory.trajectory_id,
            target_node_id=None,
            evaluator_name=self.name,
            evaluator_layer=self.layer,
            evaluator_version=self.version,
            score=score,
            confidence=1.0,
            passed=passed,
            rationale="Overall trajectory deterministic sanity check.",
            details={"total_latency_ms": trajectory.total_latency_ms},
        )
