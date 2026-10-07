"""core/models/schema.py: Core Domain Schemas for the Agent Evaluation & Observability Platform."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict


class EventType(str, Enum):
    PLAN = "plan"
    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    REASONING = "reasoning"
    STATE_TRANSITION = "state_transition"
    FINAL_OUTCOME = "final_outcome"


class FailureCategory(str, Enum):
    PLANNING = "planning"
    TOOL = "tool"
    CONTEXT_MEMORY = "context_memory"
    REASONING_STATE = "reasoning_state"
    ENVIRONMENT = "environment"
    OUTCOME = "outcome"


class GateDecision(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# -----------------------------------------------------------------------------
# Telemetry & Normalized Events
# -----------------------------------------------------------------------------

class Span(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    span_id: str
    trace_id: str
    parent_span_id: Optional[str] = None
    name: str
    start_time: datetime
    end_time: datetime
    status_code: str = "OK"  # "OK", "ERROR", "UNSET"
    attributes: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)


class ToolCall(BaseModel):
    tool_name: str
    input_args: Dict[str, Any] = Field(default_factory=dict)
    output_result: Optional[Any] = None
    execution_time_ms: float = 0.0
    is_error: bool = False
    error_message: Optional[str] = None


class MemoryEvent(BaseModel):
    operation: str  # "query", "store", "evict", "update"
    query_text: Optional[str] = None
    retrieved_keys: List[str] = Field(default_factory=list)
    retrieved_content: List[Dict[str, Any]] = Field(default_factory=list)
    similarity_scores: List[float] = Field(default_factory=list)
    latency_ms: float = 0.0


class AgentEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    trace_id: str
    span_id: str
    parent_event_id: Optional[UUID] = None
    event_type: EventType
    timestamp: datetime = Field(default_factory=utc_now)
    content: Optional[str] = None
    state_snapshot: Dict[str, Any] = Field(default_factory=dict)
    tool_call: Optional[ToolCall] = None
    memory_event: Optional[MemoryEvent] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# Trajectory Graph
# -----------------------------------------------------------------------------

class TrajectoryNode(BaseModel):
    node_id: str
    event_id: UUID
    event_type: EventType
    label: str
    timestamp: datetime
    payload: Dict[str, Any] = Field(default_factory=dict)


class TrajectoryEdge(BaseModel):
    source_node_id: str
    target_node_id: str
    edge_type: str = "temporal_sequence"  # "call_parent", "data_dependency", "temporal_sequence"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Trajectory(BaseModel):
    trajectory_id: UUID = Field(default_factory=uuid4)
    trace_id: str
    agent_id: str
    agent_version: str = "1.0.0"
    nodes: List[TrajectoryNode] = Field(default_factory=list)
    edges: List[TrajectoryEdge] = Field(default_factory=list)
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    is_success: Optional[bool] = None
    created_at: datetime = Field(default_factory=utc_now)


# -----------------------------------------------------------------------------
# Evaluation & Causal Analysis
# -----------------------------------------------------------------------------

class Evaluation(BaseModel):
    eval_id: UUID = Field(default_factory=uuid4)
    trace_id: str
    trajectory_id: UUID
    target_node_id: Optional[str] = None  # None indicates trajectory-level eval
    evaluator_name: str
    evaluator_layer: str  # "deterministic", "semantic", "llm_judge", "trajectory"
    evaluator_version: str = "1.0.0"
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    passed: bool
    rationale: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class Failure(BaseModel):
    failure_id: UUID = Field(default_factory=uuid4)
    trajectory_id: UUID
    node_id: str
    category: FailureCategory
    subcategory: str
    severity: str = "FATAL"  # "FATAL", "DEGRADED", "RECOVERED"
    description: str
    is_terminal: bool = False


class RootCause(BaseModel):
    root_cause_id: UUID = Field(default_factory=uuid4)
    trajectory_id: UUID
    primary_failure_node_id: str
    primary_category: FailureCategory
    confidence_score: float = Field(ge=0.0, le=1.0)
    propagation_chain: List[str] = Field(default_factory=list)  # Ordered node IDs from root to final
    explanation: str


# -----------------------------------------------------------------------------
# Datasets, Experiments & Regressions
# -----------------------------------------------------------------------------

class DatasetItem(BaseModel):
    item_id: UUID = Field(default_factory=uuid4)
    dataset_id: str
    source_trace_id: Optional[str] = None
    input_prompt: str
    expected_outcome: Optional[str] = None
    expected_trajectory_schema: Optional[Dict[str, Any]] = None
    assertions: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class Experiment(BaseModel):
    experiment_id: UUID = Field(default_factory=uuid4)
    name: str
    dataset_id: str
    agent_id: str
    agent_version: str
    evaluator_config: Dict[str, Any] = Field(default_factory=dict)
    total_samples: int = 0
    passed_samples: int = 0
    mean_score: float = 0.0
    mean_cost_usd: float = 0.0
    mean_latency_ms: float = 0.0
    created_at: datetime = Field(default_factory=utc_now)


class RegressionResult(BaseModel):
    regression_id: UUID = Field(default_factory=uuid4)
    experiment_id: UUID
    baseline_experiment_id: UUID
    score_delta: float
    cost_delta_usd: float
    latency_delta_ms: float
    new_failures_count: int
    resolved_failures_count: int
    gate_decision: GateDecision
    breakdown_by_category: Dict[str, float] = Field(default_factory=dict)
    summary_markdown: str
    created_at: datetime = Field(default_factory=utc_now)
