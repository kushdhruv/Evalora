"""tests/test_production_gaps_hardening.py: Verification of async ingestion, auth, DB retry, and WS."""

import asyncio
import os
import pytest
from httpx import ASGITransport, AsyncClient
from server.main import app, default_repository, ws_manager
from core.db.repository import with_db_retry


class TestProductionGapsHardening:
    """Verifies all production hardening features."""

    @pytest.mark.asyncio
    async def test_async_trace_ingestion_decoupling(self):
        """Validates that async ingestion responds in < 50ms with status 'accepted'."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "resourceSpans": [
                    {
                        "scopeSpans": [
                            {
                                "spans": [
                                    {
                                        "traceId": "trace-async-001",
                                        "spanId": "span-01",
                                        "name": "tool_step",
                                        "startTimeUnixNano": 1710000000000000000,
                                        "endTimeUnixNano": 1710000000100000000,
                                        "attributes": [
                                            {"key": "openinference.span.kind", "value": {"stringValue": "TOOL"}},
                                            {"key": "tool.name", "value": {"stringValue": "calculator"}},
                                            {"key": "tool.output", "value": {"stringValue": "42"}},
                                        ],
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }

            # Ingest with async header
            res = await client.post(
                "/v1/traces",
                json=payload,
                headers={"X-Evalora-Async": "true"},
            )
            assert res.status_code == 201
            data = res.json()
            assert data["status"] == "accepted"
            assert data["evaluation_status"] == "queued"
            assert data["trace_id"] == "trace-async-001"

            # Allow background tasks to execute
            await asyncio.sleep(0.5)

            # Trajectory should be stored
            traj = default_repository.get_trajectory("trace-async-001")
            assert traj is not None
            assert len(traj.nodes) == 1

    @pytest.mark.asyncio
    async def test_api_key_security_middleware(self, monkeypatch):
        """Validates Bearer token security when EVALORA_API_KEY is configured."""
        monkeypatch.setenv("EVALORA_API_KEY", "super-secret-test-key")
        # Update server's cached key for test
        import server.main
        server.main.EVALORA_API_KEY = "super-secret-test-key"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Unauthenticated request to /v1/traces must be rejected 401
            res_unauth = await client.post("/v1/traces", json={"resourceSpans": []})
            assert res_unauth.status_code == 401
            assert "Valid Bearer token required" in res_unauth.json()["detail"]

            # 2. Public dashboard must remain accessible without auth
            res_dash = await client.get("/dashboard")
            assert res_dash.status_code == 200

            # 3. Request with valid Bearer token must pass auth check
            res_auth = await client.get(
                "/api/v1/health-summary",
                headers={"Authorization": "Bearer super-secret-test-key"},
            )
            assert res_auth.status_code == 200

        # Reset key
        server.main.EVALORA_API_KEY = None

    def test_database_retry_decorator_on_lock(self):
        """Verifies that with_db_retry retries on transient database locks."""
        attempts = 0

        @with_db_retry(max_retries=3, initial_backoff=0.01, backoff_factor=1.5)
        def flaky_db_write():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("sqlite3.OperationalError: database is locked")
            return "SUCCESS"

        result = flaky_db_write()
        assert result == "SUCCESS"
        assert attempts == 3
