/**
 * OpenClaw Plugin: openclaw-aieval
 * Framework-agnostic OpenTelemetry tracing, causal trajectory reconstruction,
 * root-cause blame attribution, and regression quality gating.
 */

const http = require("http");
const https = require("https");
const { URL } = require("url");

class AiEvalClient {
  constructor(endpoint) {
    this.endpoint = endpoint.replace(/\/+$/, "");
  }

  async _request(method, path, body = null) {
    const targetUrl = new URL(this.endpoint + path);
    const transport = targetUrl.protocol === "https:" ? https : http;
    const payload = body ? JSON.stringify(body) : null;

    const options = {
      hostname: targetUrl.hostname,
      port: targetUrl.port || (targetUrl.protocol === "https:" ? 443 : 80),
      path: targetUrl.pathname + targetUrl.search,
      method: method,
      headers: {
        "Content-Type": "application/json",
        ...(payload ? { "Content-Length": Buffer.byteLength(payload) } : {}),
      },
      timeout: 5000,
    };

    return new Promise((resolve, reject) => {
      const req = transport.request(options, (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          try {
            const parsed = JSON.parse(data);
            resolve(parsed);
          } catch (e) {
            resolve(data);
          }
        });
      });
      req.on("error", reject);
      req.on("timeout", () => {
        req.destroy();
        reject(new Error("Request timed out"));
      });
      if (payload) req.write(payload);
      req.end();
    });
  }

  async postTrace(otlpPayload) {
    return this._request("POST", "/v1/traces", otlpPayload);
  }

  async getHealthSummary() {
    return this._request("GET", "/api/v1/health-summary");
  }

  async getTrajectory(traceId) {
    return this._request("GET", `/api/v1/trajectories/${traceId}`);
  }

  async compareGoldenPath(traceId, expectedSequence) {
    return this._request("POST", "/api/v1/golden-path/compare", {
      actual_trace_id: traceId,
      expected_tool_sequence: expectedSequence,
    });
  }
}

/**
 * OpenClaw Plugin Registration Function
 * @param {Object} api OpenClaw plugin API interface
 */
function register(api) {
  const config = api.getConfig() || {};
  const endpoint = config.endpoint || "http://localhost:8000";
  const agentId = config.agentId || "openclaw_agent";
  const agentVersion = config.agentVersion || "1.0.0";
  const autoTrace = config.autoTrace !== false;

  const client = new AiEvalClient(endpoint);

  // In-memory session trace buffers
  const activeTraces = new Map();

  function getOrCreateTrace(sessionId) {
    if (!activeTraces.has(sessionId)) {
      activeTraces.set(sessionId, {
        traceId: "trace_claw_" + Math.random().toString(36).substring(2, 10),
        spans: [],
        toolStartTimes: new Map(),
      });
    }
    return activeTraces.get(sessionId);
  }

  // --------------------------------------------------------------------------
  // 1. AUTOMATIC OBSERVABILITY HOOKS
  // --------------------------------------------------------------------------

  if (autoTrace && api.on) {
    // Hook: Before Tool Call
    api.on("before_tool_call", async (context) => {
      try {
        const sessionId = context.sessionId || "default_session";
        const sessionTrace = getOrCreateTrace(sessionId);
        const callId = context.callId || context.toolName + "_" + Date.now();
        sessionTrace.toolStartTimes.set(callId, {
          start: Date.now(),
          args: context.args || context.parameters || {},
        });
      } catch (err) {
        api.logger?.debug?.("[openclaw-aieval] before_tool_call error: " + err.message);
      }
    });

    // Hook: After Tool Call
    api.on("after_tool_call", async (context) => {
      try {
        const sessionId = context.sessionId || "default_session";
        const sessionTrace = getOrCreateTrace(sessionId);
        const callId = context.callId || context.toolName + "_" + Date.now();
        const startRecord = sessionTrace.toolStartTimes.get(callId) || {
          start: Date.now() - 50,
          args: {},
        };

        const now = Date.now();
        const isError = Boolean(context.error);

        const span = {
          spanId: "span_" + Math.random().toString(36).substring(2, 10),
          traceId: sessionTrace.traceId,
          name: "tool_" + context.toolName,
          startTimeUnixNano: startRecord.start * 1000000,
          endTimeUnixNano: now * 1000000,
          status: { code: isError ? "ERROR" : "OK" },
          attributes: [
            { key: "openinference.span.kind", value: { stringValue: "TOOL" } },
            { key: "tool.name", value: { stringValue: context.toolName } },
            { key: "tool.parameters", value: { stringValue: JSON.stringify(startRecord.args) } },
            {
              key: isError ? "error.message" : "tool.output",
              value: { stringValue: isError ? String(context.error) : JSON.stringify(context.result || {}) },
            },
          ],
        };

        sessionTrace.spans.push(span);
        sessionTrace.toolStartTimes.delete(callId);
      } catch (err) {
        api.logger?.debug?.("[openclaw-aieval] after_tool_call error: " + err.message);
      }
    });

    // Hook: On Agent Execution Finish
    api.on("on_agent_finish", async (context) => {
      try {
        const sessionId = context.sessionId || "default_session";
        const sessionTrace = activeTraces.get(sessionId);
        if (!sessionTrace || sessionTrace.spans.length === 0) return;

        const now = Date.now();
        // Add final outcome span
        sessionTrace.spans.push({
          spanId: "span_outcome_" + Math.random().toString(36).substring(2, 10),
          traceId: sessionTrace.traceId,
          name: "agent_final_outcome",
          startTimeUnixNano: now * 1000000,
          endTimeUnixNano: now * 1000000,
          status: { code: "OK" },
          attributes: [
            { key: "agent.step_type", value: { stringValue: "outcome" } },
            { key: "output.value", value: { stringValue: String(context.finalResponse || "Completed") } },
          ],
        });

        const otlpPayload = {
          resourceSpans: [
            {
              scopeSpans: [{ spans: sessionTrace.spans }],
            },
          ],
        };

        // Export directly to Ai_EvalGod server
        await client.postTrace(otlpPayload);
        api.logger?.info?.(`[openclaw-aieval] Telemetry exported: trace ${sessionTrace.traceId}`);
        activeTraces.delete(sessionId);
      } catch (err) {
        api.logger?.warn?.("[openclaw-aieval] Failed to export trace: " + err.message);
      }
    });
  }

  // --------------------------------------------------------------------------
  // 2. AGENT-CALLABLE TOOLS
  // --------------------------------------------------------------------------

  // Tool 1: Get Agent Health Summary
  api.registerTool?.({
    name: "aieval_get_health",
    description: "Fetch live OpenClaw agent health metrics including success rate, token cost, and tool usage.",
    parameters: {
      type: "object",
      properties: {},
    },
    handler: async () => {
      try {
        return await client.getHealthSummary();
      } catch (err) {
        return { error: "Failed to connect to Ai_EvalGod engine at " + endpoint + ": " + err.message };
      }
    },
  });

  // Tool 2: Causal Root-Cause Discovery
  api.registerTool?.({
    name: "aieval_analyze_root_cause",
    description: "Analyze a recorded execution trace to find the primary root cause behind any failure cascade.",
    parameters: {
      type: "object",
      properties: {
        traceId: { type: "string", description: "The trace ID to diagnose" },
      },
      required: ["traceId"],
    },
    handler: async ({ traceId }) => {
      try {
        const details = await client.getTrajectory(traceId);
        return {
          traceId,
          nodesCount: details.trajectory.nodes.length,
          rootCause: details.root_cause || "No causal failures found in this trajectory",
          evaluations: details.evaluations,
        };
      } catch (err) {
        return { error: "Could not fetch trajectory analysis: " + err.message };
      }
    },
  });

  // Tool 3: Golden Path Trajectory Comparison
  api.registerTool?.({
    name: "aieval_compare_golden_path",
    description: "Compare the agent's executed tool sequence against an expected golden path benchmark.",
    parameters: {
      type: "object",
      properties: {
        traceId: { type: "string", description: "The trace ID to evaluate" },
        expectedTools: {
          type: "array",
          items: { type: "string" },
          description: "Ordered list of expected tool names (e.g. ['sqlite_query', 'send_email'])",
        },
      },
      required: ["traceId", "expectedTools"],
    },
    handler: async ({ traceId, expectedTools }) => {
      try {
        return await client.compareGoldenPath(traceId, expectedTools);
      } catch (err) {
        return { error: "Failed golden path comparison: " + err.message };
      }
    },
  });

  api.logger?.info?.(`[openclaw-aieval] Plugin initialized. Telemetry target: ${endpoint}`);
}

module.exports = { register, AiEvalClient };
