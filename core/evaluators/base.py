"""core/evaluators/base.py: Abstract base evaluator interface."""

from abc import ABC, abstractmethod
from typing import Optional
from core.models.schema import Evaluation, Trajectory, TrajectoryNode


class BaseEvaluator(ABC):
    name: str = "base_evaluator"
    layer: str = "deterministic"  # "deterministic", "semantic", "llm_judge", "trajectory"
    version: str = "1.0.0"

    @abstractmethod
    async def evaluate_node(
        self, node: TrajectoryNode, trajectory: Trajectory
    ) -> Optional[Evaluation]:
        """Evaluate a single node in the trajectory graph."""
        pass

    @abstractmethod
    async def evaluate_trajectory(
        self, trajectory: Trajectory
    ) -> Optional[Evaluation]:
        """Evaluate the entire trajectory holistically."""
        pass
