# 🔱 Evalora: Autonomous AI Agent Observability & Causal Evaluation Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![OpenTelemetry](https://img.shields.io/badge/Telemetry-OpenTelemetry%20%2F%20OpenInference-purple.svg)](https://opentelemetry.io/)
[![Architecture](https://img.shields.io/badge/Concurrency-Asyncio%20Gather%20%2B%20Semaphore-blueviolet.svg)](core/evaluators/pipeline.py)
[![CircuitBreaker](https://img.shields.io/badge/Loop_Protection-Sliding_Window_CircuitBreaker-crimson.svg)](core/sdk/tracer.py)
[![Tests](https://img.shields.io/badge/Tests-67%20Passing%20(100%25)-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero-Cost](https://img.shields.io/badge/Local_Run-100%25_Free_&_Offline-orange.svg)](#-zero-cost-offline-mode-default)

> **A production-grade, framework-agnostic platform that converts non-deterministic agent executions into canonical Trajectory DAGs, performs reverse topological causal root-cause analysis, audits long-horizon memory in-situ, streams real-time execution via WebSockets/SSE, and prevents runaway agent execution loops with sliding-window circuit breakers.**

---

## 📑 Table of Contents

- [Overview & Value Proposition](#-overview--value-proposition)
- [🔌 How to Integrate Evalora into Your Existing AI Project](#-how-to-integrate-evalora-into-your-existing-ai-project)
  - [Method 1: Drop-in Python SDK Plugin (`@observe` & `evalora`)](#method-1-drop-in-python-sdk-plugin-observe--evalora)
  - [Method 2: Multi-Agent Chat & Swarm Observability](#method-2-multi-agent-chat--swarm-observability)
  - [Method 3: Framework-Agnostic OpenTelemetry Exporter (OTLP)](#method-3-framework-agnostic-opentelemetry-exporter-otlp)
  - [Method 4: Native OpenClaw Agent Plugin](#method-4-native-openclaw-agent-plugin)
  - [Method 5: CI/CD Quality Gate in GitHub Actions](#method-5-cicd-quality-gate-in-github-actions)
- [System Architecture & Flow](#-system-architecture--flow)
- [Core Architectural Pillars](#-core-architectural-pillars)
  - [1. 4-Layer Concurrent Evaluation Pipeline](#1-4-layer-concurrent-evaluation-pipeline)
  - [2. Causal Failure Taxonomy & Root-Cause Attribution](#2-causal-failure-taxonomy--root-cause-attribution)
  - [3. Sliding-Window Loop Circuit Breaker](#3-sliding-window-loop-circuit-breaker)
  - [4. In-Situ Long-Horizon Memory Auditor](#4-in-situ-long-horizon-memory-auditor)
  - [5. Interactive Modern Observability & Evaluation Studio](#5-interactive-modern-observability--evaluation-studio)
- [Quick Start Guide](#-quick-start-guide)
  - [1. Installation](#1-installation)
  - [2. Zero-Cost Offline Mode (Default)](#2-zero-cost-offline-mode-default)
  - [3. Live LLM Judge Mode (Google Gemini, OpenAI, Groq)](#3-live-llm-judge-mode-google-gemini-openai-groq)
- [Interactive Dashboard & Live Agent Studio Walkthrough](#-interactive-dashboard--live-agent-studio-walkthrough)
- [REST & Real-Time Streaming API](#-rest--real-time-streaming-api)
- [Verification & Automated Test Suite (67 Passing)](#-verification--automated-test-suite-67-passing)
- [License](#-license)

---

## 🎯 Overview & Value Proposition

Autonomous AI agents fail fundamentally differently from traditional microservices:
1. **Error Masking & Cascades**: When a tool fails (e.g. malformed SQL query), the agent hallucinates workarounds rather than halting, corrupting downstream state. Traditional APMs blame the final failed step; **Evalora isolates the primary root fault**.
2. **Infinite Loops & Runaway Cost**: Agents can enter unrecoverable retry loops or ping-pong between identical tools. **Evalora's sliding-window `CircuitBreaker` halts execution** if identical tools or unhandled failures exceed safe thresholds.
3. **Multi-Agent Blindness**: In multi-agent swarms (Orchestrators, Workers, Specialists), tracking inter-agent messages, delegations, and responsibility handoffs is fragmented. **Evalora builds a unified cross-agent Trajectory DAG**.
4. **Evaluation Bottlenecks**: Sequential LLM judging over hundreds of steps creates immense latency and cost. **Evalora executes a 4-tier gated pipeline with bounded async concurrency (`asyncio.gather` + `Semaphore(5)`)**, short-circuiting downstream layers upon fatal errors.

---

## 🔌 How to Integrate Evalora into Your Existing AI Project

Integrating Evalora into your codebase takes **under 3 minutes** with zero breaking changes to your existing agent architecture.

### Method 1: Drop-in Python SDK Plugin (`@observe` & `evalora`)

Install the package:
```bash
pip install evalora
# Or install in editable mode from source:
pip install -e .
```

#### A. Decorator Approach (Recommended for existing tools & functions)
Wrap your agent tools and planning functions with `@observe`:

```python
from evalora import evalora, observe, trace_agent_execution

# 1. Initialize client once at startup (points to your local or deployed Evalora server)
evalora.init(
    endpoint="http://127.0.0.1:8000/v1/traces",
    agent_id="finance_assistant_v1",
    auto_flush=True,
    mask_pii=True, # Automatically redacts emails, SSNs, and credit cards
)

# 2. Decorate existing tool functions
@observe(name="database_query", span_type="tool")
def run_sql(query: str):
    # Your existing database query logic
    return [{"balance": 450.0, "status": "OVERDUE"}]

@observe(name="send_notification", span_type="tool")
async def send_email(to: str, subject: str, body: str):
    # Your async email delivery logic
    return {"status": "DELIVERED"}

# 3. Trace full agent execution sessions
async def handle_user_request(user_prompt: str):
    with trace_agent_execution(agent_id="finance_assistant_v1", session_id="user_session_982") as tracer:
        tracer.record_plan("Query customer balance and send invoice notice", steps=["query", "notify"])
        
        # Tools are automatically traced into the current execution DAG
        data = run_sql("SELECT balance FROM invoices WHERE acct_id = '982'")
        await send_email(to="billing@customer.com", subject="Notice", body=f"Balance: {data[0]['balance']}")
        
        tracer.record_outcome("Successfully verified and delivered invoice notice.", is_success=True)
```

#### B. Asynchronous Execution & Non-Blocking Flush
For high-throughput async agents (FastAPI, asyncio workers), flush telemetry non-blockingly:
```python
# Async non-blocking flush prevents freezing agent event loops
await evalora.aflush()
```

---

### Method 2: Multi-Agent Chat & Swarm Observability

When coordinating multiple agents (e.g. LangGraph, CrewAI, AutoGen, OpenAI Swarm), use Evalora's multi-agent tracing to track task delegations and peer chats:

```python
from evalora import AgentTracer

# 1. Main Orchestrator Tracer
orchestrator = AgentTracer(agent_id="orchestrator_agent", session_id="team_sprint_12")

# 2. Record Task Delegation to a Specialist
orchestrator.record_agent_delegation(
    delegator="orchestrator_agent",
    delegatee="sql_specialist",
    task="Retrieve overdue balance for account acct_982",
)

# 3. Specialist executes tool
result = orchestrator.execute_tool(
    tool_name="sqlite_query",
    tool_fn=my_sql_runner,
    agent_id="sql_specialist",
    query="SELECT balance FROM invoices WHERE id = 982",
)

# 4. Specialist sends chat message back to Orchestrator
orchestrator.record_agent_message(
    sender="sql_specialist",
    recipient="orchestrator_agent",
    content=f"Balance verified: ${result[0]['balance']}",
)

# 5. Synthesize outcome & export unified multi-agent DAG
orchestrator.record_outcome("Multi-agent task completed successfully", is_success=True)
orchestrator.flush("http://127.0.0.1:8000/v1/traces")
```

In the Evalora Web Studio, this immediately renders the full cross-agent interaction graph with inter-agent message nodes, subagent delegation edges, and latency waterfalls.

---

### Method 3: Framework-Agnostic OpenTelemetry Exporter (OTLP)

If you already use **LangChain**, **CrewAI**, **LlamaIndex**, or **OpenInference**, simply point your OpenTelemetry OTLP exporter to Evalora's ingestion endpoint:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://127.0.0.1:8000/v1/traces"
export OTEL_SERVICE_NAME="my_autonomous_agent"
```

Evalora ingests standard OTLP JSON spans, infers causal dependencies, reconstructs the Trajectory DAG, runs the 4-layer evaluation pipeline, and detects root causes automatically.

---

### Method 4: Native OpenClaw Agent Plugin

If using [OpenClaw](https://github.com/openclaw/openclaw), install our native bidirectional plugin:

```json
// openclaw.json
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

This equips OpenClaw agents with native self-healing introspection tools (`aieval_get_health`, `aieval_analyze_root_cause`, `aieval_compare_golden_path`) enabling agents to diagnose and recover from their own execution faults.

---

### Method 5: CI/CD Quality Gate in GitHub Actions

Block pull requests if an agent changes prompts or tools and regresses in quality or latency:

```yaml
# .github/workflows/agent_regression_gate.yml
name: Agent CI Regression Gate

on: [pull_request]

jobs:
  evalora-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e .
      - name: Run Evalora Quality Gate
        run: |
          python -m cli.main gate \
            --experiment pr-eval-candidate \
            --threshold 0.85 \
            --max-latency 4500.0
```
- **Exit Code `0`**: All evaluations and regression assertions pass. PR is green.
- **Exit Code `1`**: Quality drops or latency regresses beyond threshold. PR is blocked.

---

## 🏗️ System Architecture & Flow

```
                                  AGENT RUNTIMES
       [ LangChain ]     [ AutoGen / CrewAI ]     [ OpenClaw Agents ]     [ Custom Python / TS ]
             │                     │                       │                      │
             └─────────────────────┼───────────────────────┴──────────────────────┘
                                   │ OpenTelemetry (OTLP / OpenInference) or Evalora SDK
                                   ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        EVALORA BACKEND PLATFORM (FastAPI)                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  1. Ingestion & PII Normalizer (OTLPIngestService)                                     │
│     • Maps raw spans into canonical AgentEvents (PLAN, TOOL, MEMORY, OUTCOME, AGENT_MSG)│
│     • Redacts sensitive PII (emails, SSNs, credit cards) before persistence            │
│                                                                                        │
│  2. Trajectory DAG Reconstructor (TrajectoryBuilder - NetworkX)                        │
│     • Temporal Sequence Edges • Sub-Task Invocation Edges • Multi-Agent Message Edges  │
│                                                                                        │
│  3. Sliding-Window Circuit Breaker & Loop Detection                                   │
│     • Halts runaway execution if repeated calls >= 10 or consecutive errors >= 8       │
│                                                                                        │
│  4. 4-Layer Concurrent Evaluator Pipeline (Bounded Asyncio Semaphore(5))               │
│     ┌───────────────────────────────────────────────────────────────────────────────┐  │
│     │ Layer 1: Deterministic  ──► Fatal Error? ──[ YES ]──► Short-circuit to L4   │  │
│     │            │ [Pass]                                                           │  │
│     │ Layer 2: Semantic (Context Overlap & Groundedness)                            │  │
│     │            │ [Pass]                                                           │  │
│     │ Layer 3: Structured LLM Judge (LiteLLM: Gemini / OpenAI / Groq / Heuristic)   │  │
│     │            │                                                                  │  │
│     │ Layer 4: Trajectory Graph Fidelity (Goal Alignment & Recovery Path)           │  │
│     └────────────────────────────────────┬──────────────────────────────────────────┘  │
│                                          │                                             │
│  5. Causal Failure & Blame Engine (CausalFailureAnalyzer)                              │
│     • Reverse topological DAG traversal isolates root causes from downstream symptoms  │
│                                                                                        │
│  6. In-Situ Memory Auditor (AMA-Bench Inspired)                                        │
│     • Evaluates retrieval relevance, staleness, retention, and causal tool usage       │
│                                                                                        │
│  7. High-Concurrency Storage (SQLite WAL with StaticPool / PostgreSQL)                 │
│     • Resilient retry with exponential backoff on database locks                       │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
       📊 MODERN OBSERVABILITY STUDIO                 🚦 CI/CD REGRESSION GATE
          (Interactive Graph UI at /)                    (`aieval gate` exits 0 / 1)
```

---

## 🧩 Core Architectural Pillars

### 1. 4-Layer Concurrent Evaluation Pipeline
Evaluation is organized into four hierarchical layers with intelligent short-circuiting and bounded async concurrency:

- **Layer 1: Deterministic Evaluator**: Validates schema adherence, tool authorization, token budgets, execution timeouts, and uncaught exceptions.
- **Layer 2: Semantic Evaluator**: Computes cosine similarity across retrieved memory context, prompt groundedness, and semantic alignment.
- **Layer 3: Structured LLM Judge**: Employs frontier models via LiteLLM (Google Gemini, OpenAI, Groq, Ollama) with bounded semaphore parallelism (`asyncio.Semaphore(5)`). Automatically falls back to an offline heuristic scoring engine if no API keys are present.
- **Layer 4: Trajectory Graph Evaluator**: Operates on the full execution DAG to verify goal progression, plan fidelity, and path efficiency.
- **Short-Circuit Gating**: If Layer 1 detects a fatal tool error or crash, the pipeline short-circuits Layers 2 and 3, saving latency, token spend, and provider quota.

---

### 2. Causal Failure Taxonomy & Root-Cause Attribution
Errors are classified into a 6-tier canonical taxonomy:

| Category | Description | Typical Real-World Trigger |
| :--- | :--- | :--- |
| **`planning`** | Flawed task breakdown or impossible plan | Cyclic subtask dependency or impossible precondition |
| **`tool`** | Malformed parameters, runtime crash, schema mismatch | Database SQL syntax error, missing column, 404 endpoint |
| **`context_memory`** | Missing knowledge, stale state, context loss | Agent acts on outdated customer records |
| **`reasoning_state`** | Logical hallucination despite valid inputs | Agent inverts business logic or ignores valid tool output |
| **`environment`** | Third-party downtime or transient network drops | Cloud provider 503 Service Unavailable |
| **`outcome`** | Final answer is inaccurate, incomplete, or hazardous | User query left unresolved or hallucinated |

**Root-Cause Blame Algorithm**:
Instead of blaming the final failed outcome step, `CausalFailureAnalyzer` computes reverse topological reaches from terminal failures back to the earliest anomalous node in the trajectory DAG.

---

### 3. Sliding-Window Loop Circuit Breaker
Prevents catastrophic agent retry loops and runaway token billing:
- **Max Repeated Calls**: Halts execution if an agent invokes the same tool with identical parameters $\ge 10$ times (`EVALORA_MAX_REPEATED_CALLS`).
- **Max Consecutive Failures**: Halts execution if an agent accumulates $\ge 8$ consecutive unhandled failures (`EVALORA_MAX_CONSECUTIVE_FAILURES`).
- **Max Total Steps**: Halts execution if an agent exceeds $\ge 300$ steps (`EVALORA_MAX_TOTAL_STEPS`).
- Halts raise an `AgentLoopException`, gracefully creating an error span and recording a root-cause blame node in the trajectory.

---

### 4. In-Situ Long-Horizon Memory Auditor
Inspired by recent benchmarks (*AMA-Bench*), the memory auditor observes real agent interactions without synthetic probes:
- **Retrieval Relevance**: Cosine similarity between the active prompt and retrieved memory vectors.
- **Information Staleness**: Tracks the age of facts stored in memory versus their last updated timestamp.
- **Context Retention**: Detects whether constraints established in step $N$ are retained or forgotten by step $N + K$.
- **Causal Tool Usage**: Verifies whether retrieved facts were actually utilized in subsequent tool invocations.

---

### 5. Interactive Modern Observability & Evaluation Studio
The built-in web studio at `http://127.0.0.1:8000/` provides:
- **Fleet Telemetry KPI Strip**: Real-time fleet success rate, P95/P99 latency, token spend estimates, active tool invocation volume, and categorized failure distributions.
- **Interactive Causal DAG View**: Powered by `@xyflow/react` + Dagre auto-layout. Features dedicated node components for Plans, Tools, Memory, Outcomes, and Multi-Agent Messages with glowing root-cause blame propagation chains.
- **Span Waterfall Timeline**: Sub-millisecond Gantt duration distribution bars with visual start-offset positioning.
- **Side-by-Side Golden Path Comparator**: Levenshtein sequence alignment between actual tool execution paths and reference golden traces.
- **Deep Inspector Drawer**: Slide-out detail panel inspecting execution payloads, evaluator verdicts, in-situ memory retrieval audits, and 1-click CI regression dataset curation.
- **Interactive Live Agent Studio**: Run flawed (`v1`), self-correcting (`v2`), or collaborative multi-agent fleet workflows live against local databases with instant WebSocket updates.

---

## 🚀 Quick Start Guide

### 1. Installation
```bash
git clone https://github.com/kushdhruv/Evalora.git
cd Evalora

# Install dependencies and editable SDK
pip install -r requirements.txt
pip install -e .
```

---

### 2. Zero-Cost Offline Mode (Default)
**Zero external API keys are required.** Out of the box, the platform operates entirely locally using SQLite, local deterministic evaluators, semantic checks, NetworkX DAG analysis, and offline heuristic judging:

```bash
uvicorn server.main:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

---

### 3. Live LLM Judge Mode (Google Gemini, OpenAI, Groq)
To enable live Layer-3 LLM judging with frontier models:

1. Copy `.env.example`:
   ```bash
   cp .env.example .env
   ```
2. Configure your preferred provider in `.env`:
   ```ini
   # Database
   DATABASE_URL=sqlite:///data/aieval.db

   # Option A: Google Gemini (Free tier available)
   GEMINI_API_KEY=your_gemini_api_key_here
   LLM_JUDGE_MODEL=gemini/gemini-2.5-flash

   # Option B: OpenAI
   # OPENAI_API_KEY=sk-...
   # LLM_JUDGE_MODEL=gpt-4o-mini

   # Option C: Groq
   # GROQ_API_KEY=gsk_...
   # LLM_JUDGE_MODEL=groq/llama-3.3-70b-versatile
   ```
3. Restart the server. The LLM judge will automatically route requests through your live provider.

---

## 🖥️ Interactive Dashboard & Live Agent Studio Walkthrough

### 1. Run Live Demo Workflows
Execute the included demo agents comparing flawed, fixed, and multi-agent workflows:
```bash
python -m demo_agent.run_demo
```

### 2. Live Agent Studio
Navigate to `http://127.0.0.1:8000/#studio`:
1. Click **Run Flawed Agent (v1)** to witness a cascading database schema error correctly blamed on the SQL tool step.
2. Click **Run Fixed Agent (v2)** to watch an agent autonomously correct the schema join and succeed.
3. Click **Run Multi-Agent Fleet** to observe an Orchestrator delegate tasks to a Database Specialist and Comms Specialist, visualising inter-agent messages and collaborative DAGs in real time.

---

## 📡 REST & Real-Time Streaming API

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/v1/traces` | `POST` | Ingests OTLP / OpenInference JSON spans, builds DAG, and computes causal blame. |
| `/api/v1/trajectories` | `GET` | Lists all recorded agent trajectories with summary metrics. |
| `/api/v1/trajectories/{trace_id}` | `GET` | Returns full trajectory details, DAG nodes, evaluations, and root causes. |
| `/api/v1/health-summary` | `GET` | Returns fleet metrics (success rate, tool distribution, avg latency, failure breakdown). |
| `/api/v1/golden-path/compare` | `POST` | Compares a trace's tool sequence against an expected Golden Path. |
| `/api/v1/agent/run-live` | `POST` | Triggers live execution of `flawed_v1`, `fixed_v2`, or `multi_agent` workflows. |
| `/api/v1/events/stream` | `GET` | Real-time Server-Sent Events (SSE) streaming live trace ingestion events. |
| `/ws/live-traces` | `WebSocket`| Real-time bi-directional WebSocket stream for live trace and evaluation updates. |

---

## 🧪 Verification & Automated Test Suite (67 Passing)

Evalora features a rigorous automated test suite with **100% pass rate across 67 comprehensive tests**:

```bash
pytest tests/
============================= 67 passed in 34.01s =============================
```

### Test Coverage Highlights:
* [`tests/test_circuit_breaker.py`](tests/test_circuit_breaker.py): Sliding-window threshold verification ($\ge 10$ calls, $\ge 8$ failures, $\ge 300$ steps), environment variable overrides, and non-blocking `aflush()`.
* [`tests/test_multi_agent_observability.py`](tests/test_multi_agent_observability.py): Multi-agent chat, task delegation DAG reconstruction, collaborative execution, and PII redaction.
* [`tests/test_evaluators.py`](tests/test_evaluators.py): 4-layer gated pipeline with concurrent `asyncio.gather` and `Semaphore(5)`.
* [`tests/test_causal.py`](tests/test_causal.py): Reverse topological root-cause attribution and cascading blame paths.
* [`tests/test_openclaw.py`](tests/test_openclaw.py): OpenClaw plugin integration and self-healing introspection tools.
* [`tests/test_api_server.py`](tests/test_api_server.py): FastAPI endpoints, OTLP ingestion, health summaries, and live agent endpoints.
* [`tests/test_streaming.py`](tests/test_streaming.py): Server-Sent Events (SSE) and live trace streaming.
* [`tests/test_production_gaps_hardening.py`](tests/test_production_gaps_hardening.py): SQLite lock retry with exponential backoff and memory growth auditing.

---

## 📜 License

This project is licensed under the **MIT License**. Free for commercial and research use.
