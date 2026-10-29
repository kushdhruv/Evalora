"""evalora: Universal AI Agent Observability & Evaluation Platform Plugin.

A drop-in observability SDK for AI agents (LangGraph, CrewAI, AutoGen, OpenAI Swarm, LlamaIndex, or custom runtimes).
Converts non-deterministic agent executions into canonical Trajectory DAGs, detects causal faults, and masks sensitive PII.
"""

from core.models.schema import EventType, FailureCategory, GateDecision, Trajectory
from core.sdk.tracer import (
    AgentLoopException,
    AgentTracer,
    CircuitBreaker,
    EvaloraClient,
    evalora,
    get_current_tracer,
    observe,
    sanitize_pii,
    set_current_tracer,
    trace_agent_execution,
)

__version__ = "1.0.0"

__all__ = [
    "evalora",
    "observe",
    "AgentTracer",
    "CircuitBreaker",
    "AgentLoopException",
    "trace_agent_execution",
    "sanitize_pii",
    "get_current_tracer",
    "set_current_tracer",
    "EvaloraClient",
    "Trajectory",
    "EventType",
    "FailureCategory",
    "GateDecision",
]

