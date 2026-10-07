"""tests/test_api_server.py: Tests for FastAPI endpoints and Agent-Health features."""

import pytest
from httpx import ASGITransport, AsyncClient
from server.main import app


@pytest.mark.asyncio
async def test_otlp_ingestion_and_trajectory_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "resourceSpans": [
                {
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "trace-api-123",
                                    "spanId": "span-01",
                                    "name": "plan_step",
                                    "startTimeUnixNano": 1710000000000000000,
                                    "endTimeUnixNano": 1710000000100000000,
                                    "attributes": [
                                        {"key": "agent.step_type", "value": {"stringValue": "plan"}}
                                    ],
                                },
                                {
                                    "traceId": "trace-api-123",
                                    "spanId": "span-02",
                                    "name": "sql_tool",
                                    "startTimeUnixNano": 1710000000200000000,
                                    "endTimeUnixNano": 1710000000300000000,
                                    "status": {"code": "ERROR"},
                                    "attributes": [
                                        {"key": "openinference.span.kind", "value": {"stringValue": "TOOL"}},
                                        {"key": "tool.name", "value": {"stringValue": "sql_query"}},
                                        {"key": "error.message", "value": {"stringValue": "no such column"}},
                                    ],
                                },
                                {
                                    "traceId": "trace-api-123",
                                    "spanId": "span-03",
                                    "name": "final_outcome",
                                    "startTimeUnixNano": 1710000000400000000,
                                    "endTimeUnixNano": 1710000000500000000,
                                    "attributes": [
                                        {"key": "agent.step_type", "value": {"stringValue": "outcome"}},
                                        {"key": "output.value", "value": {"stringValue": "Failed to query database."}},
                                    ],
                                },
                            ]
                        }
                    ]
                }
            ]
        }

        # 1. Post OTLP trace
        res = await client.post("/v1/traces", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["trace_id"] == "trace-api-123"
        assert data["nodes_count"] == 3
        assert data["has_root_cause"] is True
        assert data["root_cause"]["primary_category"] == "tool"

        # 2. Query Trajectory details
        res_traj = await client.get("/api/v1/trajectories/trace-api-123")
        assert res_traj.status_code == 200
        traj_data = res_traj.json()
        assert len(traj_data["trajectory"]["nodes"]) == 3
        assert traj_data["root_cause"] is not None

        # 3. Query Health Summary (agent-health feature)
        res_health = await client.get("/api/v1/health-summary")
        assert res_health.status_code == 200
        health = res_health.json()
        assert health["total_trajectories"] >= 1
        assert "sql_query" in health["tool_usage_counts"]

        # 4. Golden Path comparison
        res_gp = await client.post(
            "/api/v1/golden-path/compare",
            json={
                "actual_trace_id": "trace-api-123",
                "expected_tool_sequence": ["sql_query"],
            },
        )
        assert res_gp.status_code == 200
        gp_data = res_gp.json()
        assert gp_data["exact_match"] is True

        # 5. Check dashboard HTML
        res_dash = await client.get("/dashboard")
        assert res_dash.status_code == 200
        assert "Agent Health" in res_dash.text
        assert "Trajectory Observability" in res_dash.text
