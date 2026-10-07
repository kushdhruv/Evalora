"""core/evaluators/trajectory_eval.py: Layer 4 Trajectory & Graph Evaluator."""

import networkx as nx
from typing import List, Optional
from core.evaluators.base import BaseEvaluator
from core.models.schema import Evaluation, EventType, Trajectory, TrajectoryNode
from core.trajectory.graph import TrajectoryGraphService


class TrajectoryGraphEvaluator(BaseEvaluator):
    name: str = "trajectory_graph_metrics"
    layer: str = "trajectory"
    version: str = "1.0.0"

    async def evaluate_node(
        self, node: TrajectoryNode, trajectory: Trajectory
    ) -> Optional[Evaluation]:
        # Node-level graph checks (e.g., dangling observations)
        return None

    async def evaluate_trajectory(
        self, trajectory: Trajectory
    ) -> Optional[Evaluation]:
        if not trajectory.nodes:
            return None

        g = TrajectoryGraphService.to_networkx(trajectory)
        total_nodes = len(trajectory.nodes)
        first_node = trajectory.nodes[0].node_id
        last_node = trajectory.nodes[-1].node_id

        # 1. Path efficiency
        efficiency = TrajectoryGraphService.calculate_path_efficiency(g, first_node, last_node)

        # 2. Infinite loop / cycle detection
        has_cycles = not nx.is_directed_acyclic_graph(g)

        # 3. Repeated action penalty
        actions = [
            n.payload.get("tool_call", {}).get("tool_name")
            for n in trajectory.nodes
            if n.event_type == EventType.TOOL_CALL
        ]
        unique_actions = len(set(actions))
        redundancy_penalty = 0.0
        if actions and len(actions) > unique_actions:
            # penalize consecutive identical actions
            redundancy_penalty = min(0.4, (len(actions) - unique_actions) * 0.1)

        raw_score = (efficiency * 0.7 + (0.0 if has_cycles else 0.3)) - redundancy_penalty
        score = max(0.0, min(1.0, raw_score))
        passed = score >= 0.50

        return Evaluation(
            trace_id=trajectory.trace_id,
            trajectory_id=trajectory.trajectory_id,
            target_node_id=None,
            evaluator_name=self.name,
            evaluator_layer=self.layer,
            evaluator_version=self.version,
            score=round(score, 3),
            confidence=0.90,
            passed=passed,
            rationale=(
                f"Trajectory efficiency: {efficiency:.2f}, Cycles detected: {has_cycles}, "
                f"Redundancy penalty: {redundancy_penalty:.2f}"
            ),
            details={
                "efficiency": efficiency,
                "has_cycles": has_cycles,
                "total_nodes": total_nodes,
            },
        )
