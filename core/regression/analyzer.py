"""core/regression/analyzer.py: Regression Analyzer and CI Gate Evaluator."""

from uuid import uuid4
from core.models.schema import Experiment, GateDecision, RegressionResult


class RegressionAnalyzer:
    """Computes metric deltas between experiments and determines PASS / WARN / BLOCK gate decisions."""

    @classmethod
    def compare(
        cls,
        candidate: Experiment,
        baseline: Experiment,
        score_drop_tolerance: float = 0.05,
        cost_surge_tolerance: float = 0.20,
        latency_surge_tolerance: float = 0.30,
    ) -> RegressionResult:
        score_delta = round(candidate.mean_score - baseline.mean_score, 3)
        cost_delta = round(candidate.mean_cost_usd - baseline.mean_cost_usd, 6)
        latency_delta = round(candidate.mean_latency_ms - baseline.mean_latency_ms, 2)

        baseline_failures = baseline.total_samples - baseline.passed_samples
        candidate_failures = candidate.total_samples - candidate.passed_samples

        new_failures = max(0, candidate_failures - baseline_failures)
        resolved_failures = max(0, baseline_failures - candidate_failures)

        # Gate decision evaluation
        gate_decision = GateDecision.PASS
        reasons = []

        # 1. Block conditions: Significant score drop or new failures introduced
        if score_delta < -score_drop_tolerance:
            gate_decision = GateDecision.BLOCK
            reasons.append(f"Score dropped by {abs(score_delta):.3f} (tolerance: {score_drop_tolerance})")

        if new_failures > 0:
            gate_decision = GateDecision.BLOCK
            reasons.append(f"{new_failures} new test failure(s) detected")

        # 2. Warn conditions: Cost or latency regressions (if not already blocked)
        if gate_decision != GateDecision.BLOCK:
            cost_increase_pct = (
                (cost_delta / baseline.mean_cost_usd) if baseline.mean_cost_usd > 0 else 0.0
            )
            latency_increase_pct = (
                (latency_delta / baseline.mean_latency_ms) if baseline.mean_latency_ms > 0 else 0.0
            )

            if cost_increase_pct > cost_surge_tolerance:
                gate_decision = GateDecision.WARN
                reasons.append(f"Cost surged by {cost_increase_pct*100:.1f}%")

            if latency_increase_pct > latency_surge_tolerance and latency_delta > 200.0:
                gate_decision = GateDecision.WARN
                reasons.append(f"Latency surged by {latency_increase_pct*100:.1f}% (+{latency_delta:.1f}ms)")

        if not reasons:
            reasons.append("All metrics stable or improved.")

        # Generate markdown report
        summary_md = cls._generate_markdown_summary(
            candidate=candidate,
            baseline=baseline,
            score_delta=score_delta,
            cost_delta=cost_delta,
            latency_delta=latency_delta,
            new_failures=new_failures,
            resolved_failures=resolved_failures,
            gate_decision=gate_decision,
            reasons=reasons,
        )

        return RegressionResult(
            regression_id=uuid4(),
            experiment_id=candidate.experiment_id,
            baseline_experiment_id=baseline.experiment_id,
            score_delta=score_delta,
            cost_delta_usd=cost_delta,
            latency_delta_ms=latency_delta,
            new_failures_count=new_failures,
            resolved_failures_count=resolved_failures,
            gate_decision=gate_decision,
            breakdown_by_category={"score_drop_tolerance": score_drop_tolerance},
            summary_markdown=summary_md,
        )

    @staticmethod
    def _generate_markdown_summary(
        candidate: Experiment,
        baseline: Experiment,
        score_delta: float,
        cost_delta: float,
        latency_delta: float,
        new_failures: int,
        resolved_failures: int,
        gate_decision: GateDecision,
        reasons: list,
    ) -> str:
        icon = "✅" if gate_decision == GateDecision.PASS else ("⚠️" if gate_decision == GateDecision.WARN else "🛑")
        return f"""## {icon} Agent CI/CD Quality Gate: {gate_decision.value}

| Metric | Baseline ({baseline.agent_version}) | Candidate ({candidate.agent_version}) | Delta | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Mean Score** | {baseline.mean_score:.2f} | {candidate.mean_score:.2f} | **{'+' if score_delta >= 0 else ''}{score_delta:.2f}** | {'✅' if score_delta >= 0 else '❌'} |
| **Pass Rate** | {baseline.passed_samples}/{baseline.total_samples} | {candidate.passed_samples}/{candidate.total_samples} | **{'+' if resolved_failures >= new_failures else '-'}{abs(resolved_failures - new_failures)}** | {'✅' if candidate.passed_samples >= baseline.passed_samples else '❌'} |
| **Cost / Sample** | ${baseline.mean_cost_usd:.4f} | ${candidate.mean_cost_usd:.4f} | **{'+' if cost_delta >= 0 else ''}${cost_delta:.4f}** | {'✅' if cost_delta <= 0 else '⚠️'} |
| **Latency / Sample** | {baseline.mean_latency_ms:.1f}ms | {candidate.mean_latency_ms:.1f}ms | **{'+' if latency_delta >= 0 else ''}{latency_delta:.1f}ms** | {'✅' if latency_delta <= 0 else '⚠️'} |

**Decision Rationale**: {', '.join(reasons)}
"""
