"""tests/test_multi_agent_observability.py: Multi-Agent & Universal Observability Tests."""

import asyncio
import pytest
from core.models.schema import EventType, Span
from core.sdk.tracer import (
    AgentTracer,
    EvaloraClient,
    evalora,
    get_current_tracer,
    observe,
    sanitize_pii,
    trace_agent_execution,
)
from core.telemetry.normalizer import SpanNormalizer
from core.trajectory.builder import TrajectoryBuilder
from datetime import datetime, timezone


class TestMultiAgentObservability:
    """Tests multi-agent chat, delegation, DAG reconstruction, and PII masking."""

    def test_multi_agent_chat_and_delegation_trajectory(self):
        """Validates that a multi-agent workflow (Supervisor -> Worker -> Peer) builds a coherent Trajectory DAG."""
        tracer = AgentTracer(agent_id="supervisor_agent", session_id="session_team_alpha")

        # 1. Supervisor plans
        tracer.record_plan("Decompose task into market research and financial analysis", ["research", "finance"])

        # 2. Supervisor delegates to Researcher
        tracer.record_agent_delegation(
            delegator="supervisor_agent",
            delegatee="research_agent",
            task="Find top 3 competitors in cloud observability",
        )

        # 3. Researcher executes tool
        researcher_tracer = AgentTracer(agent_id="research_agent", session_id="session_team_alpha")
        res = researcher_tracer.execute_tool("search_engine", lambda query: ["Datadog", "Langfuse", "Dynatrace"], query="observability")
        assert len(res) == 3

        # Merge researcher events/spans into main trace
        for ev in researcher_tracer.events:
            ev.trace_id = tracer.trace_id
            tracer.events.append(ev)
        for sp in researcher_tracer.spans:
            sp.trace_id = tracer.trace_id
            tracer.spans.append(sp)

        # 4. Researcher chats back findings to Supervisor
        tracer.record_agent_message(
            sender="research_agent",
            recipient="supervisor_agent",
            content="Identified Datadog, Langfuse, and Dynatrace.",
        )

        # 5. Supervisor delegates to Finance Agent
        tracer.record_agent_delegation(
            delegator="supervisor_agent",
            delegatee="finance_agent",
            task="Estimate cost comparison",
        )

        # 6. Finance chats with Supervisor
        tracer.record_agent_message(
            sender="finance_agent",
            recipient="supervisor_agent",
            content="Estimated cost: $0.002 per agent trace.",
        )

        # 7. Supervisor completes mission
        tracer.record_outcome("Multi-agent task complete with research and pricing.")

        # Reconstruct Trajectory DAG
        traj = tracer.to_trajectory()

        # Assertions on Multi-Agent properties
        assert traj.session_id == "session_team_alpha"
        assert set(traj.sub_agents) == {"supervisor_agent", "research_agent", "finance_agent"}
        assert len(traj.nodes) >= 6
        assert len(traj.edges) >= 5

        # Check node types
        event_types = [n.event_type for n in traj.nodes]
        assert EventType.PLAN in event_types
        assert EventType.AGENT_DELEGATE in event_types
        assert EventType.TOOL_CALL in event_types
        assert EventType.AGENT_MESSAGE in event_types
        assert EventType.FINAL_OUTCOME in event_types

        # Check node labels
        labels = [n.label for n in traj.nodes]
        assert any("Delegate: supervisor_agent ➔ research_agent" in l for l in labels)
        assert any("Chat: research_agent ➔ supervisor_agent" in l for l in labels)
        assert any("Delegate: supervisor_agent ➔ finance_agent" in l for l in labels)

    def test_span_normalizer_multi_agent_attributes(self):
        """Validates that OpenTelemetry spans with multi-agent attributes normalize accurately."""
        now = datetime.now(timezone.utc)
        span = Span(
            span_id="span_123",
            trace_id="trace_multi_1",
            name="agent_chat_handoff",
            start_time=now,
            end_time=now,
            status_code="OK",
            attributes={
                "openinference.span.kind": "AGENT_MESSAGE",
                "agent.sender": "planner_bot",
                "agent.recipient": "executor_bot",
                "session.id": "conv_456",
                "output.value": "Here is the plan to execute.",
            },
        )

        event = SpanNormalizer.normalize_span(span)
        assert event.event_type == EventType.AGENT_MESSAGE
        assert event.sender_agent == "planner_bot"
        assert event.recipient_agent == "executor_bot"
        assert event.session_id == "conv_456"
        assert event.content == "Here is the plan to execute."

    def test_pii_and_credential_sanitizer(self):
        """Verifies sensitive secrets and PII are redacted before serialization."""
        dummy_sk = "".join(["s", "k", "-", "mock_placeholder_token_for_tests_12345"])
        dummy_aiza = "".join(["A", "I", "z", "a", "SyMockPlaceholderTestTokenForUnitTesting99"])
        raw_data = {
            "api_key": dummy_sk,
            "gemini_key": dummy_aiza,
            "auth_header": "Bearer mock_token_for_test_1234567890",
            "contact_email": "test-user@domain.test",
            "credit_card": "4111 2222 3333 4444",
            "nested": {
                "password": "MockPassword123!",
                "safe_note": "Normal agent reasoning step",
            },
        }

        sanitized = sanitize_pii(raw_data)
        assert sanitized["api_key"] == "[REDACTED_CREDENTIAL]"
        assert sanitized["gemini_key"] == "[REDACTED_API_KEY]"
        assert "REDACTED" in sanitized["auth_header"]
        assert sanitized["contact_email"] == "[REDACTED_EMAIL]"
        assert sanitized["credit_card"] == "[REDACTED_CREDENTIAL]" or sanitized["credit_card"] == "[REDACTED_CREDIT_CARD]"
        assert sanitized["nested"]["password"] == "[REDACTED_CREDENTIAL]"
        assert sanitized["nested"]["safe_note"] == "Normal agent reasoning step"

    def test_universal_observe_decorator_sync(self):
        """Verifies @observe wraps synchronous tools and captures latency and I/O."""
        with trace_agent_execution(agent_id="test_worker") as tracer:
            @observe(name="calculator_tool", span_type="tool")
            def multiply(a: int, b: int) -> int:
                return a * b

            res = multiply(6, 7)
            assert res == 42

            traj = tracer.to_trajectory()
            assert len(traj.nodes) == 1
            node = traj.nodes[0]
            assert node.event_type == EventType.TOOL_CALL
            assert node.label == "Tool: calculator_tool"
            assert node.payload["tool_call"]["input_args"]["a"] == 6
            assert node.payload["tool_call"]["output_result"] == 42

    @pytest.mark.asyncio
    async def test_universal_observe_decorator_async(self):
        """Verifies @observe wraps asynchronous functions and captures errors."""
        tracer = AgentTracer(agent_id="async_worker")
        token = evalora.trace("async_worker")

        with trace_agent_execution(agent_id="async_worker") as active_tracer:
            @observe(name="async_fetcher", span_type="tool")
            async def mock_fetch(url: str):
                await asyncio.sleep(0.01)
                if "fail" in url:
                    raise ConnectionResetError("Connection dropped by peer")
                return {"status": 200, "url": url}

            success = await mock_fetch("https://api.example.com/data")
            assert success["status"] == 200

            with pytest.raises(ConnectionResetError):
                await mock_fetch("https://api.example.com/fail")

            traj = active_tracer.to_trajectory()
            assert len(traj.nodes) == 2
            err_node = traj.nodes[1]
            assert err_node.payload["tool_call"]["is_error"] is True
            assert "Connection dropped" in err_node.payload["tool_call"]["error_message"]

    def test_evalora_client_safe_flush_offline(self):
        """Verifies client gracefully handles offline/unreachable servers without throwing."""
        client = EvaloraClient()
        client.init(endpoint="http://127.0.0.1:59999/unreachable_traces", auto_flush=False)

        tracer = AgentTracer(agent_id="offline_agent")
        tracer.record_plan("Offline plan", ["step1"])

        # Direct flush to unreachable port should return False without crashing
        success = tracer.flush(endpoint="http://127.0.0.1:59999/unreachable_traces")
        assert success is False

        # Client enqueue and flush
        client.enqueue_trace(tracer)
        client.flush(timeout=0.5)

    def test_execute_multi_agent_workflow_live(self):
        """Verifies real multi-agent workflow executes and generates full DAG with delegation and chat."""
        from core.agent.runtime import execute_multi_agent_workflow
        tracer = execute_multi_agent_workflow("Verify balance for acct_982 and notify billing")
        traj = tracer.to_trajectory()
        assert len(traj.nodes) >= 6
        assert "orchestrator_agent" in traj.agent_id
        event_types = [n.event_type for n in traj.nodes]
        assert EventType.AGENT_DELEGATE in event_types
        assert EventType.AGENT_MESSAGE in event_types
        assert EventType.TOOL_CALL in event_types
        assert traj.is_success is True

