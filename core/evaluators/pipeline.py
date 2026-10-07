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
        # STEP 1: Layer 1 Deterministic Evaluator (Hard Gate)
        # -------------------------------------------------------------
        for node in trajectory.nodes:
            eval_res = await self.deterministic.evaluate_node(node, trajectory)
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

        traj_det = await self.deterministic.evaluate_trajectory(trajectory)
        if traj_det:
            evaluations.append(traj_det)

        # -------------------------------------------------------------
        # STEP 2: Layer 2 Semantic Evaluator
        # -------------------------------------------------------------
        for node in trajectory.nodes:
            sem_res = await self.semantic.evaluate_node(node, trajectory)
            if sem_res:
                evaluations.append(sem_res)

        traj_sem = await self.semantic.evaluate_trajectory(trajectory)
        if traj_sem:
            evaluations.append(traj_sem)

        # -------------------------------------------------------------
        # STEP 3: Layer 3 LLM Judge (Skipped if fatal deterministic error occurred on node)
        # -------------------------------------------------------------
        for node in trajectory.nodes:
            # Check if this node already experienced fatal deterministic failure
            node_has_fatal = any(
                f.node_id == node.node_id and f.severity == "FATAL" for f in failures
            )
            if node_has_fatal:
                continue  # Save compute and avoid LLM judging already broken steps

            judge_res = await self.llm_judge.evaluate_node(node, trajectory)
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

        traj_judge = await self.llm_judge.evaluate_trajectory(trajectory)
        if traj_judge:
            evaluations.append(traj_judge)

        # -------------------------------------------------------------
        # STEP 4: Layer 4 Trajectory Graph Evaluator
        # -------------------------------------------------------------
        traj_graph = await self.trajectory_eval.evaluate_trajectory(trajectory)
        if traj_graph:
            evaluations.append(traj_graph)

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
