/**
 * plugins/openclaw-aieval/test.js: Test script for OpenClaw plugin integration.
 */

const { AiEvalClient, register } = require("./index.js");

async function runTests() {
  console.log("=== Testing OpenClaw Plugin Integration ===");
  const client = new AiEvalClient("http://127.0.0.1:8000");

  try {
    // 1. Test Health Summary from Plugin Client
    console.log("[1] Testing client.getHealthSummary()...");
    const health = await client.getHealthSummary();
    console.log("    Success! Total Trajectories:", health.total_trajectories, "Success Rate:", (health.success_rate * 100) + "%");

    // 2. Test Mock OpenClaw API Registration
    console.log("\n[2] Testing register(mockOpenClawApi)...");
    const registeredTools = [];
    const registeredHooks = [];

    const mockApi = {
      getConfig: () => ({ endpoint: "http://127.0.0.1:8000", autoTrace: true }),
      on: (event, handler) => registeredHooks.push(event),
      registerTool: (toolDef) => registeredTools.push(toolDef.name),
      logger: {
        info: (msg) => console.log("    [OpenClaw Log]", msg),
        debug: () => {},
        warn: (msg) => console.warn("    [OpenClaw Warn]", msg),
      },
    };

    register(mockApi);
    console.log("    Registered Hooks:", registeredHooks);
    console.log("    Registered Tools:", registeredTools);

    console.log("\n✅ OpenClaw Plugin Test Passed successfully!");
  } catch (err) {
    console.error("❌ Test Failed:", err.message);
    process.exit(1);
  }
}

runTests();
