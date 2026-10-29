"""tests/test_circuit_breaker.py: Verification of active agent loop kill-switch."""

import pytest
from core.sdk.tracer import (
    AgentLoopException,
    AgentTracer,
    CircuitBreaker,
    observe,
    trace_agent_execution,
)


class TestCircuitBreaker:
    """Verifies active sliding-window loop detection and execution kill-switch."""

    def test_circuit_breaker_trips_on_repeated_identical_calls(self):
        cb = CircuitBreaker(max_repeated_calls=3)
        cb.check_call("sql_query", {"query": "SELECT * FROM users"})
        cb.check_call("sql_query", {"query": "SELECT * FROM users"})

        # 3rd identical call must trip the breaker
        with pytest.raises(AgentLoopException) as exc:
            cb.check_call("sql_query", {"query": "SELECT * FROM users"})
        assert "invoked 3 times with identical arguments" in str(exc.value)

    def test_circuit_breaker_allows_varying_calls(self):
        cb = CircuitBreaker(max_repeated_calls=3)
        cb.check_call("search", {"q": "cats"})
        cb.check_call("search", {"q": "dogs"})
        cb.check_call("search", {"q": "birds"})
        cb.check_call("search", {"q": "cats"})
        # Varying parameters should not trip breaker

    def test_circuit_breaker_trips_on_consecutive_failures(self):
        cb = CircuitBreaker(max_consecutive_failures=3)
        cb.record_outcome(is_error=True)
        cb.record_outcome(is_error=True)

        with pytest.raises(AgentLoopException) as exc:
            cb.record_outcome(is_error=True)
        assert "encountered 3 consecutive tool failures" in str(exc.value)

    def test_circuit_breaker_trips_on_max_total_steps(self):
        cb = CircuitBreaker(max_total_steps=5)
        for i in range(5):
            cb.check_call(f"tool_{i}", {"step": i})

        with pytest.raises(AgentLoopException) as exc:
            cb.check_call("final_tool", {"step": 6})
        assert "exceeded maximum allowed execution steps" in str(exc.value)

    def test_tracer_execute_tool_trips_circuit_breaker_and_records_span(self):
        tracer = AgentTracer(agent_id="looping_bot", circuit_breaker=CircuitBreaker(max_repeated_calls=2))

        def dummy_tool(x: int):
            return x * 2

        # 1st call succeeds
        assert tracer.execute_tool("dummy_tool", dummy_tool, x=10) == 20

        # 2nd identical call must trip circuit breaker
        with pytest.raises(AgentLoopException):
            tracer.execute_tool("dummy_tool", dummy_tool, x=10)

        # Verify error span was captured
        traj = tracer.to_trajectory()
        assert len(traj.nodes) == 2
        err_node = traj.nodes[1]
        assert err_node.payload["tool_call"]["is_error"] is True
        assert "Circuit breaker tripped" in err_node.payload["tool_call"]["error_message"]

    def test_observe_decorator_with_circuit_breaker(self):
        cb = CircuitBreaker(max_repeated_calls=2)
        tracer = AgentTracer(agent_id="observed_looper", circuit_breaker=cb)

        with trace_agent_execution(agent_id="observed_looper", auto_flush=False) as active_tracer:
            active_tracer.circuit_breaker = cb

            @observe(name="loop_check_tool", span_type="tool")
            def failing_loop(query: str):
                return f"Result for {query}"

            # Call 1
            failing_loop("repeat_me")

            # Call 2 with identical arg trips breaker
            with pytest.raises(AgentLoopException):
                failing_loop("repeat_me")

    def test_circuit_breaker_increased_default_thresholds(self):
        """Verifies default thresholds are higher to support legitimate agent polling/retries."""
        cb = CircuitBreaker()
        assert cb.max_repeated_calls >= 10
        assert cb.max_consecutive_failures >= 8
        assert cb.max_total_steps >= 300

    def test_circuit_breaker_env_var_override(self, monkeypatch):
        """Verifies thresholds can be customized via environment variables."""
        monkeypatch.setenv("EVALORA_MAX_REPEATED_CALLS", "15")
        monkeypatch.setenv("EVALORA_MAX_CONSECUTIVE_FAILURES", "12")
        monkeypatch.setenv("EVALORA_MAX_TOTAL_STEPS", "500")

        cb = CircuitBreaker()
        assert cb.max_repeated_calls == 15
        assert cb.max_consecutive_failures == 12
        assert cb.max_total_steps == 500

    @pytest.mark.asyncio
    async def test_async_flush_non_blocking(self):
        """Verifies aflush method flushes asynchronously without blocking event loop."""
        tracer = AgentTracer(agent_id="async_flusher_agent")
        tracer.record_plan("Async plan", ["step1"])

        # aflush returns boolean without blocking
        success = await tracer.aflush(endpoint="http://127.0.0.1:59999/unreachable_traces")
        assert success is False

