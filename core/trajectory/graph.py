"""core/trajectory/graph.py: NetworkX graph utilities for Trajectories."""

import networkx as nx
from typing import Any, Dict, List, Optional
from core.models.schema import Trajectory, TrajectoryEdge, TrajectoryNode


class TrajectoryGraphService:
    """Manages in-memory NetworkX DiGraph representations of Trajectories."""

    @staticmethod
    def to_networkx(trajectory: Trajectory) -> nx.DiGraph:
        g = nx.DiGraph()
        for node in trajectory.nodes:
            g.add_node(
                node.node_id,
                event_id=str(node.event_id),
                event_type=node.event_type.value,
                label=node.label,
                timestamp=node.timestamp.isoformat(),
                payload=node.payload,
            )
        for edge in trajectory.edges:
            g.add_edge(
                edge.source_node_id,
                edge.target_node_id,
                edge_type=edge.edge_type,
                metadata=edge.metadata,
            )
        return g

    @staticmethod
    def get_topological_order(g: nx.DiGraph) -> List[str]:
        """Returns topological ordering. If cycles exist, breaks cycles safely."""
        if nx.is_directed_acyclic_graph(g):
            return list(nx.topological_sort(g))
        # Handle cycles (e.g., retries/loops) by creating a condensation or breaking feedback edges
        dag = g.copy()
        while not nx.is_directed_acyclic_graph(dag):
            cycle = nx.find_cycle(dag, orientation="original")
            dag.remove_edge(cycle[0][0], cycle[0][1])
        return list(nx.topological_sort(dag))

    @staticmethod
    def find_ancestors(g: nx.DiGraph, node_id: str) -> List[str]:
        if node_id in g:
            return list(nx.ancestors(g, node_id))
        return []

    @staticmethod
    def find_shortest_causal_path(g: nx.DiGraph, source: str, target: str) -> List[str]:
        try:
            return nx.shortest_path(g, source=source, target=target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return [source, target]

    @staticmethod
    def calculate_path_efficiency(g: nx.DiGraph, start_node: str, end_node: str) -> float:
        """Ratio of shortest path length to total node count."""
        total_nodes = len(g.nodes)
        if total_nodes <= 1:
            return 1.0
        try:
            shortest = nx.shortest_path(g, source=start_node, target=end_node)
            return len(shortest) / total_nodes
        except Exception:
            return 0.5
