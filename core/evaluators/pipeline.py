"""core/evaluators/pipeline.py: Gated 4-Layer Evaluator Pipeline Orchestrator."""

import asyncio
from typing import Any, Dict, List, Optional
from core.evaluators.base import BaseEvaluator
from core.evaluators.deterministic import DeterministicEvaluator
from core.evaluators.llm_judge import LLMJudgeEvaluator
from core.evaluators.semantic import SemanticEvaluator
from core.evaluators.trajectory_eval import TrajectoryGraphEvaluator
from core.models.schema import Evaluation, Failure, FailureCategory, Trajectory, TrajectoryNode


class EvaluatorPipeline:
    """Orchestrates 4-layer evaluation with short-circuiting and score aggregation."""

    def __init__(
        self,
        deterministic: Optional[DeterministicEvaluator] = None,
        semantic: Optional[SemanticEvaluator] = None,
        llm_judge: Optional[LLMJudgeEvaluator] = None,
        trajectory_eval: Optional[TrajectoryGraphEvaluator] = None,
    ):
        self.deterministic = deterministic or DeterministicEvaluator()
        self.semantic = semantic or SemanticEvaluator()
        self.llm_judge = llm_judge or LLMJudgeEvaluator()
        self.trajectory_eval = trajectory_eval or TrajectoryGraphEvaluator()

        self.weights = {
            "deterministic": 1.0,
            "semantic": 0.6,
            "llm_judge": 0.8,
            "trajectory": 0.9,
        }

    async def run(self, trajectory: Trajectory) -> Dict[str, Any]:
        evaluations: List[Evaluation] = []
        failures: List[Failure] = []
        fatal_short_circuit = False

        # -------------------------------------------------------------
        # STEP 1: Layer 1 Deterministic Evaluator (Hard Gate - Concurrent)
        # -------------------------------------------------------------
        det_tasks = [self.deterministic.evaluate_node(node, trajectory) for node in trajectory.nodes]
        det_results = await asyncio.gather(*det_tasks)
        for node, eval_res in zip(trajectory.nodes, det_results):
            if eval_res:
                evaluations.append(eval_res)
                if not eval_res.passed:
                    # Record deterministic failure
                    failures.append(
                        Failure(
                            trajectory_id=trajectory.trajectory_id,
                            node_id=node.node_id,
                            category=FailureCategory.TOOL,
                            subcategory=eval_res.details.get("rule", "deterministic_violation"),
                            severity="FATAL",
                            description=eval_res.rationale or "Deterministic check failed",
                            is_terminal=False,
                        )
                    )
                    # If tool had fatal error or forbidden tool, short-circuit LLM Judge for this node
                    if eval_res.score == 0.0:
                        fatal_short_circuit = True

        # -------------------------------------------------------------
        # STEP 2: Layer 2 Semantic Evaluator (Concurrent)
        # -------------------------------------------------------------
        sem_tasks = [self.semantic.evaluate_node(node, trajectory) for node in trajectory.nodes]
        sem_results = await asyncio.gather(*sem_tasks)
        for sem_res in sem_results:
            if sem_res:
                evaluations.append(sem_res)

        # -------------------------------------------------------------
        # STEP 3: Layer 3 LLM Judge (Concurrent with Semaphore)
        # -------------------------------------------------------------
        judge_sem = asyncio.Semaphore(5)

        async def _eval_judge(node: TrajectoryNode):
            node_has_fatal = any(
                f.node_id == node.node_id and f.severity == "FATAL" for f in failures
            )
            if node_has_fatal:
                return None
            async with judge_sem:
                return await self.llm_judge.evaluate_node(node, trajectory)

        judge_tasks = [_eval_judge(node) for node in trajectory.nodes]
        judge_results = await asyncio.gather(*judge_tasks)
        for node, judge_res in zip(trajectory.nodes, judge_results):
            if judge_res:
                evaluations.append(judge_res)
                if not judge_res.passed:
                    cat_str = judge_res.details.get("detected_error_category") or "reasoning_state"
                    category = FailureCategory.REASONING_STATE
                    if cat_str == "outcome":
                        category = FailureCategory.OUTCOME
                    elif cat_str == "tool":
                        category = FailureCategory.TOOL

                    failures.append(
                        Failure(
                            trajectory_id=trajectory.trajectory_id,
                            node_id=node.node_id,
                            category=category,
                            subcategory="judge_critique_failure",
                            severity="DEGRADED",
                            description=judge_res.rationale or "Judge rejected node execution",
                            is_terminal=(category == FailureCategory.OUTCOME),
                        )
                    )

        # -------------------------------------------------------------
        # STEP 4: Trajectory-Level Multi-Layer Evaluators (Concurrent)
        # -------------------------------------------------------------
        traj_tasks = [
            self.deterministic.evaluate_trajectory(trajectory),
            self.semantic.evaluate_trajectory(trajectory),
            self.llm_judge.evaluate_trajectory(trajectory),
            self.trajectory_eval.evaluate_trajectory(trajectory),
        ]
        traj_results = await asyncio.gather(*traj_tasks)
        for tr in traj_results:
            if tr:
                evaluations.append(tr)

        # -------------------------------------------------------------
        # STEP 5: Aggregation & Weighted Scoring
        # -------------------------------------------------------------
        total_weighted_score = 0.0
        total_weight_conf = 0.0

        for ev in evaluations:
            w = self.weights.get(ev.evaluator_layer, 0.5)
            wc = w * ev.confidence
            total_weighted_score += ev.score * wc
            total_weight_conf += wc

        mean_score = (
            round(total_weighted_score / total_weight_conf, 3)
            if total_weight_conf > 0
            else 0.0
        )

        return {
            "evaluations": evaluations,
            "failures": failures,
            "mean_score": mean_score,
            "fatal_short_circuit": fatal_short_circuit,
            "passed": mean_score >= 0.70 and not any(f.is_terminal for f in failures),
        }
