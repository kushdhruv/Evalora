"""tests/test_openclaw.py: Validates OpenClaw plugin schema and mock API contracts."""

import json
import os
import pytest
from httpx import ASGITransport, AsyncClient
from server.main import app


def test_openclaw_plugin_manifest():
    plugin_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "plugins",
        "openclaw-aieval",
        "openclaw.plugin.json",
    )
    assert os.path.exists(plugin_path), "openclaw.plugin.json must exist"

    with open(plugin_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["id"] == "openclaw-aieval"
    assert data["version"] == "1.0.0"
    assert "capabilities" in data
    assert "tools" in data["capabilities"]
    tool_names = [t["name"] for t in data["capabilities"]["tools"]]
    assert "aieval_get_health" in tool_names
    assert "aieval_analyze_root_cause" in tool_names
    assert "aieval_compare_golden_path" in tool_names
    assert "aieval_gate_check" in tool_names


@pytest.mark.asyncio
async def test_openclaw_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health endpoint
        resp = await client.get("/api/v1/health-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_trajectories" in data
        assert "success_rate" in data

        # 2. Golden path comparison
        gp_resp = await client.post(
            "/api/v1/golden-path/compare",
            json={
                "actual_trace_id": "non-existent-trace",
                "expected_tool_sequence": ["sqlite_query", "send_email"],
            },
        )
        # Should be 404 since trace doesn't exist
        assert gp_resp.status_code == 404
