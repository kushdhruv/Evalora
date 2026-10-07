"""core/db/models.py: SQLAlchemy ORM models for persistent storage."""

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now():
    return datetime.now(timezone.utc)


class DBTrace(Base):
    __tablename__ = "traces"

    trace_id = Column(String(64), primary_key=True, index=True)
    agent_id = Column(String(128), default="agent_under_test", index=True)
    agent_version = Column(String(32), default="1.0.0")
    created_at = Column(DateTime, default=utc_now)
    total_latency_ms = Column(Float, default=0.0)
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    is_success = Column(Boolean, default=True)

    spans = relationship("DBSpan", back_populates="trace", cascade="all, delete-orphan")
    trajectory = relationship("DBTrajectory", back_populates="trace", uselist=False, cascade="all, delete-orphan")
    evaluations = relationship("DBEvaluation", back_populates="trace", cascade="all, delete-orphan")
    failures = relationship("DBFailure", back_populates="trace", cascade="all, delete-orphan")
    root_cause = relationship("DBRootCause", back_populates="trace", uselist=False, cascade="all, delete-orphan")


class DBSpan(Base):
    __tablename__ = "spans"

    span_id = Column(String(64), primary_key=True, index=True)
    trace_id = Column(String(64), ForeignKey("traces.trace_id"), index=True)
    parent_span_id = Column(String(64), nullable=True)
    name = Column(String(255), nullable=False)
    start_time = Column(DateTime, default=utc_now)
    end_time = Column(DateTime, default=utc_now)
    status_code = Column(String(32), default="OK")
    attributes = Column(JSON, default=dict)
    events = Column(JSON, default=list)

    trace = relationship("DBTrace", back_populates="spans")


class DBTrajectory(Base):
    __tablename__ = "trajectories"

    trajectory_id = Column(String(64), primary_key=True, index=True)
    trace_id = Column(String(64), ForeignKey("traces.trace_id"), unique=True, index=True)
    agent_id = Column(String(128), default="agent_under_test")
    agent_version = Column(String(32), default="1.0.0")
    nodes = Column(JSON, default=list)
    edges = Column(JSON, default=list)
    total_latency_ms = Column(Float, default=0.0)
    total_tokens = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    is_success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    trace = relationship("DBTrace", back_populates="trajectory")


class DBEvaluation(Base):
    __tablename__ = "evaluations"

    eval_id = Column(String(64), primary_key=True, index=True)
    trace_id = Column(String(64), ForeignKey("traces.trace_id"), index=True)
    target_node_id = Column(String(64), nullable=True)
    evaluator_name = Column(String(128), nullable=False)
    evaluator_layer = Column(String(32), nullable=False)
    evaluator_version = Column(String(32), default="1.0.0")
    score = Column(Float, nullable=False)
    confidence = Column(Float, default=1.0)
    passed = Column(Boolean, default=True)
    rationale = Column(Text, nullable=True)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    trace = relationship("DBTrace", back_populates="evaluations")


class DBFailure(Base):
    __tablename__ = "failures"

    failure_id = Column(String(64), primary_key=True, index=True)
    trace_id = Column(String(64), ForeignKey("traces.trace_id"), index=True)
    node_id = Column(String(64), nullable=False)
    category = Column(String(64), nullable=False)
    subcategory = Column(String(64), nullable=False)
    severity = Column(String(32), default="FATAL")
    description = Column(Text, nullable=False)
    is_terminal = Column(Boolean, default=False)

    trace = relationship("DBTrace", back_populates="failures")


class DBRootCause(Base):
    __tablename__ = "root_causes"

    root_cause_id = Column(String(64), primary_key=True, index=True)
    trace_id = Column(String(64), ForeignKey("traces.trace_id"), unique=True, index=True)
    primary_failure_node_id = Column(String(64), nullable=False)
    primary_category = Column(String(64), nullable=False)
    confidence_score = Column(Float, default=1.0)
    propagation_chain = Column(JSON, default=list)
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    trace = relationship("DBTrace", back_populates="root_cause")


class DBDatasetItem(Base):
    __tablename__ = "dataset_items"

    item_id = Column(String(64), primary_key=True, index=True)
    dataset_id = Column(String(128), index=True)
    source_trace_id = Column(String(64), nullable=True)
    input_prompt = Column(Text, nullable=False)
    expected_outcome = Column(Text, nullable=True)
    expected_trajectory_schema = Column(JSON, default=dict)
    assertions = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=utc_now)


class DBExperiment(Base):
    __tablename__ = "experiments"

    experiment_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    dataset_id = Column(String(128), index=True)
    agent_id = Column(String(128), nullable=False)
    agent_version = Column(String(32), default="1.0.0")
    evaluator_config = Column(JSON, default=dict)
    total_samples = Column(Integer, default=0)
    passed_samples = Column(Integer, default=0)
    mean_score = Column(Float, default=0.0)
    mean_cost_usd = Column(Float, default=0.0)
    mean_latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)


class DBRegression(Base):
    __tablename__ = "regressions"

    regression_id = Column(String(64), primary_key=True, index=True)
    experiment_id = Column(String(64), index=True)
    baseline_experiment_id = Column(String(64), index=True)
    score_delta = Column(Float, default=0.0)
    cost_delta_usd = Column(Float, default=0.0)
    latency_delta_ms = Column(Float, default=0.0)
    new_failures_count = Column(Integer, default=0)
    resolved_failures_count = Column(Integer, default=0)
    gate_decision = Column(String(32), default="PASS")
    breakdown_by_category = Column(JSON, default=dict)
    summary_markdown = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)
