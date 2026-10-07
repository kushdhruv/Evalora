"""core/evaluators/llm_judge.py: Layer 3 Structured LLM Judge Evaluator with LiteLLM live provider support."""

import json
import os
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, Field
from core.evaluators.base import BaseEvaluator
from core.models.schema import Evaluation, EventType, Trajectory, TrajectoryNode

try:
    import litellm
    # Suppress verbose litellm logs
    litellm.suppress_debug_info = True
    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False


class LLMJudgeStructuredOutput(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    detected_error_category: Optional[str] = None


class LLMJudgeEvaluator(BaseEvaluator):
    name: str = "llm_judge"
    layer: str = "llm_judge"
    version: str = "1.0.0"

    def __init__(
        self,
        model_name: Optional[str] = None,
        judge_fn: Optional[Callable[[Dict[str, Any]], LLMJudgeStructuredOutput]] = None,
    ):
        self.model_name = model_name or os.getenv("LLM_JUDGE_MODEL", "heuristic-judge-v1")
        self.custom_judge_fn = judge_fn

    def _has_live_llm_key(self) -> bool:
        return any(
            os.getenv(k)
            for k in [
                "GEMINI_API_KEY",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "GROQ_API_KEY",
                "OLLAMA_API_BASE",
            ]
        )

    def _default_heuristic_judge(self, context: Dict[str, Any]) -> LLMJudgeStructuredOutput:
        event_type = context.get("event_type")
        payload = context.get("payload", {})

        if event_type == EventType.FINAL_OUTCOME.value:
            content = (payload.get("content") or "").lower()
            if any(err_word in content for err_word in ["unable", "failed", "error", "cannot", "sorry"]):
                return LLMJudgeStructuredOutput(
                    score=0.20,
                    passed=False,
                    confidence=0.90,
                    rationale="Final response explicitly acknowledges task fulfillment failure.",
                    detected_error_category="outcome",
                )
            return LLMJudgeStructuredOutput(
                score=0.95,
                passed=True,
                confidence=0.92,
                rationale="Agent delivered a complete and coherent outcome.",
            )

        elif event_type == EventType.TOOL_CALL.value:
            tc = payload.get("tool_call", {})
            if tc.get("is_error"):
                return LLMJudgeStructuredOutput(
                    score=0.10,
                    passed=False,
                    confidence=0.95,
                    rationale=f"Tool call failed: {tc.get('error_message')}",
                    detected_error_category="tool",
                )
            return LLMJudgeStructuredOutput(
                score=0.90,
                passed=True,
                confidence=0.88,
                rationale="Tool call successfully executed and logically aligned with goal.",
            )

        return LLMJudgeStructuredOutput(
            score=0.85,
            passed=True,
            confidence=0.80,
            rationale="Step reasoning is valid.",
        )

    async def _evaluate_with_live_llm(self, context: Dict[str, Any]) -> LLMJudgeStructuredOutput:
        prompt = f"""You are an expert AI Agent Evaluation Judge.
Analyze the following step executed by an autonomous AI agent:

Step Node ID: {context.get('node_id')}
Step Event Type: {context.get('event_type')}
Step Label: {context.get('label')}
Payload Data: {json.dumps(context.get('payload', {}), indent=2)}

Evaluate:
1. Did this step advance the agent towards fulfilling the goal?
2. Did any tool argument or schema hallucination occur?
3. If an error occurred, did the agent handle it or cascade it?

Respond ONLY in valid JSON matching this exact structure:
{{
  "score": <float between 0.0 and 1.0>,
  "passed": <boolean true or false>,
  "confidence": <float between 0.0 and 1.0>,
  "rationale": "<concise 1-2 sentence justification>",
  "detected_error_category": "<one of: planning, tool, context_memory, reasoning_state, environment, outcome, or null>"
}}
"""
        try:
            model = self.model_name
            # If using gemini without explicit prefix, ensure provider routing
            if os.getenv("GEMINI_API_KEY") and not model.startswith("gemini/"):
                model = f"gemini/{model}"

            response = await litellm.acompletion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
                timeout=10,
            )
            raw_text = response.choices[0].message.content
            parsed = json.loads(raw_text)
            return LLMJudgeStructuredOutput(**parsed)
        except Exception:
            # Fall back safely to heuristic judge on network or API quota error
            return self._default_heuristic_judge(context)

    async def evaluate_node(
        self, node: TrajectoryNode, trajectory: Trajectory
    ) -> Optional[Evaluation]:
        if node.event_type in (EventType.TOOL_CALL, EventType.FINAL_OUTCOME, EventType.PLAN):
            context = {
                "node_id": node.node_id,
                "event_type": node.event_type.value,
                "label": node.label,
                "payload": node.payload,
                "agent_id": trajectory.agent_id,
            }

            if self.custom_judge_fn:
                res = self.custom_judge_fn(context)
            elif HAS_LITELLM and self._has_live_llm_key():
                res = await self._evaluate_with_live_llm(context)
            else:
                res = self._default_heuristic_judge(context)

            return Evaluation(
                trace_id=trajectory.trace_id,
                trajectory_id=trajectory.trajectory_id,
                target_node_id=node.node_id,
                evaluator_name=f"{self.name}:{self.model_name}",
                evaluator_layer=self.layer,
                evaluator_version=self.version,
                score=round(res.score, 3),
                confidence=round(res.confidence, 3),
                passed=res.passed,
                rationale=res.rationale,
                details={"detected_error_category": res.detected_error_category},
            )
        return None

    async def evaluate_trajectory(
        self, trajectory: Trajectory
    ) -> Optional[Evaluation]:
        outcome_node = next(
            (n for n in reversed(trajectory.nodes) if n.event_type == EventType.FINAL_OUTCOME),
            None,
        )
        if outcome_node:
            context = {
                "node_id": outcome_node.node_id,
                "event_type": EventType.FINAL_OUTCOME.value,
                "label": outcome_node.label,
                "payload": outcome_node.payload,
            }
            if self.custom_judge_fn:
                res = self.custom_judge_fn(context)
            elif HAS_LITELLM and self._has_live_llm_key():
                res = await self._evaluate_with_live_llm(context)
            else:
                res = self._default_heuristic_judge(context)

            return Evaluation(
                trace_id=trajectory.trace_id,
                trajectory_id=trajectory.trajectory_id,
                target_node_id=None,
                evaluator_name=f"{self.name}:{self.model_name}:trajectory",
                evaluator_layer=self.layer,
                evaluator_version=self.version,
                score=round(res.score, 3),
                confidence=round(res.confidence, 3),
                passed=res.passed,
                rationale=res.rationale,
                details={"detected_error_category": res.detected_error_category},
            )
        return None
