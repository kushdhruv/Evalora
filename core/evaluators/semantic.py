"""core/evaluators/semantic.py: Layer 2 Semantic Evaluator."""

import math
import re
from typing import Dict, List, Optional, Set
from core.evaluators.base import BaseEvaluator
from core.models.schema import Evaluation, EventType, Trajectory, TrajectoryNode


class SemanticEvaluator(BaseEvaluator):
    name: str = "semantic_similarity"
    layer: str = "semantic"
    version: str = "1.0.0"

    def _tokenize(self, text: str) -> Set[str]:
        words = re.findall(r"\b\w{3,}\b", text.lower())
        return set(words)

    def _jaccard_similarity(self, s1: Set[str], s2: Set[str]) -> float:
        if not s1 or not s2:
            return 0.0
        intersection = len(s1.intersection(s2))
        union = len(s1.union(s2))
        return intersection / union if union > 0 else 0.0

    async def evaluate_node(
        self, node: TrajectoryNode, trajectory: Trajectory
    ) -> Optional[Evaluation]:
        # Evaluates semantic retrieval relevance on MEMORY_READ nodes
        if node.event_type == EventType.MEMORY_READ:
            mem_data = node.payload.get("memory_event", {})
            query = mem_data.get("query_text") or ""
            retrieved = mem_data.get("retrieved_content") or []
            scores = mem_data.get("similarity_scores") or []

            if scores:
                avg_score = sum(scores) / len(scores)
                score = min(1.0, max(0.0, avg_score))
            elif query and retrieved:
                q_tokens = self._tokenize(query)
                r_text = " ".join([str(item) for item in retrieved])
                r_tokens = self._tokenize(r_text)
                score = self._jaccard_similarity(q_tokens, r_tokens)
            else:
                score = 0.5

            passed = score >= 0.60
            return Evaluation(
                trace_id=trajectory.trace_id,
                trajectory_id=trajectory.trajectory_id,
                target_node_id=node.node_id,
                evaluator_name=self.name,
                evaluator_layer=self.layer,
                evaluator_version=self.version,
                score=round(score, 3),
                confidence=0.85,
                passed=passed,
                rationale=f"Semantic retrieval relevance score: {score:.2f}",
                details={"scores": scores},
            )

        return None

    async def evaluate_trajectory(
        self, trajectory: Trajectory
    ) -> Optional[Evaluation]:
        # Evaluates grounding: check if final outcome tokens overlap with tool observations
        outcome_node = next(
            (n for n in reversed(trajectory.nodes) if n.event_type == EventType.FINAL_OUTCOME),
            None,
        )
        if not outcome_node or not outcome_node.payload.get("content"):
            return None

        outcome_tokens = self._tokenize(outcome_node.payload["content"])
        observation_tokens: Set[str] = set()

        for node in trajectory.nodes:
            if node.event_type == EventType.TOOL_CALL:
                out = node.payload.get("tool_call", {}).get("output_result")
                if out:
                    observation_tokens.update(self._tokenize(str(out)))

        if not observation_tokens:
            overlap_score = 0.8  # No tools to ground against
        else:
            overlap_score = len(outcome_tokens.intersection(observation_tokens)) / max(
                1, len(outcome_tokens)
            )

        score = min(1.0, max(0.0, overlap_score))
        return Evaluation(
            trace_id=trajectory.trace_id,
            trajectory_id=trajectory.trajectory_id,
            target_node_id=outcome_node.node_id,
            evaluator_name="grounding_overlap",
            evaluator_layer=self.layer,
            evaluator_version=self.version,
            score=round(score, 3),
            confidence=0.80,
            passed=score >= 0.20,
            rationale=f"Final outcome token overlap with observations: {score:.2f}",
            details={"overlap_ratio": score},
        )
