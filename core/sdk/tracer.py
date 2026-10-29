"""core/sdk/tracer.py: Universal Agent Instrumentation SDK & Plugin for Evalora."""

import asyncio
import functools
import inspect
import json
import logging
import queue
import re
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

from core.models.schema import (
    AgentEvent,
    EventType,
    MemoryEvent,
    Span,
    ToolCall,
    Trajectory,
)
from core.trajectory.builder import TrajectoryBuilder

logger = logging.getLogger("evalora.sdk")

# Context variable for thread/task-local active tracer
_current_tracer: ContextVar[Optional["AgentTracer"]] = ContextVar("evalora_current_tracer", default=None)


def get_current_tracer() -> Optional["AgentTracer"]:
    """Returns the currently active AgentTracer in this execution context."""
    return _current_tracer.get()


def set_current_tracer(tracer: Optional["AgentTracer"]):
    """Sets the active AgentTracer in this execution context."""
    _current_tracer.set(tracer)


# ---------------------------------------------------------------------------
# PII & Sensitive Credential Masking
# ---------------------------------------------------------------------------

_PII_PATTERNS = [
    # API Keys & Tokens
    (re.compile(r"(?:sk-[a-zA-Z0-9_\-]{20,}|AIza[a-zA-Z0-9_\-]{35,}|ghp_[a-zA-Z0-9]{36,}|gsk_[a-zA-Z0-9]{30,})"), "[REDACTED_API_KEY]"),
    # Bearer tokens
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{20,}", re.IGNORECASE), r"\1[REDACTED_BEARER_TOKEN]"),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"), "[REDACTED_EMAIL]"),
    # Credit Card numbers (13-16 digits with dashes or spaces)
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[REDACTED_CREDIT_CARD]"),
    # Passwords or Secrets in key-value formats
    (re.compile(r'(?i)(password|passwd|secret|api_key|access_token|private_key)["\']?\s*[:=]\s*["\']?([^"\'\s,]+)'), r'\1="[REDACTED]"'),
]

_SENSITIVE_KEY_SUBSTRINGS = {"password", "secret", "api_key", "token", "credential", "auth", "private_key"}


def sanitize_pii(data: Any) -> Any:
    """Recursively redacts API keys, credentials, tokens, emails, and sensitive keys."""
    if isinstance(data, str):
        sanitized = data
        for pattern, repl in _PII_PATTERNS:
            sanitized = pattern.sub(repl, sanitized)
        return sanitized
    elif isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if any(s in str(k).lower() for s in _SENSITIVE_KEY_SUBSTRINGS):
                cleaned[k] = "[REDACTED_CREDENTIAL]"
            else:
                cleaned[k] = sanitize_pii(v)
        return cleaned
    elif isinstance(data, (list, tuple)):
        return [sanitize_pii(item) for item in data]
    return data


# ---------------------------------------------------------------------------
# Active Runtime Circuit Breaker & Infinite Loop Guard
# ---------------------------------------------------------------------------

class AgentLoopException(RuntimeError):
    """Raised when an agent enters an infinite repetitive tool or execution loop."""

    def __init__(self, message: str, tool_name: Optional[str] = None, repetitions: int = 0):
        super().__init__(message)
        self.tool_name = tool_name
        self.repetitions = repetitions


class CircuitBreaker:
    """Sliding-window active circuit breaker protecting agents from runaway execution loops."""

    def __init__(
        self,
        max_repeated_calls: Optional[int] = None,
        max_consecutive_failures: Optional[int] = None,
        max_total_steps: Optional[int] = None,
        enabled: bool = True,
    ):
        import os
        self.max_repeated_calls = (
            max_repeated_calls
            if max_repeated_calls is not None
            else int(os.getenv("EVALORA_MAX_REPEATED_CALLS", "10"))
        )
        self.max_consecutive_failures = (
            max_consecutive_failures
            if max_consecutive_failures is not None
            else int(os.getenv("EVALORA_MAX_CONSECUTIVE_FAILURES", "8"))
        )
        self.max_total_steps = (
            max_total_steps
            if max_total_steps is not None
            else int(os.getenv("EVALORA_MAX_TOTAL_STEPS", "300"))
        )
        self.enabled = enabled
        self._history: List[Dict[str, Any]] = []
        self._consecutive_failures = 0
        self._total_steps = 0

    def check_call(self, tool_name: str, kwargs: Dict[str, Any]):
        if not self.enabled:
            return

        self._total_steps += 1
        if self._total_steps > self.max_total_steps:
            raise AgentLoopException(
                f"Circuit breaker tripped: exceeded maximum allowed execution steps ({self.max_total_steps})",
                tool_name=tool_name,
                repetitions=self._total_steps,
            )

        call_sig = {"tool": tool_name, "args": json.dumps(kwargs, sort_keys=True, default=str)}

        consecutive_repeats = 0
        for prev in reversed(self._history):
            if prev == call_sig:
                consecutive_repeats += 1
            else:
                break

        if consecutive_repeats >= (self.max_repeated_calls - 1):
            raise AgentLoopException(
                f"Circuit breaker tripped: tool '{tool_name}' invoked {consecutive_repeats + 1} times with identical arguments",
                tool_name=tool_name,
                repetitions=consecutive_repeats + 1,
            )

        self._history.append(call_sig)
        if len(self._history) > 50:
            self._history.pop(0)

    def record_outcome(self, is_error: bool):
        if not self.enabled:
            return

        if is_error:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.max_consecutive_failures:
                raise AgentLoopException(
                    f"Circuit breaker tripped: encountered {self._consecutive_failures} consecutive tool failures without recovery",
                    repetitions=self._consecutive_failures,
                )
        else:
            self._consecutive_failures = 0


# ---------------------------------------------------------------------------
# Core AgentTracer
# ---------------------------------------------------------------------------

class AgentTracer:
    """Real-time tracer capturing execution duration, tool I/O, multi-agent chat, and exceptions."""

    def __init__(
        self,
        agent_id: str = "production_agent",
        agent_version: str = "1.0.0",
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        mask_pii: bool = True,
        circuit_breaker: Optional[Union[CircuitBreaker, bool]] = None,
    ):
        self.agent_id = agent_id
        self.agent_version = agent_version
        self.session_id = session_id or f"sess_{uuid4().hex[:10]}"
        self.trace_id = trace_id or f"trace_{uuid4().hex[:12]}"
        self.mask_pii = mask_pii
        if circuit_breaker is True:
            self.circuit_breaker: Optional[CircuitBreaker] = CircuitBreaker()
        elif isinstance(circuit_breaker, CircuitBreaker):
            self.circuit_breaker = circuit_breaker
        elif circuit_breaker is False:
            self.circuit_breaker = None
        else:
            self.circuit_breaker = CircuitBreaker() if evalora.is_circuit_breaker_enabled() else None
        self.spans: List[Span] = []
        self.events: List[AgentEvent] = []
        self.start_wall_time = time.perf_counter()

    def record_plan(self, plan_content: str, steps: List[str], agent_id: Optional[str] = None):
        """Records an agent planning action."""
        now = datetime.now(timezone.utc)
        span_id = f"span_plan_{uuid4().hex[:8]}"
        clean_content = sanitize_pii(plan_content) if self.mask_pii else plan_content
        clean_steps = sanitize_pii(steps) if self.mask_pii else steps
        target_agent = agent_id or self.agent_id

        self.spans.append(
            Span(
                span_id=span_id,
                trace_id=self.trace_id,
                name="agent_planning",
                start_time=now,
                end_time=now,
                status_code="OK",
                attributes={
                    "agent.id": target_agent,
                    "agent.step_type": "plan",
                    "output.value": clean_content,
                    "session.id": self.session_id,
                },
            )
        )
        self.events.append(
            AgentEvent(
                trace_id=self.trace_id,
                span_id=span_id,
                event_type=EventType.PLAN,
                timestamp=now,
                content=clean_content,
                sender_agent=target_agent,
                session_id=self.session_id,
                metadata={"planned_steps": clean_steps},
            )
        )

    def record_reasoning(
        self,
        thought: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Records an internal reasoning or CoT (Chain of Thought) step."""
        now = datetime.now(timezone.utc)
        span_id = f"span_reason_{uuid4().hex[:8]}"
        clean_thought = sanitize_pii(thought) if self.mask_pii else thought
        target_agent = agent_id or self.agent_id
        sess = session_id or self.session_id

        meta = metadata or {}
        if self.mask_pii:
            meta = sanitize_pii(meta)

        self.spans.append(
            Span(
                span_id=span_id,
                trace_id=self.trace_id,
                name="agent_reasoning",
                start_time=now,
                end_time=now,
                status_code="OK",
                attributes={
                    "agent.id": target_agent,
                    "agent.step_type": "reasoning",
                    "output.value": clean_thought,
                    "session.id": sess,
                    **meta,
                },
            )
        )
        self.events.append(
            AgentEvent(
                trace_id=self.trace_id,
                span_id=span_id,
                event_type=EventType.REASONING,
                timestamp=now,
                content=clean_thought,
                sender_agent=target_agent,
                session_id=sess,
                metadata=meta,
            )
        )

    def record_agent_message(
        self,
        sender: str,
        recipient: str,
        content: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Records an explicit inter-agent communication message in a multi-agent chat."""
        now = datetime.now(timezone.utc)
        span_id = f"span_msg_{uuid4().hex[:8]}"
        clean_content = sanitize_pii(content) if self.mask_pii else content
        sess = session_id or self.session_id

        attrs: Dict[str, Any] = {
            "openinference.span.kind": "AGENT_MESSAGE",
            "agent.sender": sender,
            "agent.recipient": recipient,
            "agent.action": "message",
            "session.id": sess,
            "output.value": clean_content,
        }
        if metadata:
            attrs.update(sanitize_pii(metadata) if self.mask_pii else metadata)

        self.spans.append(
            Span(
                span_id=span_id,
                trace_id=self.trace_id,
                name=f"chat_{sender}_to_{recipient}",
                start_time=now,
                end_time=now,
                status_code="OK",
                attributes=attrs,
            )
        )
        self.events.append(
            AgentEvent(
                trace_id=self.trace_id,
                span_id=span_id,
                event_type=EventType.AGENT_MESSAGE,
                timestamp=now,
                content=clean_content,
                sender_agent=sender,
                recipient_agent=recipient,
                session_id=sess,
                metadata=attrs,
            )
        )

    def record_agent_delegation(
        self,
        delegator: str,
        delegatee: str,
        task: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Records a supervisor-to-subagent task delegation or swarm handoff."""
        now = datetime.now(timezone.utc)
        span_id = f"span_deleg_{uuid4().hex[:8]}"
        clean_task = sanitize_pii(task) if self.mask_pii else task
        sess = session_id or self.session_id

        attrs: Dict[str, Any] = {
            "openinference.span.kind": "AGENT_DELEGATE",
            "agent.sender": delegator,
            "agent.recipient": delegatee,
            "agent.action": "delegate",
            "session.id": sess,
            "output.value": clean_task,
        }
        if metadata:
            attrs.update(sanitize_pii(metadata) if self.mask_pii else metadata)

        self.spans.append(
            Span(
                span_id=span_id,
                trace_id=self.trace_id,
                name=f"delegate_{delegator}_to_{delegatee}",
                start_time=now,
                end_time=now,
                status_code="OK",
                attributes=attrs,
            )
        )
        self.events.append(
            AgentEvent(
                trace_id=self.trace_id,
                span_id=span_id,
                event_type=EventType.AGENT_DELEGATE,
                timestamp=now,
                content=clean_task,
                sender_agent=delegator,
                recipient_agent=delegatee,
                session_id=sess,
                metadata=attrs,
            )
        )

    def record_tool_call(
        self,
        tool_name: str,
        input_args: Dict[str, Any],
        output_result: Any,
        execution_time_ms: float = 0.0,
        is_error: bool = False,
        error_message: Optional[str] = None,
        agent_id: Optional[str] = None,
    ):
        """Directly records a tool call event and span."""
        span_id = f"span_tool_{uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        target_agent = agent_id or self.agent_id

        clean_args = sanitize_pii(input_args) if self.mask_pii else input_args
        clean_out = sanitize_pii(output_result) if self.mask_pii else output_result
        clean_err = sanitize_pii(error_message) if (self.mask_pii and error_message) else error_message

        attrs = {
            "openinference.span.kind": "TOOL",
            "tool.name": tool_name,
            "tool.parameters": json.dumps(clean_args) if isinstance(clean_args, dict) else str(clean_args),
            "agent.id": target_agent,
            "session.id": self.session_id,
        }
        if is_error:
            # pyrefly: ignore[bad-assignment]
            attrs["error"] = True
            attrs["error.message"] = clean_err or "Tool execution failed"
        else:
            attrs["tool.output"] = str(clean_out)

        self.spans.append(
            Span(
                span_id=span_id,
                trace_id=self.trace_id,
                name=f"tool_{tool_name}",
                start_time=now,
                end_time=now,
                status_code="ERROR" if is_error else "OK",
                attributes=attrs,
            )
        )
        self.events.append(
            AgentEvent(
                trace_id=self.trace_id,
                span_id=span_id,
                event_type=EventType.TOOL_CALL,
                timestamp=now,
                sender_agent=target_agent,
                session_id=self.session_id,
                tool_call=ToolCall(
                    tool_name=tool_name,
                    input_args=clean_args if isinstance(clean_args, dict) else {"raw": clean_args},
                    output_result=clean_out if not is_error else None,
                    execution_time_ms=execution_time_ms,
                    is_error=is_error,
                    error_message=clean_err,
                ),
            )
        )

    def execute_tool(self, tool_name: str, tool_fn: Callable, agent_id: Optional[str] = None, **kwargs) -> Any:
        """Executes a real tool function, measuring real latency, checking circuit breaker, and capturing exceptions."""
        target_agent = agent_id or self.agent_id
        if self.circuit_breaker:
            try:
                self.circuit_breaker.check_call(tool_name, kwargs)
            except AgentLoopException as loop_err:
                self.record_tool_call(
                    tool_name=tool_name,
                    input_args=kwargs,
                    output_result=None,
                    execution_time_ms=0.0,
                    is_error=True,
                    error_message=str(loop_err),
                    agent_id=target_agent,
                )
                raise

        start_t = time.perf_counter()
        result = None
        is_error = False
        error_msg = None

        try:
            result = tool_fn(**kwargs)
        except Exception as e:
            is_error = True
            error_msg = f"{type(e).__name__}: {str(e)}"

        elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
        self.record_tool_call(
            tool_name=tool_name,
            input_args=kwargs,
            output_result=result,
            execution_time_ms=elapsed_ms,
            is_error=is_error,
            error_message=error_msg,
            agent_id=target_agent,
        )

        if self.circuit_breaker:
            self.circuit_breaker.record_outcome(is_error=is_error)

        if is_error:
            raise RuntimeError(error_msg)

        return result

    def record_memory(
        self,
        operation: str,
        query: Optional[str] = None,
        keys: Optional[List[str]] = None,
        content: Optional[List[Dict[str, Any]]] = None,
        scores: Optional[List[float]] = None,
        latency_ms: float = 0.0,
        agent_id: Optional[str] = None,
    ):
        """Records a vector search, working memory query, or knowledge retrieval."""
        now = datetime.now(timezone.utc)
        span_id = f"span_mem_{uuid4().hex[:8]}"
        target_agent = agent_id or self.agent_id

        clean_query = sanitize_pii(query) if (self.mask_pii and query) else query
        clean_content = sanitize_pii(content) if (self.mask_pii and content) else (content or [])

        event_type = EventType.MEMORY_WRITE if operation.lower() in ("store", "write") else EventType.MEMORY_READ

        self.spans.append(
            Span(
                span_id=span_id,
                trace_id=self.trace_id,
                name=f"memory_{operation}",
                start_time=now,
                end_time=now,
                status_code="OK",
                attributes={
                    "openinference.span.kind": "RETRIEVER",
                    "memory.operation": operation,
                    "input.value": clean_query or "",
                    "agent.id": target_agent,
                    "session.id": self.session_id,
                },
            )
        )
        self.events.append(
            AgentEvent(
                trace_id=self.trace_id,
                span_id=span_id,
                event_type=event_type,
                timestamp=now,
                sender_agent=target_agent,
                session_id=self.session_id,
                memory_event=MemoryEvent(
                    operation=operation,
                    query_text=clean_query,
                    retrieved_keys=keys or [],
                    retrieved_content=clean_content,
                    similarity_scores=scores or [],
                    latency_ms=latency_ms,
                ),
            )
        )

    def record_outcome(self, outcome_text: str, is_success: Optional[bool] = None, agent_id: Optional[str] = None):
        """Records the final response or mission outcome."""
        now = datetime.now(timezone.utc)
        span_id = f"span_outcome_{uuid4().hex[:8]}"
        clean_outcome = sanitize_pii(outcome_text) if self.mask_pii else outcome_text
        target_agent = agent_id or self.agent_id

        self.spans.append(
            Span(
                span_id=span_id,
                trace_id=self.trace_id,
                name="agent_final_outcome",
                start_time=now,
                end_time=now,
                status_code="OK",
                attributes={
                    "agent.id": target_agent,
                    "agent.step_type": "outcome",
                    "output.value": clean_outcome,
                    "session.id": self.session_id,
                },
            )
        )
        self.events.append(
            AgentEvent(
                trace_id=self.trace_id,
                span_id=span_id,
                event_type=EventType.FINAL_OUTCOME,
                timestamp=now,
                content=clean_outcome,
                sender_agent=target_agent,
                session_id=self.session_id,
            )
        )

    def to_trajectory(self) -> Trajectory:
        """Compiles recorded events into a complete Trajectory DAG."""
        return TrajectoryBuilder.build_trajectory(
            events=self.events,
            raw_spans=self.spans,
            agent_id=self.agent_id,
            agent_version=self.agent_version,
        )

    def to_otlp_payload(self) -> Dict[str, Any]:
        """Exports standard OTLP JSON payload for HTTP ingestion."""
        raw_spans = []
        for s in self.spans:
            raw_spans.append(
                {
                    "traceId": s.trace_id,
                    "spanId": s.span_id,
                    "parentSpanId": s.parent_span_id,
                    "name": s.name,
                    "startTimeUnixNano": int(s.start_time.timestamp() * 1e9),
                    "endTimeUnixNano": int(s.end_time.timestamp() * 1e9),
                    "status": {"code": "ERROR" if s.status_code == "ERROR" else "OK"},
                    "attributes": [
                        {"key": k, "value": {"stringValue": str(v)}} for k, v in s.attributes.items()
                    ],
                }
            )
        return {"resourceSpans": [{"scopeSpans": [{"spans": raw_spans}]}]}

    def flush(self, endpoint: Optional[str] = None) -> bool:
        """Flushes the current trace payload to the Evalora server."""
        ep = endpoint or evalora.endpoint
        payload = self.to_otlp_payload()
        try:
            headers = {"Content-Type": "application/json", "User-Agent": "evalora-sdk/1.0"}
            if evalora.api_key:
                headers["Authorization"] = f"Bearer {evalora.api_key}"
            req = urllib.request.Request(
                ep,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as response:
                return response.status in (200, 201)
        except Exception as e:
            logger.debug("Evalora trace flush non-fatal error: %s", e)
            return False

    async def aflush(self, endpoint: Optional[str] = None) -> bool:
        """Asynchronously flushes the current trace payload without blocking the event loop."""
        return await asyncio.to_thread(self.flush, endpoint)


# ---------------------------------------------------------------------------
# Context Manager for Scoped Tracing
# ---------------------------------------------------------------------------

@contextmanager
def trace_agent_execution(
    agent_id: str = "agent",
    agent_version: str = "1.0.0",
    session_id: Optional[str] = None,
    auto_flush: bool = True,
):
    """Context manager setting active tracer and optionally auto-flushing on exit."""
    tracer = AgentTracer(agent_id=agent_id, agent_version=agent_version, session_id=session_id)
    token = _current_tracer.set(tracer)
    try:
        yield tracer
    finally:
        _current_tracer.reset(token)
        if auto_flush and evalora.is_auto_flush_enabled():
            evalora.enqueue_trace(tracer)


# ---------------------------------------------------------------------------
# Universal @observe Decorator
# ---------------------------------------------------------------------------

def observe(
    name_or_fn: Union[str, Callable, None] = None,
    *,
    name: Optional[str] = None,
    span_type: str = "tool",  # "tool", "agent", "reasoning", "message", "delegate"
    agent_id: Optional[str] = None,
    recipient_agent: Optional[str] = None,
    mask_pii: bool = True,
):
    """Universal decorator for functions, tools, or agents.
    
    Can be used bare:
        @observe
        def search(query: str): ...
        
    Or with options:
        @observe(name="web_search", span_type="tool")
        @observe(span_type="agent", agent_id="researcher")
        @observe(span_type="delegate", agent_id="supervisor", recipient_agent="coder")
    """
    effective_name = name or (name_or_fn if isinstance(name_or_fn, str) else None)

    def decorator(fn: Callable) -> Callable:
        fn_name = effective_name or getattr(fn, "__name__", "observed_function")

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                tracer = get_current_tracer()
                if not tracer:
                    # Ephemeral tracer if none active
                    tracer = AgentTracer(agent_id=agent_id or "observed_agent", mask_pii=mask_pii)

                try:
                    sig = inspect.signature(fn)
                    bound = sig.bind_partial(*args, **kwargs)
                    bound.apply_defaults()
                    call_args = dict(bound.arguments)
                except Exception:
                    call_args = kwargs.copy()
                    if args:
                        call_args["_args"] = [str(a) for a in args]

                if tracer.circuit_breaker and span_type == "tool":
                    tracer.circuit_breaker.check_call(fn_name, call_args)

                start_t = time.perf_counter()
                result = None
                is_error = False
                err_msg = None

                try:
                    result = await fn(*args, **kwargs)
                    return result
                except Exception as e:
                    is_error = True
                    err_msg = f"{type(e).__name__}: {str(e)}"
                    raise
                finally:
                    if tracer.circuit_breaker and span_type == "tool":
                        tracer.circuit_breaker.record_outcome(is_error=is_error)
                    elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
                    _record_observed(
                        tracer=tracer,
                        name=fn_name,
                        span_type=span_type,
                        args=call_args,
                        result=result,
                        elapsed_ms=elapsed_ms,
                        is_error=is_error,
                        err_msg=err_msg,
                        agent_id=agent_id,
                        recipient_agent=recipient_agent,
                    )
            return async_wrapper
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                tracer = get_current_tracer()
                if not tracer:
                    tracer = AgentTracer(agent_id=agent_id or "observed_agent", mask_pii=mask_pii)

                try:
                    sig = inspect.signature(fn)
                    bound = sig.bind_partial(*args, **kwargs)
                    bound.apply_defaults()
                    call_args = dict(bound.arguments)
                except Exception:
                    call_args = kwargs.copy()
                    if args:
                        call_args["_args"] = [str(a) for a in args]

                if tracer.circuit_breaker and span_type == "tool":
                    tracer.circuit_breaker.check_call(fn_name, call_args)

                start_t = time.perf_counter()
                result = None
                is_error = False
                err_msg = None

                try:
                    result = fn(*args, **kwargs)
                    return result
                except Exception as e:
                    is_error = True
                    err_msg = f"{type(e).__name__}: {str(e)}"
                    raise
                finally:
                    if tracer.circuit_breaker and span_type == "tool":
                        tracer.circuit_breaker.record_outcome(is_error=is_error)
                    elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
                    _record_observed(
                        tracer=tracer,
                        name=fn_name,
                        span_type=span_type,
                        args=call_args,
                        result=result,
                        elapsed_ms=elapsed_ms,
                        is_error=is_error,
                        err_msg=err_msg,
                        agent_id=agent_id,
                        recipient_agent=recipient_agent,
                    )
            return sync_wrapper

    if callable(name_or_fn):
        fn = name_or_fn
        name_or_fn = None
        return decorator(fn)
    return decorator


def _record_observed(
    tracer: AgentTracer,
    name: str,
    span_type: str,
    args: Dict[str, Any],
    result: Any,
    elapsed_ms: float,
    is_error: bool,
    err_msg: Optional[str],
    agent_id: Optional[str],
    recipient_agent: Optional[str],
):
    tgt_agent = agent_id or tracer.agent_id
    if span_type == "tool":
        tracer.record_tool_call(
            tool_name=name,
            input_args=args,
            output_result=result,
            execution_time_ms=elapsed_ms,
            is_error=is_error,
            error_message=err_msg,
            agent_id=tgt_agent,
        )
    elif span_type == "delegate":
        tracer.record_agent_delegation(
            delegator=tgt_agent,
            delegatee=recipient_agent or "worker",
            task=str(args.get("task") or args.get("query") or args),
        )
    elif span_type == "message":
        tracer.record_agent_message(
            sender=tgt_agent,
            recipient=recipient_agent or "peer",
            content=str(result if result is not None else args),
        )
    elif span_type == "reasoning":
        tracer.record_reasoning(
            thought=str(result if result is not None else args),
            agent_id=tgt_agent,
        )
    else:  # "agent" or general step
        tracer.record_tool_call(
            tool_name=name,
            input_args=args,
            output_result=result,
            execution_time_ms=elapsed_ms,
            is_error=is_error,
            error_message=err_msg,
            agent_id=tgt_agent,
        )


# ---------------------------------------------------------------------------
# Evalora Singleton & Background Async Exporter
# ---------------------------------------------------------------------------

class EvaloraClient:
    """Production drop-in client managing configuration, background flushing, and trace buffers."""

    _instance: Optional["EvaloraClient"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(EvaloraClient, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.endpoint: str = "http://localhost:8000/v1/traces"
        self.api_key: Optional[str] = None
        self.default_agent_id: str = "production_agent"
        self.default_agent_version: str = "1.0.0"
        self.enabled: bool = True
        self.auto_flush: bool = True
        self.circuit_breaker_enabled: bool = False
        self.circuit_breaker_max_repeats: int = 3
        self.circuit_breaker_max_failures: int = 4
        self._queue: queue.Queue = queue.Queue(maxsize=5000)
        self._worker_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._initialized = True
        self._start_worker()

    def init(
        self,
        endpoint: str = "http://localhost:8000/v1/traces",
        api_key: Optional[str] = None,
        agent_id: str = "production_agent",
        agent_version: str = "1.0.0",
        auto_flush: bool = True,
        enabled: bool = True,
        circuit_breaker: bool = False,
        max_repeated_calls: int = 3,
        max_consecutive_failures: int = 4,
    ):
        """Initializes Evalora client settings for the host application."""
        self.endpoint = endpoint
        self.api_key = api_key
        self.default_agent_id = agent_id
        self.default_agent_version = agent_version
        self.auto_flush = auto_flush
        self.enabled = enabled
        self.circuit_breaker_enabled = circuit_breaker
        self.circuit_breaker_max_repeats = max_repeated_calls
        self.circuit_breaker_max_failures = max_consecutive_failures
        if self.enabled and (not self._worker_thread or not self._worker_thread.is_alive()):
            self._start_worker()

    def is_auto_flush_enabled(self) -> bool:
        return self.enabled and self.auto_flush

    def is_circuit_breaker_enabled(self) -> bool:
        return self.enabled and self.circuit_breaker_enabled

    def _start_worker(self):
        self._shutdown_event.clear()
        self._worker_thread = threading.Thread(target=self._flusher_loop, daemon=True, name="EvaloraFlusher")
        self._worker_thread.start()

    def enqueue_trace(self, tracer: AgentTracer):
        if not self.enabled:
            return
        try:
            self._queue.put_nowait(tracer.to_otlp_payload())
        except queue.Full:
            logger.warning("Evalora trace queue is full; dropping trace to prevent backpressure on agent.")

    def _flusher_loop(self):
        while not self._shutdown_event.is_set():
            batch = []
            try:
                # Grab first item with short timeout
                item = self._queue.get(timeout=1.0)
                batch.append(item)
                # Drain queue up to batch size 20
                while len(batch) < 20:
                    batch.append(self._queue.get_nowait())
            except (queue.Empty, Exception):
                pass

            if batch:
                for payload in batch:
                    try:
                        headers = {
                            "Content-Type": "application/json",
                            "User-Agent": "evalora-sdk/1.0",
                            "X-Evalora-Async": "true",
                        }
                        if self.api_key:
                            headers["Authorization"] = f"Bearer {self.api_key}"
                        req = urllib.request.Request(
                            self.endpoint,
                            data=json.dumps(payload).encode("utf-8"),
                            headers=headers,
                            method="POST",
                        )
                        with urllib.request.urlopen(req, timeout=4.0):
                            pass
                    except Exception as e:
                        logger.debug("Evalora async export non-fatal failure: %s", e)

    def trace(
        self,
        agent_id: Optional[str] = None,
        agent_version: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """Returns a scoped context manager for tracing an agent execution."""
        return trace_agent_execution(
            agent_id=agent_id or self.default_agent_id,
            agent_version=agent_version or self.default_agent_version,
            session_id=session_id,
            auto_flush=self.auto_flush,
        )

    def flush(self, timeout: float = 3.0):
        """Waits for all buffered traces to be sent."""
        start_t = time.time()
        while not self._queue.empty() and (time.time() - start_t) < timeout:
            time.sleep(0.05)

    async def aflush(self, timeout: float = 3.0):
        """Asynchronously waits for all buffered traces to be sent without blocking the event loop."""
        return await asyncio.to_thread(self.flush, timeout)

    def shutdown(self):
        """Flushes buffered traces and halts background worker."""
        self.flush()
        self._shutdown_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)


# Exported singleton instance
evalora = EvaloraClient()
