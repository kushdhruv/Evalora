"""core/causal/analyzer.py: Causal Root-Cause Discovery over Trajectory DAG."""

import networkx as nx
from typing import Dict, List, Optional
from core.models.schema import Failure, FailureCategory, RootCause, Trajectory
from core.trajectory.graph import TrajectoryGraphService


class CausalFailureAnalyzer:
    """Isolates the Primary Root Cause of cascading agent failures over the trajectory graph."""

    def __init__(self, trajectory: Trajectory):
        self.trajectory = trajectory
        self.graph = TrajectoryGraphService.to_networkx(trajectory)

    def identify_root_cause(self, failures: List[Failure]) -> Optional[RootCause]:
        if not failures:
            return None

        # 1. Identify terminal failures (the final observed failure/symptom)
        terminal_failures = [f for f in failures if f.is_terminal]
        if not terminal_failures:
            terminal_failures = failures

        target_failure = terminal_failures[-1]
        target_node = target_failure.node_id

        # 2. Extract upstream causal ancestors in the trajectory DAG
        ancestor_node_ids = TrajectoryGraphService.find_ancestors(self.graph, target_node)
        ancestor_failures = [f for f in failures if f.node_id in ancestor_node_ids]

        if not ancestor_failures:
            # The terminal failure is itself the primary root cause
            return RootCause(
                trajectory_id=self.trajectory.trajectory_id,
                primary_failure_node_id=target_node,
                primary_category=target_failure.category,
                confidence_score=0.95,
                propagation_chain=[target_node],
                explanation=(
                    f"Direct root failure at node '{target_node}' ({target_failure.category.value}): "
                    f"{target_failure.description}"
                ),
            )

        # 3. Sort ancestor failures by topological order to find the earliest unrecovered fault
        topological_order = TrajectoryGraphService.get_topological_order(self.graph)
        node_order_map = {node_id: idx for idx, node_id in enumerate(topological_order)}

        ordered_ancestor_failures = sorted(
            ancestor_failures,
            key=lambda f: node_order_map.get(f.node_id, 9999),
        )

        primary_failure = ordered_ancestor_failures[0]

        # 4. Compute causal propagation path
        propagation_path = TrajectoryGraphService.find_shortest_causal_path(
            self.graph, primary_failure.node_id, target_node
        )

        cascade_length = max(0, len(propagation_path) - 1)
        confidence = max(0.70, 0.95 - (cascade_length * 0.03))

        explanation = (
            f"Primary root fault initiated at node '{primary_failure.node_id}' "
            f"({primary_failure.category.value} - {primary_failure.subcategory}): {primary_failure.description}. "
            f"Cascaded through {cascade_length} intermediate transitions to terminal symptom at '{target_node}'."
        )

        return RootCause(
            trajectory_id=self.trajectory.trajectory_id,
            primary_failure_node_id=primary_failure.node_id,
            primary_category=primary_failure.category,
            confidence_score=round(confidence, 3),
            propagation_chain=propagation_path,
            explanation=explanation,
        )
