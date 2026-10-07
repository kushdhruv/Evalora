# 🔱 Evalora: Framework-Agnostic Agent Evaluation & Observability Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![OpenTelemetry](https://img.shields.io/badge/Telemetry-OpenTelemetry%20%2F%20OpenInference-purple.svg)](https://opentelemetry.io/)
[![Architecture](https://img.shields.io/badge/Graph_Engine-NetworkX%20DAG-darkgreen.svg)](https://networkx.org/)
[![Tests](https://img.shields.io/badge/Tests-21%20Passing%20(100%25)-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero-Cost](https://img.shields.io/badge/Local_Run-100%25_Free_&_Offline-orange.svg)](#-zero-cost-offline-mode-default)

> **A production-grade, framework-agnostic platform that converts non-deterministic agent execution traces into canonical Trajectory DAGs, performs causal failure root-cause analysis, evaluates long-horizon memory, and enforces CI/CD regression quality gates.**

---

## 📑 Table of Contents

- [Overview & Problem Statement](#-overview--problem-statement)
- [System Architecture](#-system-architecture)
- [Core Architectural Pillars](#-core-architectural-pillars)
  - [1. 4-Layer Gated Evaluation Pipeline](#1-4-layer-gated-evaluation-pipeline)
  - [2. Causal Failure Taxonomy & Root-Cause Engine](#2-causal-failure-taxonomy--root-cause-engine)
  - [3. In-Situ Long-Horizon Memory Auditor](#3-in-situ-long-horizon-memory-auditor)
  - [4. Real-Time Agent-Health Web Dashboard](#4-real-time-agent-health-web-dashboard)
  - [5. Native OpenClaw Plugin (`openclaw-aieval`)](#5-native-openclaw-plugin-openclaw-aieval)
  - [6. CI/CD Quality Gate CLI (`aieval gate`)](#6-cicd-quality-gate-cli-aieval-gate)
- [Quick Start Guide](#-quick-start-guide)
  - [1. Installation](#1-installation)
  - [2. Zero-Cost Offline Mode (Default)](#2-zero-cost-offline-mode-default)
  - [3. Live LLM Judge Mode (Google Gemini, OpenAI, Groq)](#3-live-llm-judge-mode-google-gemini-openai-groq)
- [Interactive Dashboard & Live Demo Walkthrough](#-interactive-dashboard--live-demo-walkthrough)
- [OpenClaw Plugin Quickstart](#-openclaw-plugin-quickstart)
- [REST API Specification](#-rest-api-specification)
- [Verification & Automated Test Suite](#-verification--automated-test-suite)
- [Documentation Index](#-documentation-index)
- [License](#-license)

---

## 🎯 Overview & Problem Statement

Autonomous AI agents fail differently from traditional microservices:
1. **Error Masking & Cascading**: A tool failure early in an execution (e.g., an SQL syntax error) causes downstream agents to hallucinate workarounds, resulting in an ungrounded final outcome. Traditional tracing blames the final step; **Ai_EvalGod isolates the primary root fault**.
2. **Framework Lock-In**: Evaluation tools often require specific agent SDKs. **Ai_EvalGod is framework-agnostic**, ingesting standard OpenTelemetry (OTLP) and OpenInference payloads from LangChain, AutoGen, CrewAI, OpenClaw, or custom Python/Node runtimes.
3. **Expensive, Redundant Judging**: Running frontier LLMs as judges over hundreds of intermediate steps is slow and costly. **Ai_EvalGod employs a 4-tier gated pipeline** that short-circuits evaluation when fatal deterministic errors occur.

---

## 🏗️ System Architecture

```
                                  AGENT RUNTIMES
       [ LangChain ]     [ AutoGen / CrewAI ]     [ OpenClaw Agents ]     [ Custom Python/TS ]
             │                     │                       │                      │
             └─────────────────────┼───────────────────────┴──────────────────────┘
                                   │ OpenTelemetry (OTLP / OpenInference)
                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        AI_EVALGOD BACKEND SERVICE (FastAPI)                            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  1. Ingestion & Normalizer (OTLPIngestService)                                         │
│     • Maps raw spans into canonical AgentEvents (PLAN, TOOL_CALL, MEMORY, OUTCOME)      │
│                                                                                        │
│  2. Trajectory DAG Reconstructor (TrajectoryBuilder - NetworkX)                        │
│     • Temporal Sequence Edges  • Sub-Task Invocation Edges  • Data-Flow Dependency     │
│                                                                                        │
│  3. 4-Layer Gated Evaluator Pipeline                                                   │
│     ┌───────────────────────────────────────────────────────────────────────────────┐  │
│     │ Layer 1: Deterministic  ──► Fatal Error? ──[ YES ]──► Short-circuit to L4   │  │
│     │            │ [Pass]                                                           │  │
│     │ Layer 2: Semantic (Embeddings / Token Relevance)                              │  │
│     │            │ [Pass]                                                           │  │
│     │ Layer 3: Structured LLM Judge (LiteLLM / Gemini / OpenAI / Groq / Ollama)     │  │
│     │            │                                                                  │  │
│     │ Layer 4: Trajectory Graph Fidelity (Goal Alignment & Recovery Path)           │  │
│     └────────────────────────────────────┬──────────────────────────────────────────┘  │
│                                          │                                             │
│  4. Causal Failure & Blame Engine (CausalFailureAnalyzer)                              │
│     • Reverse topological DAG traversal isolates root causes from downstream symptoms  │
│                                                                                        │
│  5. In-Situ Memory Auditor (AMA-Bench Inspired)                                        │
│     • Evaluates retrieval precision, information staleness, and causal tool usage      │
│                                                                                        │
│  6. Persistent Storage (SQLite WAL / PostgreSQL)                                       │
│     • Preserves Trajectories, Evaluations, Failures, and RootCauses                    │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
       📊 AGENT-HEALTH WEB DASHBOARD                  🚦 CI/CD REGRESSION CLI
          (Interactive Graph UI at /dashboard)          (`aieval gate` exits 0 / 1)
```

---

## 🧩 Core Architectural Pillars

### 1. 4-Layer Gated Evaluation Pipeline
Evaluation is organized into four hierarchical layers with intelligent short-circuiting:

- **Layer 1: Deterministic Evaluator**: Validates JSON schema adherence, unauthorized tool invocations, execution timeouts, token budgets, and uncaught exceptions.
- **Layer 2: Semantic Evaluator**: Evaluates retrieved memory relevance, context overlap, and citation groundedness using cosine similarity.
- **Layer 3: Structured LLM Judge**: Employs frontier LLMs (via LiteLLM provider routing) to score reasoning depth, argument correctness, and error recovery. Automatically falls back to an offline heuristic engine if no API keys are configured.
- **Layer 4: Trajectory Graph Evaluator**: Operates over the complete execution DAG to score goal progression, plan-action alignment, and topological efficiency.
- **Short-Circuit Gating**: If Layer 1 detects a fatal tool error or crash, the pipeline short-circuits Layers 2 and 3, saving latency, token costs, and API quota.

---

### 2. Causal Failure Taxonomy & Root-Cause Engine
Every agent error is mapped into an explicit 6-tier taxonomy:

| Category | Description | Typical Real-World Trigger |
| :--- | :--- | :--- |
| **`planning`** | Flawed task breakdown or impossible plan | Infinite loop or cyclic dependency in subtasks |
| **`tool`** | Malformed parameters, runtime crash, schema mismatch | Database SQL syntax error, 404 API endpoint |
| **`context_memory`** | Missing knowledge, stale state, context overflow | Agent acts on outdated customer records |
| **`reasoning_state`** | Logical hallucination despite valid inputs | Agent inverts logic or ignores tool results |
| **`environment`** | Third-party service downtime or transient network drop | Cloud provider 503 Service Unavailable |
| **`outcome`** | Final answer is inaccurate, incomplete, or hazardous | Customer query left unresolved |

**Root-Cause Blame Algorithm**:
Instead of blaming the final failed outcome node, the `CausalFailureAnalyzer` computes reverse topological reaches from terminal failures back to the earliest anomalous node in the trajectory DAG.

---

### 3. In-Situ Long-Horizon Memory Auditor
Inspired by recent benchmarks (*AMA-Bench*), the memory auditor observes real agent interactions without synthetic probes:
- **Retrieval Relevance**: Measures cosine similarity between the current query and retrieved memory items.
- **Information Staleness**: Tracks the age of facts stored in memory vs their last updated timestamp.
- **Context Retention**: Detects whether crucial constraints established in step $N$ are retained or forgotten by step $N + K$.
- **Causal Attribution**: Verifies whether retrieved facts were actually utilized in subsequent tool invocations.

---

### 4. Real-Time Agent-Health Web Dashboard
Inspired by OpenSearch's `agent-health` architecture, the embedded web dashboard at `http://127.0.0.1:8000/dashboard` provides:
- **Live Fleet Telemetry**: Success rates, average latency, total trajectory counts, and tool distribution histograms.
- **Auto-Sync Polling**: Automatically refreshes live agent executions every 3 seconds.
- **Interactive SVG Trajectory DAG**: Renders sequence dependencies, parent-child invocation trees, and data-flow edges with color-coded status badges.
- **Root Cause & Blame Inspector**: Highlights the isolated initial fault node in red and details error rationale.
- **Golden Path Benchmark Comparator**: Compares actual agent tool trajectories against the ideal golden execution sequence.
- **One-Click Live Agent Runner**: Executes flawed (`v1`) and fixed (`v2`) agent runs live against a real SQLite database.

---

### 5. Native OpenClaw Plugin (`openclaw-aieval`)
The repository includes a production-ready OpenClaw plugin located in [`plugins/openclaw-aieval/`](file:///plugins/openclaw-aieval/):
- **Lifecycle Interception**: Hooks into `before_tool_call`, `after_tool_call`, and `on_agent_finish`.
- **Introspection Tools**: Equips OpenClaw agents with native tools (`aieval_get_health`, `aieval_analyze_root_cause`, `aieval_compare_golden_path`) so agents can inspect and recover from their own failures.
- **Standards-Compliant**: Verified via standalone Node.js integration tests.

---

### 6. CI/CD Quality Gate CLI (`aieval gate`)
Automates PR quality gates in continuous integration pipelines:
```powershell
python -m cli.main gate --experiment exp-1 --threshold 0.85 --max-latency 5000.0
```
- **Exit Code `0`**: Trajectory passes evaluation and regression thresholds. PR passes.
- **Exit Code `1`**: Trajectory fails or latency regresses beyond tolerance. PR is blocked.

---

## 🚀 Quick Start Guide

### 1. Installation
Clone the repository and install dependencies:

```powershell
# Clone the repository
git clone https://github.com/kushdhruv/Evalora.git
cd Evalora

# Install Python requirements
pip install -r requirements.txt
# (or: pip install fastapi uvicorn pydantic sqlalchemy networkx litellm httpx pytest pytest-asyncio python-dotenv)
```

---

### 2. Zero-Cost Offline Mode (Default)
**Zero API keys are mandatory.** Out of the box, the platform operates entirely locally using SQLite, local deterministic evaluators, semantic checks, NetworkX DAG analysis, and offline heuristic judging:

```powershell
# Start the FastAPI server and Dashboard
uvicorn server.main:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)** in your browser.

---

### 3. Live LLM Judge Mode (Google Gemini, OpenAI, Groq)
To enable live Layer-3 LLM judging with frontier models:

1. Copy the example configuration:
   ```powershell
   cp .env.example .env
   ```
2. Open [`.env`](file:///c:/Ai_EvalGod/.env) and configure your preferred provider:
   ```ini
   # Database
   DATABASE_URL=sqlite:///data/aieval.db

   # Option A: Google Gemini (Free tier available)
   GEMINI_API_KEY=your_gemini_api_key_here
   LLM_JUDGE_MODEL=gemini/gemini-2.5-flash

   # Option B: OpenAI
   # OPENAI_API_KEY=sk-...
   # LLM_JUDGE_MODEL=gpt-4o-mini

   # Option C: Groq (Ultra-fast Llama-3.3-70b)
   # GROQ_API_KEY=gsk_...
   # LLM_JUDGE_MODEL=groq/llama-3.3-70b-versatile

   # Option D: Offline Ollama (100% Free)
   # OLLAMA_API_BASE=http://localhost:11434
   # LLM_JUDGE_MODEL=ollama/llama3:8b
   ```
3. Restart the server. The LLM judge will automatically switch to your configured live model.

---

## 🖥️ Interactive Dashboard & Live Demo Walkthrough

### 1. Execute the End-to-End Demo Agents
Run the demonstration script comparing an agent with a faulty tool (`Agent v1`) against an agent with self-correction (`Agent v2`):

```powershell
python -m demo_agent.run_demo
```

### 2. Explore the Web Dashboard
Navigate to **`http://127.0.0.1:8000/dashboard`**:
1. **Health Summary**: Review total trajectories, success rates, and tool execution breakdown.
2. **Select Trajectory**: Choose between `v1` (flawed run) and `v2` (remediated run).
3. **Interactive Graph**: Observe how the SVG DAG highlights the primary root-cause failure in red.
4. **Golden Path Comparison**: See the exact tool diff between the agent's run and the target sequence.
5. **Live Trigger**: Click **Run Flawed Agent (v1)** or **Run Fixed Agent (v2)** to watch live executions stream in real time.

---

## 🔌 OpenClaw Plugin Quickstart

The native OpenClaw plugin connects OpenClaw agents directly to the evaluation platform:

### 1. Configuration in `openclaw.json`
```json
{
  "plugins": {
    "openclaw-aieval": {
      "endpoint": "http://127.0.0.1:8000",
      "agentId": "customer_support_agent",
      "agentVersion": "1.0.0",
      "autoTrace": true,
      "minScoreThreshold": 0.85
    }
  }
}
```

### 2. Verify Plugin Integration
Run the automated test script:
```powershell
node plugins/openclaw-aieval/test.js
```

---

## 📡 REST API Specification

The FastAPI backend exposes standard OpenTelemetry ingestion and evaluation endpoints:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/v1/traces` | `POST` | Ingests OTLP JSON trace spans and computes the Trajectory DAG and root-cause blame. |
| `/api/v1/trajectories` | `GET` | Lists all stored agent trajectories with summary metrics. |
| `/api/v1/trajectories/{trace_id}` | `GET` | Returns full trajectory details, DAG nodes, evaluations, and root causes. |
| `/api/v1/health-summary` | `GET` | Returns fleet metrics (success rate, tool distribution, avg latency, failure breakdown). |
| `/api/v1/golden-path/compare` | `POST` | Compares a trace's tool sequence against an expected Golden Path. |
| `/api/v1/agent/run-live` | `POST` | Executes Agent v1 or v2 live against the local SQLite database. |
| `/dashboard` | `GET` | Renders the production-grade interactive Agent-Health HTML dashboard. |

---

## 🧪 Verification & Automated Test Suite

The platform includes a comprehensive automated test suite covering schemas, ingestion, DAG building, 4-layer evaluators, causal analysis, memory audits, regression gates, persistent database storage, and API endpoints:

```powershell
# Run the full test suite
pytest tests/
```

### Test Results:
```
tests/test_api_server.py .                                               [  4%]
tests/test_causal.py .                                                   [  9%]
tests/test_e2e_demo.py .                                                 [ 14%]
tests/test_evaluators.py ..                                              [ 23%]
tests/test_memory.py ..                                                  [ 33%]
tests/test_regression.py ...                                             [ 47%]
tests/test_schemas.py .....                                              [ 71%]
tests/test_storage.py .                                                  [ 76%]
tests/test_telemetry.py ...                                              [ 90%]
tests/test_trajectory.py ..                                              [100%]

============================= 21 passed in 1.15s =============================
```

---

## 🔬 Architectural & Theoretical Foundations

Evalora's design grounds itself on modern frontier research in multi-agent observability and causal evaluation:

- **OpenTelemetry & OpenInference**: Standardized, vendor-neutral span formats allowing direct drop-in telemetry from LangChain, CrewAI, AutoGen, and OpenClaw without proprietary SDK locks.
- **Topological Causal Discovery**: Root-cause detection models execution traces as Directed Acyclic Graphs (DAGs), traversing dependency chains upstream to identify the true failure originator rather than superficial downstream symptoms.
- **In-Situ Memory Benchmarking (AMA-Bench Inspired)**: Non-invasive auditing of agent long-horizon memory—evaluating retrieval relevance, context staleness, retention degradation, and causal utilization during live production tasks.
- **Gated Evaluation Economics**: Multi-tier cascading evaluation pipeline with short-circuit gates prevents wasteful, expensive LLM judge calls when lower-level deterministic constraints fail.

---

## 📜 License

This project is licensed under the **MIT License**. Free for commercial and research use.
