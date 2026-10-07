"""server/main.py: FastAPI Server and Production-Grade Agent-Health Dashboard."""

import asyncio
from dotenv import load_dotenv

load_dotenv()
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from core.agent.runtime import execute_real_agent_v1, execute_real_agent_v2
from core.causal.analyzer import CausalFailureAnalyzer
from core.db.repository import default_repository
from core.evaluators.pipeline import EvaluatorPipeline
from core.memory.auditor import MemoryTelemetryAuditor
from core.models.schema import (
    DatasetItem,
    Evaluation,
    Experiment,
    Failure,
    GateDecision,
    RegressionResult,
    RootCause,
    Trajectory,
)
from core.regression.analyzer import RegressionAnalyzer
from core.regression.dataset import DatasetCurationService
from core.telemetry.ingest import OTLPIngestService
from core.trajectory.builder import TrajectoryBuilder

app = FastAPI(
    title="Agent Evaluation & Observability Platform",
    description="Framework-agnostic agent telemetry, causal DAG analysis, and CI regression gating.",
    version="1.0.0",
)

pipeline = EvaluatorPipeline()


# -----------------------------------------------------------------------------
# Root Redirect to Dashboard
# -----------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root path to interactive dashboard."""
    return RedirectResponse(url="/dashboard")


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------

class GoldenPathRequest(BaseModel):
    actual_trace_id: str
    expected_tool_sequence: List[str]
    expected_outcome_substring: Optional[str] = None


class CurateTraceRequest(BaseModel):
    dataset_id: str = "default_regression_set"
    custom_prompt: Optional[str] = None
    expected_outcome: Optional[str] = None


class RunAgentRequest(BaseModel):
    agent_mode: str = "flawed_v1"  # "flawed_v1" or "fixed_v2"
    prompt: Optional[str] = None


# -----------------------------------------------------------------------------
# Live Real-Time Agent Execution Trigger
# -----------------------------------------------------------------------------

@app.post("/api/v1/agent/run-live")
async def run_live_agent(req: RunAgentRequest):
    """Executes a real agent workflow, captures live trace, evaluates and persists to database."""
    default_prompt = (
        req.prompt
        or "Check the overdue balance for customer acct_982 and email the summary to their billing address."
    )

    if req.agent_mode == "fixed_v2":
        tracer = execute_real_agent_v2(default_prompt)
    else:
        tracer = execute_real_agent_v1(default_prompt)

    trajectory = tracer.to_trajectory()
    default_repository.save_spans(tracer.spans)
    default_repository.save_trajectory(trajectory)

    # Run evaluations
    eval_result = await pipeline.run(trajectory)
    default_repository.save_evaluations(trajectory.trace_id, eval_result["evaluations"])
    default_repository.save_failures(trajectory.trace_id, eval_result["failures"])

    # Run root cause analysis if failures occurred
    root_cause = None
    if eval_result["failures"]:
        analyzer = CausalFailureAnalyzer(trajectory)
        root_cause = analyzer.identify_root_cause(eval_result["failures"])
        if root_cause:
            default_repository.save_root_cause(trajectory.trace_id, root_cause)

    return {
        "status": "success",
        "agent_mode": req.agent_mode,
        "trace_id": trajectory.trace_id,
        "nodes_count": len(trajectory.nodes),
        "mean_score": eval_result["mean_score"],
        "passed": eval_result["passed"],
        "root_cause": root_cause.model_dump() if root_cause else None,
    }


# -----------------------------------------------------------------------------
# Telemetry Ingestion (OTLP Standard)
# -----------------------------------------------------------------------------

@app.post("/v1/traces", status_code=status.HTTP_201_CREATED)
async def ingest_otlp_traces(payload: Dict[str, Any]):
    """Ingests OTLP JSON traces, reconstructs trajectory DAG, runs evaluations & causal analysis."""
    spans = OTLPIngestService.parse_otlp_json(payload)
    if not spans:
        raise HTTPException(status_code=400, detail="No valid spans parsed from payload")

    default_repository.save_spans(spans)
    events = OTLPIngestService.process_trace(spans)
    trace_id = spans[0].trace_id

    # Reconstruct Trajectory DAG
    trajectory = TrajectoryBuilder.build_trajectory(events, raw_spans=spans)
    default_repository.save_trajectory(trajectory)

    # Execute 4-Layer Evaluators
    eval_result = await pipeline.run(trajectory)
    default_repository.save_evaluations(trace_id, eval_result["evaluations"])
    default_repository.save_failures(trace_id, eval_result["failures"])

    # Execute Causal Root-Cause Discovery if failures detected
    root_cause = None
    if eval_result["failures"]:
        analyzer = CausalFailureAnalyzer(trajectory)
        root_cause = analyzer.identify_root_cause(eval_result["failures"])
        if root_cause:
            default_repository.save_root_cause(trace_id, root_cause)

    # Run Memory Telemetry Audit
    memory_audit = MemoryTelemetryAuditor.audit_trajectory(trajectory)

    return {
        "status": "success",
        "trace_id": trace_id,
        "nodes_count": len(trajectory.nodes),
        "edges_count": len(trajectory.edges),
        "mean_score": eval_result["mean_score"],
        "passed": eval_result["passed"],
        "failures_count": len(eval_result["failures"]),
        "has_root_cause": root_cause is not None,
        "root_cause": root_cause.model_dump() if root_cause else None,
        "memory_audit": memory_audit.model_dump(),
    }


# -----------------------------------------------------------------------------
# Observability & Trajectory Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/v1/trajectories")
async def list_trajectories():
    return [t.model_dump() for t in default_repository.list_trajectories()]


@app.get("/api/v1/trajectories/{trace_id}")
async def get_trajectory_details(trace_id: str):
    trajectory = default_repository.get_trajectory(trace_id)
    if not trajectory:
        raise HTTPException(status_code=404, detail="Trajectory not found")

    evaluations = default_repository.get_evaluations(trace_id)
    failures = default_repository.get_failures(trace_id)
    root_cause = default_repository.get_root_cause(trace_id)
    memory_audit = MemoryTelemetryAuditor.audit_trajectory(trajectory)

    return {
        "trajectory": trajectory.model_dump(),
        "evaluations": [e.model_dump() for e in evaluations],
        "failures": [f.model_dump() for f in failures],
        "root_cause": root_cause.model_dump() if root_cause else None,
        "memory_audit": memory_audit.model_dump(),
    }


@app.get("/api/v1/health-summary")
async def get_health_summary():
    """Inspired by OpenSearch agent-health: aggregates activity, tool usage, cost, and failure distribution."""
    return default_repository.get_health_summary()


@app.post("/api/v1/golden-path/compare")
async def compare_golden_path(req: GoldenPathRequest):
    """Compares actual trajectory against expected golden path tool sequence."""
    trajectory = default_repository.get_trajectory(req.actual_trace_id)
    if not trajectory:
        raise HTTPException(status_code=404, detail="Trajectory not found")

    actual_tools = [
        n.payload.get("tool_call", {}).get("tool_name")
        for n in trajectory.nodes
        if n.event_type.value == "tool_call"
    ]

    matches = [a == e for a, e in zip(actual_tools, req.expected_tool_sequence)]
    match_ratio = (
        sum(matches) / max(len(req.expected_tool_sequence), len(actual_tools))
        if actual_tools or req.expected_tool_sequence
        else 1.0
    )

    return {
        "trace_id": req.actual_trace_id,
        "actual_tool_sequence": actual_tools,
        "expected_tool_sequence": req.expected_tool_sequence,
        "sequence_match_ratio": round(match_ratio, 3),
        "exact_match": actual_tools == req.expected_tool_sequence,
    }


# -----------------------------------------------------------------------------
# Dataset & Regression Endpoints
# -----------------------------------------------------------------------------

@app.post("/api/v1/datasets/{dataset_id}/items/from-trace/{trace_id}")
async def curate_trace_to_dataset(dataset_id: str, trace_id: str, req: CurateTraceRequest):
    trajectory = default_repository.get_trajectory(trace_id)
    if not trajectory:
        raise HTTPException(status_code=404, detail="Trajectory not found")

    item = DatasetCurationService.create_item_from_trajectory(
        trajectory=trajectory,
        dataset_id=dataset_id,
        custom_input_prompt=req.custom_prompt,
        expected_outcome=req.expected_outcome,
    )
    default_repository.save_dataset_item(item)
    return item.model_dump()


@app.get("/api/v1/datasets")
async def list_datasets():
    return default_repository.list_datasets()


@app.get("/api/v1/datasets/{dataset_id}/items")
async def get_dataset_items(dataset_id: str):
    return [i.model_dump() for i in default_repository.get_dataset_items(dataset_id)]


# -----------------------------------------------------------------------------
# Production-Grade Agent-Health Inspired Web Dashboard
# -----------------------------------------------------------------------------

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """High-density real-time dashboard inspired by OpenSearch agent-health."""
    summary = default_repository.get_health_summary()
    trajectories = default_repository.list_trajectories(limit=25)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Health & Causal Trajectory Observability</title>
    <style>
        :root {{
            --bg: #090d16;
            --surface: #111827;
            --surface-elevated: #1a2234;
            --surface-hover: #222e47;
            --border: #2d3748;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #3b82f6;
            --primary-glow: rgba(59, 130, 246, 0.25);
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --danger-glow: rgba(239, 68, 68, 0.35);
            --card-radius: 10px;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; }}
        body {{ background: var(--bg); color: var(--text-main); padding: 20px; font-size: 14px; min-height: 100vh; }}
        
        /* Top Navigation Header */
        .topbar {{ display: flex; justify-content: space-between; align-items: center; padding-bottom: 16px; margin-bottom: 20px; border-bottom: 1px solid var(--border); }}
        .brand {{ display: flex; align-items: center; gap: 12px; }}
        .brand-icon {{ font-size: 26px; }}
        .brand-title h1 {{ font-size: 19px; font-weight: 700; color: #fff; letter-spacing: -0.02em; }}
        .brand-title p {{ color: var(--text-muted); font-size: 12px; margin-top: 2px; }}
        .header-actions {{ display: flex; align-items: center; gap: 12px; }}
        
        .live-beacon {{ display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600; color: #34d399; background: rgba(16, 185, 129, 0.12); padding: 4px 10px; border-radius: 9999px; border: 1px solid rgba(16, 185, 129, 0.3); }}
        .pulse-dot {{ width: 8px; height: 8px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981; animation: pulse 2s infinite; }}
        @keyframes pulse {{ 0% {{ opacity: 1; transform: scale(1); }} 50% {{ opacity: 0.4; transform: scale(0.85); }} 100% {{ opacity: 1; transform: scale(1); }} }}
        
        .btn {{ padding: 7px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; border: 1px solid transparent; transition: all 0.15s ease; display: inline-flex; align-items: center; gap: 6px; }}
        .btn-primary {{ background: var(--primary); color: #fff; }}
        .btn-primary:hover {{ background: #2563eb; box-shadow: 0 0 10px var(--primary-glow); }}
        .btn-danger {{ background: rgba(239, 68, 68, 0.15); color: #fca5a5; border-color: rgba(239, 68, 68, 0.4); }}
        .btn-danger:hover {{ background: rgba(239, 68, 68, 0.25); }}
        .btn-success {{ background: rgba(16, 185, 129, 0.15); color: #6ee7b7; border-color: rgba(16, 185, 129, 0.4); }}
        .btn-success:hover {{ background: rgba(16, 185, 129, 0.25); }}
        .btn-secondary {{ background: var(--surface-elevated); color: var(--text-main); border-color: var(--border); }}
        .btn-secondary:hover {{ background: var(--surface-hover); }}

        /* KPI Stat Cards (Agent-Health Grid) */
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 20px; }}
        .kpi-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--card-radius); padding: 16px 18px; }}
        .kpi-title {{ font-size: 11px; text-transform: uppercase; color: var(--text-muted); font-weight: 600; letter-spacing: 0.05em; margin-bottom: 6px; display: flex; justify-content: space-between; }}
        .kpi-value {{ font-size: 24px; font-weight: 700; }}
        .val-green {{ color: #34d399; }}
        .val-blue {{ color: #60a5fa; }}
        .val-orange {{ color: #fbbf24; }}

        /* Main Workspace: 3 Columns Layout */
        .workspace {{ display: grid; grid-template-columns: 320px 1fr 340px; gap: 18px; min-height: 580px; }}
        
        .panel {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--card-radius); display: flex; flex-direction: column; overflow: hidden; }}
        .panel-header {{ padding: 12px 16px; border-bottom: 1px solid var(--border); font-size: 13px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.01); }}

        /* Left Column: Trace Session List */
        .search-box {{ padding: 10px 14px; border-bottom: 1px solid var(--border); }}
        .search-input {{ width: 100%; padding: 6px 10px; background: var(--surface-elevated); border: 1px solid var(--border); border-radius: 6px; color: #fff; font-size: 12px; outline: none; }}
        .search-input:focus {{ border-color: var(--primary); }}
        .trace-list {{ list-style: none; overflow-y: auto; flex: 1; padding: 10px; }}
        .trace-item {{ padding: 10px 12px; border-radius: 8px; margin-bottom: 6px; border: 1px solid transparent; background: var(--surface-elevated); cursor: pointer; transition: all 0.15s ease; }}
        .trace-item:hover {{ background: var(--surface-hover); border-color: var(--border); }}
        .trace-item.active {{ background: #1e293b; border-color: var(--primary); box-shadow: 0 0 10px rgba(59, 130, 246, 0.15); }}
        .item-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }}
        .item-id {{ font-family: monospace; font-size: 12px; font-weight: 600; color: #e2e8f0; }}
        .item-status {{ font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; }}
        .status-pass {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
        .status-fail {{ background: rgba(239, 68, 68, 0.2); color: #f87171; }}
        .item-meta {{ font-size: 11px; color: var(--text-muted); display: flex; justify-content: space-between; }}

        /* Center Column: Trajectory DAG Viewer */
        .dag-viewport {{ flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; align-items: center; background: #070a13; }}
        .node-card {{ width: 100%; max-width: 480px; background: var(--surface-elevated); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; margin: 4px 0; cursor: pointer; transition: transform 0.1s, box-shadow 0.1s; position: relative; }}
        .node-card:hover {{ transform: translateY(-1px); border-color: #4b5563; }}
        .node-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
        .node-title {{ font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px; }}
        .node-latency {{ font-size: 11px; font-family: monospace; color: var(--text-muted); }}
        .node-desc {{ font-size: 12px; color: #cbd5e1; font-family: monospace; word-break: break-all; }}
        
        /* Causal Status Styles */
        .node-plan {{ border-left: 4px solid #60a5fa; }}
        .node-healthy {{ border-left: 4px solid #34d399; }}
        .node-root-cause {{ border: 2px solid #ef4444; background: #2a0e14; box-shadow: 0 0 16px var(--danger-glow); }}
        .node-cascade {{ border-left: 4px solid #f59e0b; background: rgba(245, 158, 11, 0.05); }}
        .dag-arrow {{ color: #4b5563; font-size: 18px; margin: 2px 0; }}

        /* Right Column: Diagnostic & Tool Analytics */
        .right-section {{ display: flex; flex-direction: column; gap: 14px; overflow-y: auto; padding: 14px; }}
        .diag-box {{ background: var(--surface-elevated); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }}
        .diag-title {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); margin-bottom: 8px; }}
        .rca-alert {{ background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 6px; padding: 10px; margin-bottom: 10px; }}
        .rca-alert h4 {{ color: #f87171; font-size: 13px; font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; }}
        .rca-alert p {{ color: #e2e8f0; font-size: 12px; line-height: 1.5; }}
        
        .tool-bar {{ margin-bottom: 10px; }}
        .tool-bar-top {{ display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 3px; }}
        .tool-track {{ height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden; }}
        .tool-fill {{ height: 100%; background: var(--primary); border-radius: 3px; }}

        /* Modal for Node Inspection */
        .modal {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 1000; align-items: center; justify-content: center; }}
        .modal-content {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; width: 560px; max-width: 90%; max-height: 80vh; overflow-y: auto; padding: 20px; }}
    </style>
</head>
<body>

    <!-- Top Navigation Header -->
    <div class="topbar">
        <div class="brand">
            <div class="brand-icon">🛡️</div>
            <div class="brand-title">
                <h1>Agent Health & Causal Observability</h1>
                <p>Telemetry-native Trajectory Graphs • Root Cause Analysis • Golden Path Evaluation</p>
            </div>
        </div>
        <div class="header-actions">
            <div class="live-beacon"><span class="pulse-dot"></span> LIVE AUTO-SYNC (3s)</div>
            <button class="btn btn-danger" onclick="triggerLiveAgent('flawed_v1')">⚡ Run Flawed V1</button>
            <button class="btn btn-success" onclick="triggerLiveAgent('fixed_v2')">✨ Run Fixed V2</button>
            <a href="/docs" target="_blank" class="btn btn-secondary">API Docs</a>
        </div>
    </div>

    <!-- Agent-Health Key Performance Indicators -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-title"><span>Total Trajectories</span> <span>📈</span></div>
            <div class="kpi-value" id="kpi-total">{summary.get('total_trajectories', 0)}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title"><span>Health Success Rate</span> <span>🛡️</span></div>
            <div class="kpi-value val-green" id="kpi-rate">{int(summary.get('success_rate', 1.0) * 100)}%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title"><span>Token Cost Estimate</span> <span>💵</span></div>
            <div class="kpi-value val-blue" id="kpi-cost">${summary.get('total_cost_usd', 0.0):.4f}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title"><span>Avg Execution Latency</span> <span>⚡</span></div>
            <div class="kpi-value val-orange" id="kpi-latency">{summary.get('avg_latency_ms', 0.0):.1f}ms</div>
        </div>
    </div>

    <!-- Main 3-Column Workspace -->
    <div class="workspace">
        
        <!-- Left: Trace Sessions List -->
        <div class="panel">
            <div class="panel-header">
                <span>Agent Execution Sessions</span>
                <span style="font-size:11px;color:var(--text-muted);" id="trace-count">{len(trajectories)} traces</span>
            </div>
            <div class="search-box">
                <input type="text" class="search-input" id="search-box" placeholder="Filter by trace ID or agent..." oninput="filterTraces()">
            </div>
            <ul class="trace-list" id="trace-list">
                {"".join([f'''
                <li class="trace-item" data-id="{t.trace_id}" onclick="selectTrace('{t.trace_id}')">
                    <div class="item-top">
                        <span class="item-id">{t.agent_id[:16]}...</span>
                        <span class="item-status {'status-pass' if t.is_success else 'status-fail'}">
                            {'HEALTHY' if t.is_success else 'FAILED'}
                        </span>
                    </div>
                    <div class="item-meta">
                        <span>{t.trace_id[:12]}</span>
                        <span>{t.total_latency_ms:.0f}ms</span>
                    </div>
                </li>
                ''' for t in trajectories]) if trajectories else '<li style="padding:14px;color:var(--text-muted);font-size:12px;">No traces yet. Click "Run Flawed V1" above to capture live telemetry.</li>'}
            </ul>
        </div>

        <!-- Center: Interactive Causal Trajectory DAG Viewer -->
        <div class="panel">
            <div class="panel-header">
                <span id="dag-header-title">Causal Execution Trajectory (DAG)</span>
                <button class="btn btn-secondary" style="padding:3px 8px;font-size:11px;" onclick="curateToRegression()">+ Add to Regression Set</button>
            </div>
            <div class="dag-viewport" id="dag-viewport">
                <p style="color:var(--text-muted);margin-top:80px;font-size:13px;">Select a trace from the left panel to inspect its execution graph.</p>
            </div>
        </div>

        <!-- Right: Diagnostic RCA & Agent-Health Tool Stats -->
        <div class="panel">
            <div class="panel-header">
                <span>Causal Fault Localization & Health</span>
            </div>
            <div class="right-section">
                <!-- Root Cause Diagnostic Box -->
                <div class="diag-box" id="rca-box">
                    <div class="diag-title">Root Cause Blame Attribution</div>
                    <div id="rca-content">
                        <p style="color:var(--text-muted);font-size:12px;">Select a trace to view automated root cause diagnosis.</p>
                    </div>
                </div>

                <!-- Tool Usage Activity (Agent-Health) -->
                <div class="diag-box">
                    <div class="diag-title">Tool Usage Frequency</div>
                    <div id="tools-content">
                        {"".join([f'''
                        <div class="tool-bar">
                            <div class="tool-bar-top"><span>{tool}</span><span>{count} calls</span></div>
                            <div class="tool-track"><div class="tool-fill" style="width: {min(100, count*20)}%;"></div></div>
                        </div>
                        ''' for tool, count in summary.get('tool_usage_counts', {}).items()]) or '<p style="color:var(--text-muted);font-size:12px;">No tools recorded yet.</p>'}
                    </div>
                </div>

                <!-- Golden Path Benchmark -->
                <div class="diag-box">
                    <div class="diag-title">Golden Path Benchmark</div>
                    <p style="color:var(--text-muted);font-size:11px;margin-bottom:8px;">Expected Sequence: <code>sqlite_query ──▶ send_email</code></p>
                    <div id="golden-path-status" style="font-size:12px;color:#cbd5e1;">Awaiting trace selection...</div>
                </div>
            </div>
        </div>

    </div>

    <!-- Node Detail Modal -->
    <div class="modal" id="node-modal" onclick="closeModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <h3 id="modal-title" style="margin-bottom:10px;font-size:15px;">Node Details</h3>
            <pre id="modal-json" style="background:#0b0f19;padding:12px;border-radius:6px;font-size:11px;overflow-x:auto;color:#38bdf8;border:1px solid var(--border);"></pre>
            <div style="margin-top:14px;text-align:right;">
                <button class="btn btn-secondary" onclick="document.getElementById('node-modal').style.display='none'">Close</button>
            </div>
        </div>
    </div>

    <script>
        let currentTraceId = null;

        // Auto-select first trace on load if present
        window.addEventListener('DOMContentLoaded', () => {{
            const first = document.querySelector('.trace-item');
            if (first) {{
                first.click();
            }}
            // Start real-time polling every 3 seconds
            setInterval(syncDashboard, 3000);
        }});

        async function triggerLiveAgent(mode) {{
            const res = await fetch('/api/v1/agent/run-live', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ agent_mode: mode }})
            }});
            const data = await res.json();
            await syncDashboard();
            selectTrace(data.trace_id);
        }}

        async function syncDashboard() {{
            try {{
                const res = await fetch('/api/v1/health-summary');
                const summary = await res.json();
                document.getElementById('kpi-total').innerText = summary.total_trajectories;
                document.getElementById('kpi-rate').innerText = Math.round(summary.success_rate * 100) + '%';
                document.getElementById('kpi-cost').innerText = '$' + summary.total_cost_usd.toFixed(4);
                document.getElementById('kpi-latency').innerText = summary.avg_latency_ms.toFixed(1) + 'ms';

                // Refresh trajectories list
                const tRes = await fetch('/api/v1/trajectories');
                const trajs = await tRes.json();
                document.getElementById('trace-count').innerText = trajs.length + ' traces';
                
                const list = document.getElementById('trace-list');
                list.innerHTML = trajs.map(t => `
                    <li class="trace-item ${{t.trace_id === currentTraceId ? 'active' : ''}}" data-id="${{t.trace_id}}" onclick="selectTrace('${{t.trace_id}}')">
                        <div class="item-top">
                            <span class="item-id">${{t.agent_id.substring(0, 16)}}...</span>
                            <span class="item-status ${{t.is_success ? 'status-pass' : 'status-fail'}}">
                                ${{t.is_success ? 'HEALTHY' : 'FAILED'}}
                            </span>
                        </div>
                        <div class="item-meta">
                            <span>${{t.trace_id.substring(0, 12)}}</span>
                            <span>${{Math.round(t.total_latency_ms)}}ms</span>
                        </div>
                    </li>
                `).join('');
            }} catch (e) {{}}
        }}

        async function selectTrace(traceId) {{
            currentTraceId = traceId;
            document.querySelectorAll('.trace-item').forEach(el => {{
                el.classList.toggle('active', el.getAttribute('data-id') === traceId);
            }});

            const res = await fetch('/api/v1/trajectories/' + traceId);
            const data = await res.json();
            document.getElementById('dag-header-title').innerText = 'Causal Trajectory: ' + traceId;

            const viewport = document.getElementById('dag-viewport');
            viewport.innerHTML = '';

            const nodes = data.trajectory.nodes;
            const rcNodeId = data.root_cause ? data.root_cause.primary_failure_node_id : null;

            nodes.forEach((n, idx) => {{
                const card = document.createElement('div');
                card.className = 'node-card ';
                
                const isRC = (n.node_id === rcNodeId);
                const isToolErr = n.payload.tool_call && n.payload.tool_call.is_error;
                
                let icon = '⚙️';
                let typeLabel = 'TOOL';
                if (n.event_type === 'plan') {{ icon = '📋'; typeLabel = 'PLAN'; card.className += 'node-plan'; }}
                else if (n.event_type === 'final_outcome') {{ icon = '🎯'; typeLabel = 'OUTCOME'; }}
                
                if (isRC) {{
                    card.className += 'node-root-cause';
                    typeLabel = '🚨 PRIMARY ROOT CAUSE';
                }} else if (isToolErr) {{
                    card.className += 'node-cascade';
                    typeLabel = '⚠️ CASCADE ERROR';
                }} else if (n.event_type !== 'plan') {{
                    card.className += 'node-healthy';
                }}

                let desc = '';
                if (n.payload.tool_call) {{
                    desc = `Tool: <strong>${{n.payload.tool_call.tool_name}}</strong>`;
                    if (n.payload.tool_call.error_message) {{
                        desc += `<br><span style="color:#f87171;">${{n.payload.tool_call.error_message}}</span>`;
                    }}
                }} else if (n.payload.content) {{
                    desc = n.payload.content.substring(0, 90) + '...';
                }}

                card.innerHTML = `
                    <div class="node-header">
                        <span class="node-title">${{icon}} ${{n.label}} <span style="font-size:10px;color:var(--text-muted);">[${{typeLabel}}]</span></span>
                        <span class="node-latency">${{n.payload.tool_call ? n.payload.tool_call.execution_time_ms + 'ms' : ''}}</span>
                    </div>
                    <div class="node-desc">${{desc}}</div>
                `;
                card.onclick = () => showModal(n);
                viewport.appendChild(card);

                if (idx < nodes.length - 1) {{
                    const arrow = document.createElement('div');
                    arrow.className = 'dag-arrow';
                    arrow.innerText = '▼';
                    viewport.appendChild(arrow);
                }}
            }});

            // Update Root Cause Diagnostic Box
            const rcaBox = document.getElementById('rca-content');
            if (data.root_cause) {{
                rcaBox.innerHTML = `
                    <div class="rca-alert">
                        <h4>🚨 Root Cause Detected: ${{data.root_cause.primary_category.toUpperCase()}}</h4>
                        <p>${{data.root_cause.explanation}}</p>
                    </div>
                    <p style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">Propagation Path:</p>
                    <p style="font-family:monospace;font-size:11px;background:#090d16;padding:6px;border-radius:4px;border:1px solid var(--border);color:#fca5a5;">
                        ${{data.root_cause.propagation_chain.join(' ──▶ ')}}
                    </p>
                    <p style="font-size:11px;margin-top:8px;">Diagnostic Confidence: <strong style="color:#34d399;">${{Math.round(data.root_cause.confidence_score * 100)}}%</strong></p>
                `;
            }} else {{
                rcaBox.innerHTML = '<p style="color:#34d399;font-size:12px;">✅ No execution faults or failure cascades detected. Trajectory is healthy.</p>';
            }}

            // Evaluate Golden Path
            const gpRes = await fetch('/api/v1/golden-path/compare', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    actual_trace_id: traceId,
                    expected_tool_sequence: ['sqlite_query', 'send_email']
                }})
            }});
            const gpData = await gpRes.json();
            document.getElementById('golden-path-status').innerHTML = `
                Sequence Match: <strong>${{Math.round(gpData.sequence_match_ratio * 100)}}%</strong><br>
                Actual: <code>${{gpData.actual_tool_sequence.join(' ──▶ ') || 'none'}}</code><br>
                Verdict: <span style="color:${{gpData.exact_match ? '#34d399' : '#f87171'}};">${{gpData.exact_match ? '✅ Exact Golden Path Match' : '❌ Sequence Deviation'}}</span>
            `;
        }}

        function showModal(node) {{
            document.getElementById('modal-title').innerText = node.label + ' (' + node.node_id + ')';
            document.getElementById('modal-json').innerText = JSON.stringify(node.payload, null, 2);
            document.getElementById('node-modal').style.display = 'flex';
        }}

        function closeModal(e) {{
            document.getElementById('node-modal').style.display = 'none';
        }}

        async function curateToRegression() {{
            if (!currentTraceId) return alert('Select a trace first.');
            const res = await fetch('/api/v1/datasets/production_regressions/items/from-trace/' + currentTraceId, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ dataset_id: 'production_regressions' }})
            }});
            const data = await res.json();
            alert('Trace successfully curated into regression dataset "production_regressions" (Item ID: ' + data.item_id + ')');
        }}

        function filterTraces() {{
            const val = document.getElementById('search-box').value.toLowerCase();
            document.querySelectorAll('.trace-item').forEach(el => {{
                el.style.display = el.innerText.toLowerCase().includes(val) ? 'block' : 'none';
            }});
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
