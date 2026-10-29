"""core/evaluators/semantic.py: Layer 2 Semantic Evaluator with Vector Embedding & Lexical Grounding."""

import math
import os
import re
from typing import Dict, List, Optional, Set
from core.evaluators.base import BaseEvaluator
from core.models.schema import Evaluation, EventType, Trajectory, TrajectoryNode

try:
    import litellm
    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False


class SemanticEvaluator(BaseEvaluator):
    name: str = "semantic_similarity"
    layer: str = "semantic"
    version: str = "1.0.0"

    def __init__(self, embedding_model: Optional[str] = None):
        self.embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "gemini/gemini-embedding-001")

    def _tokenize(self, text: str) -> Set[str]:
        words = re.findall(r"\b\w{3,}\b", text.lower())
        return set(words)

    def _jaccard_similarity(self, s1: Set[str], s2: Set[str]) -> float:
        if not s1 or not s2:
            return 0.0
        intersection = len(s1.intersection(s2))
        union = len(s1.union(s2))
        return intersection / union if union > 0 else 0.0

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm1 * norm2)))

    async def _compute_embedding_similarity(self, text1: str, text2: str) -> Optional[float]:
        if not HAS_LITELLM or not os.getenv("GEMINI_API_KEY"):
            return None
        try:
            res = await litellm.aembedding(
                model=self.embedding_model,
                input=[text1[:1000], text2[:1000]],
            )
            vec1 = res.data[0]["embedding"]
            vec2 = res.data[1]["embedding"]
            return self._cosine_similarity(vec1, vec2)
        except Exception:
            return None

    async def evaluate_node(
        self, node: TrajectoryNode, trajectory: Trajectory
    ) -> Optional[Evaluation]:
        # Evaluates semantic retrieval relevance on MEMORY_READ nodes
        if node.event_type == EventType.MEMORY_READ:
            mem_data = node.payload.get("memory_event", {})
            query = mem_data.get("query_text") or ""
            retrieved = mem_data.get("retrieved_content") or []
            scores = mem_data.get("similarity_scores") or []

            confidence = 0.85
            method = "lexical_jaccard"

            if scores:
                avg_score = sum(scores) / len(scores)
                score = min(1.0, max(0.0, avg_score))
                method = "reported_vector_similarity"
            elif query and retrieved:
                r_text = " ".join([str(item) for item in retrieved])
                # Attempt vector embedding similarity if API key is present
                vec_sim = await self._compute_embedding_similarity(query, r_text)
                if vec_sim is not None:
                    score = vec_sim
                    method = "gemini_vector_embedding"
                    confidence = 0.95
                else:
                    q_tokens = self._tokenize(query)
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
                confidence=confidence,
                passed=passed,
                rationale=f"Semantic retrieval relevance score ({method}): {score:.2f}",
                details={"scores": scores, "method": method},
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
