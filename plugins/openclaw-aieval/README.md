# OpenClaw Plugin: AI EvalGod Observability & Causal Analysis (`openclaw-aieval`)

> **Native OpenClaw plugin that captures agent execution traces, constructs causal trajectory DAGs, identifies root-cause failure cascades, and enforces regression quality gates.**

---

## 🌟 Features for OpenClaw Agents

1. **Automatic Zero-Code Telemetry**:
   - Hooks into OpenClaw's lifecycle (`before_tool_call`, `after_tool_call`, `on_agent_finish`).
   - Captures real tool inputs, outputs, exceptions, and latency in standard OpenTelemetry (OTLP) format.
   - Automatically streams telemetry directly to the local or remote `Ai_EvalGod` evaluation server.

2. **Causal Root-Cause Discovery Tool (`aieval_analyze_root_cause`)**:
   - Allows OpenClaw agents to introspect their own failures.
   - Reconstructs the execution DAG and isolates the primary fault (e.g. database schema error) from downstream cascading errors (e.g. failed email delivery).

3. **Live Health & Activity Monitoring (`aieval_get_health`)**:
   - Queries OpenSearch `agent-health` inspired metrics: success rates, tool call distributions, token cost, and average latency.

4. **Golden Path Trajectory Benchmark (`aieval_compare_golden_path`)**:
   - Evaluates whether the agent adhered to the expected sequence of tools.

---

## 📦 Installation & Setup

### 1. Local Link / Workspace Installation
If running OpenClaw locally, you can install the plugin directly from the directory:

```bash
openclaw plugins install ./plugins/openclaw-aieval
```

Or copy the `plugins/openclaw-aieval` directory into your OpenClaw `plugins/` folder.

### 2. Configuration (`openclaw.json` / `config.json`)

Add the plugin configuration to your OpenClaw setup:

```json
{
  "plugins": {
    "openclaw-aieval": {
      "endpoint": "http://localhost:8000",
      "agentId": "my_openclaw_assistant",
      "agentVersion": "1.0.0",
      "autoTrace": true,
      "minScoreThreshold": 0.85
    }
  }
}
```

---

## 🛠️ Registered Agent Tools

When enabled, your OpenClaw agent has access to the following built-in diagnostic tools:

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `aieval_get_health` | *None* | Returns live success rate, token costs, and tool frequency stats. |
| `aieval_analyze_root_cause` | `traceId` (string) | Reconstructs the trajectory DAG and returns the primary root cause diagnostic. |
| `aieval_compare_golden_path` | `traceId` (string), `expectedTools` (array) | Computes sequence alignment against expected tool steps. |

---

## 🖥️ Live Real-Time Dashboard

Whenever your OpenClaw agent runs, its execution graph is rendered live in the dashboard:

👉 **[http://localhost:8000/dashboard](http://localhost:8000/dashboard)**

- Real-time session explorer (polls every 3 seconds).
- Color-coded Causal Trajectory DAG (Blue = Plan, Green = Healthy Tool, Red = Root Cause, Orange = Cascade Error).
- Tool usage frequency charts and golden path verification.
