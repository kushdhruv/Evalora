"""tests/test_deep_stress_and_edge_cases.py: Deep Stress, Edge Cases, Boundary and Fuzz Testing."""

import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
import networkx as nx
from httpx import ASGITransport, AsyncClient

from core.models.schema import (
    AgentEvent,
    EventType,
    Failure,
    FailureCategory,
    GateDecision,
    MemoryEvent,
    Span,
    ToolCall,
    Trajectory,
    TrajectoryEdge,
    TrajectoryNode,
    Experiment,
)
from core.telemetry.ingest import OTLPIngestService
from core.telemetry.normalizer import SpanNormalizer
from core.trajectory.builder import TrajectoryBuilder
from core.trajectory.graph import TrajectoryGraphService
from core.evaluators.deterministic import DeterministicEvaluator
from core.evaluators.semantic import SemanticEvaluator
from core.evaluators.trajectory_eval import TrajectoryGraphEvaluator
from core.evaluators.pipeline import EvaluatorPipeline
from core.causal.analyzer import CausalFailureAnalyzer
from core.memory.auditor import MemoryTelemetryAuditor
from core.regression.analyzer import RegressionAnalyzer
from core.regression.dataset import DatasetCurationService
from core.regression.runner import ExperimentRunner
from core.db.repository import default_repository
from server.main import app


# =============================================================================
# 1. Telemetry Ingest & Normalizer Edge Cases
# =============================================================================

def test_otlp_ingest_malformed_empty_payload():
    """Empty or corrupted OTLP payload should return empty span list without crashing."""
    spans = OTLPIngestService.parse_otlp_json({})
    assert spans == []

    spans_corrupt = OTLPIngestService.parse_otlp_json({"resourceSpans": [{"scopeSpans": [{"spans": []}]}]})
    assert spans_corrupt == []


def test_otlp_ingest_timestamp_variations():
    """Validates nanosecond, second, ISO-8601 string, and invalid timestamp parsing."""
    t_nano = OTLPIngestService._parse_time(1710000000000000000)
    assert t_nano.year >= 2024

    t_sec = OTLPIngestService._parse_time(1710000000.5)
    assert t_sec.year >= 2024

    t_iso = OTLPIngestService._parse_time("2026-10-28T12:00:00Z")
    assert t_iso.year == 2026

    t_invalid = OTLPIngestService._parse_time("not-a-timestamp")
    assert isinstance(t_invalid, datetime)


def test_span_normalizer_status_code_edge_cases():
    """Status code 'ERROR' vs 2 vs 'OK' vs missing."""
    now = datetime.now(timezone.utc)
    s_err_int = Span(span_id="s1", trace_id="t1", name="call", start_time=now, end_time=now, status_code="ERROR")
    ev = SpanNormalizer.normalize_span(s_err_int)
    assert ev.event_type == EventType.REASONING

    # Tool with status ERROR
    s_tool_err = Span(
        span_id="s2",
        trace_id="t1",
        name="tool_run",
        start_time=now,
        end_time=now,
        status_code="ERROR",
        attributes={"tool.name": "calculator"},
    )
    ev_tool = SpanNormalizer.normalize_span(s_tool_err)
    assert ev_tool.event_type == EventType.TOOL_CALL
    assert ev_tool.tool_call.is_error is True


def test_span_normalizer_huge_attributes():
    """Ensures huge attribute payloads do not crash parser."""
    now = datetime.now(timezone.utc)
    huge_text = "x" * 50000
    s_huge = Span(
        span_id="s_huge",
        trace_id="t_huge",
        name="huge_span",
        start_time=now,
        end_time=now,
        attributes={"output.value": huge_text},
    )
    ev = SpanNormalizer.normalize_span(s_huge)
    assert len(ev.content) == 50000


# =============================================================================
# 2. Trajectory Reconstruction & Graph Edge Cases
# =============================================================================

def test_trajectory_builder_zero_events():
    """Empty events list creates safe placeholder trajectory."""
    traj = TrajectoryBuilder.build_trajectory([])
    assert traj.trace_id == "empty"
    assert len(traj.nodes) == 0
    assert len(traj.edges) == 0


def test_trajectory_builder_single_node():
    """Single node trajectory has zero edges and correct efficiency."""
    now = datetime.now(timezone.utc)
    ev = AgentEvent(
        trace_id="t_single",
        span_id="s1",
        event_type=EventType.PLAN,
        timestamp=now,
        content="Single step plan",
    )
    traj = TrajectoryBuilder.build_trajectory([ev])
    assert len(traj.nodes) == 1
    assert len(traj.edges) == 0

    g = TrajectoryGraphService.to_networkx(traj)
    eff = TrajectoryGraphService.calculate_path_efficiency(g, "node_1_plan", "node_1_plan")
    assert eff == 1.0


def test_trajectory_graph_cycle_breaking():
    """Graph with intentional feedback loops must have cycles broken for topological sort."""
    g = nx.DiGraph()
    g.add_edge("node_1", "node_2")
    g.add_edge("node_2", "node_3")
    g.add_edge("node_3", "node_2")  # Cycle!

    topo = TrajectoryGraphService.get_topological_order(g)
    assert len(topo) == 3
    assert set(topo) == {"node_1", "node_2", "node_3"}


def test_trajectory_graph_disconnected_subgraphs():
    """Graph with two completely disconnected components."""
    g = nx.DiGraph()
    g.add_edge("branch_a_1", "branch_a_2")
    g.add_edge("branch_b_1", "branch_b_2")

    path = TrajectoryGraphService.find_shortest_causal_path(g, "branch_a_1", "branch_b_2")
    # No path exists: fallback returns [source, target]
    assert path == ["branch_a_1", "branch_b_2"]


# =============================================================================
# 3. 4-Layer Evaluator Boundary & Extreme Value Tests
# =============================================================================

@pytest.mark.asyncio
async def test_deterministic_forbidden_tool():
    """Forbidden tool invocation flags fatal error with score 0.0."""
    evaluator = DeterministicEvaluator(forbidden_tools={"rm_rf", "eval_untrusted"})
    now = datetime.now(timezone.utc)
    node = TrajectoryNode(
        node_id="node_forbidden",
        event_id=uuid4(),
        event_type=EventType.TOOL_CALL,
        label="Forbidden tool",
        timestamp=now,
        payload={"tool_call": {"tool_name": "rm_rf", "is_error": False}},
    )
    traj = Trajectory(trace_id="t_forbid", nodes=[node])
    res = await evaluator.evaluate_node(node, traj)
    assert res is not None
    assert res.score == 0.0
    assert res.passed is False
    assert res.details.get("rule") == "forbidden_tool"


@pytest.mark.asyncio
async def test_deterministic_latency_budget_exceeded():
    """Tool exceeding latency budget receives 0.5 score."""
    evaluator = DeterministicEvaluator(max_tool_latency_ms=1000.0)
    now = datetime.now(timezone.utc)
    node = TrajectoryNode(
        node_id="node_slow",
        event_id=uuid4(),
        event_type=EventType.TOOL_CALL,
        label="Slow tool",
        timestamp=now,
        payload={"tool_call": {"tool_name": "slow_api", "execution_time_ms": 5000.0, "input_args": {"q": "test"}}},
    )
    traj = Trajectory(trace_id="t_slow", nodes=[node])
    res = await evaluator.evaluate_node(node, traj)
    assert res.score == 0.5
    assert res.passed is False
    assert res.details.get("rule") == "latency_budget_exceeded"


@pytest.mark.asyncio
async def test_gated_pipeline_fatal_short_circuit():
    """Fatal Layer 1 deterministic failure short-circuits Layer 3 LLM judging for that node."""
    pipeline = EvaluatorPipeline()
    now = datetime.now(timezone.utc)
    fatal_node = TrajectoryNode(
        node_id="fatal_tool",
        event_id=uuid4(),
        event_type=EventType.TOOL_CALL,
        label="Crashed Tool",
        timestamp=now,
        payload={"tool_call": {"tool_name": "rm_rf", "is_error": True, "error_message": "Segmentation fault"}},
    )
    outcome_node = TrajectoryNode(
        node_id="outcome",
        event_id=uuid4(),
        event_type=EventType.FINAL_OUTCOME,
        label="Final Outcome",
        timestamp=now,
        payload={"content": "I encountered an error."},
    )
    traj = Trajectory(
        trace_id="t_short_circuit",
        nodes=[fatal_node, outcome_node],
        edges=[TrajectoryEdge(source_node_id="fatal_tool", target_node_id="outcome", edge_type="temporal_sequence")],
        is_success=False,
    )

    result = await pipeline.run(traj)
    assert result["passed"] is False
    assert len(result["failures"]) >= 1

    # Verify that fatal_node was NOT evaluated by LLM judge due to short-circuit
    judge_evals_for_fatal_node = [
        e for e in result["evaluations"]
        if e.target_node_id == "fatal_tool" and e.evaluator_layer == "llm_judge"
    ]
    assert len(judge_evals_for_fatal_node) == 0


# =============================================================================
# 4. Causal Failure Analyzer Fuzzing & Blame Attribution
# =============================================================================

def test_causal_analyzer_no_failures():
    """Trajectory with 0 failures returns None."""
    traj = Trajectory(trace_id="t_clean", nodes=[])
    analyzer = CausalFailureAnalyzer(traj)
    rc = analyzer.identify_root_cause([])
    assert rc is None


def test_causal_analyzer_single_terminal_failure():
    """Single failure is directly identified as root cause without ancestors."""
    now = datetime.now(timezone.utc)
    node = TrajectoryNode(
        node_id="terminal_node",
        event_id=uuid4(),
        event_type=EventType.FINAL_OUTCOME,
        label="Outcome",
        timestamp=now,
        payload={"content": "Failed."},
    )
    traj = Trajectory(trace_id="t_single_fail", nodes=[node])
    analyzer = CausalFailureAnalyzer(traj)
    fail = Failure(
        trajectory_id=traj.trajectory_id,
        node_id="terminal_node",
        category=FailureCategory.OUTCOME,
        subcategory="incorrect_answer",
        description="Outcome was incorrect",
        is_terminal=True,
    )
    rc = analyzer.identify_root_cause([fail])
    assert rc is not None
    assert rc.primary_failure_node_id == "terminal_node"
    assert rc.propagation_chain == ["terminal_node"]


def test_causal_analyzer_deep_cascade_attribution():
    """3-step cascade: Node 1 fails (root), Node 2 fails (cascade), Node 3 fails (symptom)."""
    now = datetime.now(timezone.utc)
    n1 = TrajectoryNode(node_id="n1", event_id=uuid4(), event_type=EventType.TOOL_CALL, label="T1", timestamp=now, payload={})
    n2 = TrajectoryNode(node_id="n2", event_id=uuid4(), event_type=EventType.TOOL_CALL, label="T2", timestamp=now, payload={})
    n3 = TrajectoryNode(node_id="n3", event_id=uuid4(), event_type=EventType.FINAL_OUTCOME, label="Outcome", timestamp=now, payload={})

    edges = [
        TrajectoryEdge(source_node_id="n1", target_node_id="n2", edge_type="temporal_sequence"),
        TrajectoryEdge(source_node_id="n2", target_node_id="n3", edge_type="temporal_sequence"),
    ]
    traj = Trajectory(trace_id="t_cascade", nodes=[n1, n2, n3], edges=edges, is_success=False)

    failures = [
        Failure(trajectory_id=traj.trajectory_id, node_id="n1", category=FailureCategory.TOOL, subcategory="syntax_error", description="SQL syntax error", is_terminal=False),
        Failure(trajectory_id=traj.trajectory_id, node_id="n2", category=FailureCategory.TOOL, subcategory="retry_failed", description="Retry failed", is_terminal=False),
        Failure(trajectory_id=traj.trajectory_id, node_id="n3", category=FailureCategory.OUTCOME, subcategory="failed_outcome", description="Goal not achieved", is_terminal=True),
    ]

    analyzer = CausalFailureAnalyzer(traj)
    rc = analyzer.identify_root_cause(failures)
    assert rc is not None
    assert rc.primary_failure_node_id == "n1"
    assert rc.primary_category == FailureCategory.TOOL
    assert rc.propagation_chain == ["n1", "n2", "n3"]
    assert "Cascaded through 2 intermediate transitions" in rc.explanation


# =============================================================================
# 5. Memory Telemetry Auditor Edge Cases
# =============================================================================

def test_memory_auditor_zero_memory_nodes():
    """Trajectory without memory events returns clear finding."""
    traj = Trajectory(trace_id="t_no_mem", nodes=[])
    res = MemoryTelemetryAuditor.audit_trajectory(traj)
    assert res.has_memory_events is False
    assert len(res.findings) == 1


def test_memory_auditor_stale_key_detection():
    """Detects 'deprecated' or 'stale' memory retrieval keys."""
    now = datetime.now(timezone.utc)
    m_node = TrajectoryNode(
        node_id="m1",
        event_id=uuid4(),
        event_type=EventType.MEMORY_READ,
        label="Memory query",
        timestamp=now,
        payload={
            "memory_event": {
                "operation": "query",
                "retrieved_keys": ["user_address_stale_v1"],
                "retrieved_content": ["123 Old Street"],
                "similarity_scores": [0.90],
            }
        },
    )
    traj = Trajectory(trace_id="t_stale", nodes=[m_node])
    res = MemoryTelemetryAuditor.audit_trajectory(traj)
    assert res.staleness_detected is True
    assert res.passed is False
    assert any("Stale memory key" in f for f in res.findings)


def test_memory_auditor_causal_usefulness_success():
    """Memory read containing 'EUR' is causally used when downstream tool arguments contain 'EUR'."""
    now = datetime.now(timezone.utc)
    m_node = TrajectoryNode(
        node_id="m1",
        event_id=uuid4(),
        event_type=EventType.MEMORY_READ,
        label="Memory query",
        timestamp=now,
        payload={
            "memory_event": {
                "operation": "read",
                "retrieved_keys": ["currency_pref"],
                "retrieved_content": [{"currency": "EUR"}],
                "similarity_scores": [0.95],
            }
        },
    )
    t_node = TrajectoryNode(
        node_id="t1",
        event_id=uuid4(),
        event_type=EventType.TOOL_CALL,
        label="Payment",
        timestamp=now,
        payload={"tool_call": {"tool_name": "pay_invoice", "input_args": {"currency": "EUR", "amount": 100}}},
    )
    traj = Trajectory(trace_id="t_mem_used", nodes=[m_node, t_node])
    res = MemoryTelemetryAuditor.audit_trajectory(traj)
    assert res.causal_usefulness_score >= 0.8
    assert res.passed is True


# =============================================================================
# 6. Regression Analyzer CI Gate Boundary & Tolerance Tests
# =============================================================================

def test_regression_gate_zero_cost_zero_latency_no_division_by_zero():
    """Protects against ZeroDivisionError when baseline cost and latency are 0.0."""
    baseline = Experiment(
        name="Baseline",
        dataset_id="d1",
        agent_id="agent",
        agent_version="1.0.0",
        total_samples=5,
        passed_samples=5,
        mean_score=0.90,
        mean_cost_usd=0.0,
        mean_latency_ms=0.0,
    )
    candidate = Experiment(
        name="Candidate",
        dataset_id="d1",
        agent_id="agent",
        agent_version="2.0.0",
        total_samples=5,
        passed_samples=5,
        mean_score=0.92,
        mean_cost_usd=0.001,
        mean_latency_ms=10.0,
    )
    result = RegressionAnalyzer.compare(candidate=candidate, baseline=baseline)
    assert result.gate_decision == GateDecision.PASS


def test_regression_gate_score_drop_block():
    """Candidate with score drop exceeding tolerance is BLOCKED."""
    baseline = Experiment(
        name="Baseline",
        dataset_id="d1",
        agent_id="agent",
        agent_version="1.0.0",
        total_samples=10,
        passed_samples=10,
        mean_score=0.95,
        mean_cost_usd=0.01,
        mean_latency_ms=100.0,
    )
    candidate = Experiment(
        name="Candidate Regressed",
        dataset_id="d1",
        agent_id="agent",
        agent_version="1.1.0",
        total_samples=10,
        passed_samples=8,
        mean_score=0.75,  # -0.20 drop > 0.05 tolerance
        mean_cost_usd=0.01,
        mean_latency_ms=100.0,
    )
    result = RegressionAnalyzer.compare(candidate=candidate, baseline=baseline)
    assert result.gate_decision == GateDecision.BLOCK
    assert "Score dropped" in result.summary_markdown


def test_regression_gate_latency_cost_warning():
    """Cost/latency surge triggers WARN without blocking."""
    baseline = Experiment(
        name="Baseline",
        dataset_id="d1",
        agent_id="agent",
        agent_version="1.0.0",
        total_samples=10,
        passed_samples=10,
        mean_score=0.90,
        mean_cost_usd=0.01,
        mean_latency_ms=100.0,
    )
    candidate = Experiment(
        name="Candidate Slower",
        dataset_id="d1",
        agent_id="agent",
        agent_version="2.0.0",
        total_samples=10,
        passed_samples=10,
        mean_score=0.92,
        mean_cost_usd=0.015,  # +50% cost surge
        mean_latency_ms=500.0,  # +400ms latency surge
    )
    result = RegressionAnalyzer.compare(candidate=candidate, baseline=baseline)
    assert result.gate_decision == GateDecision.WARN


# =============================================================================
# 7. FastAPI Server REST Security & Robustness Tests
# =============================================================================

@pytest.mark.asyncio
async def test_api_invalid_trace_id_404():
    """Querying a non-existent trace returns clean 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/trajectories/trace_does_not_exist_99999")
        assert res.status_code == 404
        assert res.json()["detail"] == "Trajectory not found"


@pytest.mark.asyncio
async def test_api_empty_otlp_payload_400():
    """Sending empty JSON to /v1/traces returns 400 Bad Request."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/v1/traces", json={})
        assert res.status_code == 400
        assert "No valid spans parsed" in res.json()["detail"]


@pytest.mark.asyncio
async def test_api_experiments_run_endpoint():
    """Executes /api/v1/experiments/run and verifies output structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/experiments/run",
            json={
                "name": "Integration Test Experiment",
                "dataset_id": "api_test_dataset",
                "agent_mode": "fixed_v2",
                "agent_id": "test_agent",
                "agent_version": "2.0.0",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Integration Test Experiment"
        assert data["total_samples"] >= 1
        assert "mean_score" in data

        # Verify listing experiments
        list_res = await client.get("/api/v1/experiments")
        assert list_res.status_code == 200
        exps = list_res.json()
        assert len(exps) >= 1
