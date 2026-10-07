"""core/regression/runner.py: Experiment runner for candidate agents over datasets."""

from typing import Any, Callable, Coroutine, Dict, List, Optional
from uuid import uuid4
from core.evaluators.pipeline import EvaluatorPipeline
from core.models.schema import DatasetItem, Experiment, Trajectory


class ExperimentRunner:
    """Executes agent implementations against test datasets and evaluates results."""

    def __init__(self, pipeline: Optional[EvaluatorPipeline] = None):
        self.pipeline = pipeline or EvaluatorPipeline()

    async def run_experiment(
        self,
        name: str,
        dataset_id: str,
        dataset_items: List[DatasetItem],
        agent_callable: Callable[[str], Coroutine[Any, Any, Trajectory]],
        agent_id: str = "candidate_agent",
        agent_version: str = "2.0.0",
    ) -> Experiment:
        total_samples = len(dataset_items)
        passed_samples = 0
        total_score = 0.0
        total_cost = 0.0
        total_latency = 0.0

        for item in dataset_items:
            # 1. Execute agent on test item prompt
            trajectory: Trajectory = await agent_callable(item.input_prompt)

            # 2. Run evaluation pipeline
            eval_result = await self.pipeline.run(trajectory)
            score = eval_result["mean_score"]
            passed = eval_result["passed"]

            # 3. Check item specific assertions
            min_score = item.assertions.get("min_score", 0.70)
            if score >= min_score and passed:
                passed_samples += 1

            total_score += score
            total_cost += trajectory.total_cost_usd
            total_latency += trajectory.total_latency_ms

        mean_score = round(total_score / max(1, total_samples), 3)
        mean_cost = round(total_cost / max(1, total_samples), 6)
        mean_latency = round(total_latency / max(1, total_samples), 2)

        return Experiment(
            experiment_id=uuid4(),
            name=name,
            dataset_id=dataset_id,
            agent_id=agent_id,
            agent_version=agent_version,
            evaluator_config={"weights": self.pipeline.weights},
            total_samples=total_samples,
            passed_samples=passed_samples,
            mean_score=mean_score,
            mean_cost_usd=mean_cost,
            mean_latency_ms=mean_latency,
        )
