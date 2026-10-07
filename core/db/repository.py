"""core/db/repository.py: Persistent Database Repository with SQLite/Postgres backing."""

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from core.db.models import (
    DBDatasetItem,
    DBEvaluation,
    DBExperiment,
    DBFailure,
    DBRegression,
    DBRootCause,
    DBSpan,
    DBTrace,
    DBTrajectory,
)
from core.db.session import SessionLocal, init_db
from core.models.schema import (
    DatasetItem,
    Evaluation,
    EventType,
    Experiment,
    Failure,
    FailureCategory,
    RegressionResult,
    RootCause,
    Span,
    Trajectory,
    TrajectoryEdge,
    TrajectoryNode,
)

# Ensure tables exist on load
init_db()


class PersistentRepository:
    """Thread-safe persistent repository storing traces, evaluations, and datasets to disk."""

    def __init__(self):
        self._session_factory = SessionLocal

    def _get_session(self) -> Session:
        return self._session_factory()

    def save_spans(self, spans: List[Span]):
        if not spans:
            return
        session = self._get_session()
        try:
            trace_id = spans[0].trace_id
            db_trace = session.query(DBTrace).filter_by(trace_id=trace_id).first()
            if not db_trace:
                db_trace = DBTrace(trace_id=trace_id)
                session.add(db_trace)

            for s in spans:
                existing = session.query(DBSpan).filter_by(span_id=s.span_id).first()
                if not existing:
                    db_span = DBSpan(
                        span_id=s.span_id,
                        trace_id=s.trace_id,
                        parent_span_id=s.parent_span_id,
                        name=s.name,
                        start_time=s.start_time,
                        end_time=s.end_time,
                        status_code=s.status_code,
                        attributes=s.attributes,
                        events=s.events,
                    )
                    session.add(db_span)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_trajectory(self, trajectory: Trajectory):
        session = self._get_session()
        try:
            db_trace = session.query(DBTrace).filter_by(trace_id=trajectory.trace_id).first()
            if not db_trace:
                db_trace = DBTrace(
                    trace_id=trajectory.trace_id,
                    agent_id=trajectory.agent_id,
                    agent_version=trajectory.agent_version,
                    total_latency_ms=trajectory.total_latency_ms,
                    total_tokens=trajectory.total_tokens,
                    total_cost_usd=trajectory.total_cost_usd,
                    is_success=trajectory.is_success,
                )
                session.add(db_trace)
            else:
                db_trace.agent_id = trajectory.agent_id
                db_trace.agent_version = trajectory.agent_version
                db_trace.total_latency_ms = trajectory.total_latency_ms
                db_trace.total_tokens = trajectory.total_tokens
                db_trace.total_cost_usd = trajectory.total_cost_usd
                db_trace.is_success = trajectory.is_success

            existing_traj = session.query(DBTrajectory).filter_by(trace_id=trajectory.trace_id).first()
            nodes_data = [n.model_dump(mode="json") for n in trajectory.nodes]
            edges_data = [e.model_dump(mode="json") for e in trajectory.edges]

            if existing_traj:
                existing_traj.nodes = nodes_data
                existing_traj.edges = edges_data
                existing_traj.total_latency_ms = trajectory.total_latency_ms
                existing_traj.total_tokens = trajectory.total_tokens
                existing_traj.total_cost_usd = trajectory.total_cost_usd
                existing_traj.is_success = trajectory.is_success
            else:
                db_traj = DBTrajectory(
                    trajectory_id=str(trajectory.trajectory_id),
                    trace_id=trajectory.trace_id,
                    agent_id=trajectory.agent_id,
                    agent_version=trajectory.agent_version,
                    nodes=nodes_data,
                    edges=edges_data,
                    total_latency_ms=trajectory.total_latency_ms,
                    total_tokens=trajectory.total_tokens,
                    total_cost_usd=trajectory.total_cost_usd,
                    is_success=trajectory.is_success,
                )
                session.add(db_traj)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_trajectory(self, trace_id: str) -> Optional[Trajectory]:
        session = self._get_session()
        try:
            db_traj = session.query(DBTrajectory).filter_by(trace_id=trace_id).first()
            if not db_traj:
                return None
            return Trajectory(
                trajectory_id=UUID(db_traj.trajectory_id),
                trace_id=db_traj.trace_id,
                agent_id=db_traj.agent_id,
                agent_version=db_traj.agent_version,
                nodes=[TrajectoryNode(**n) for n in db_traj.nodes],
                edges=[TrajectoryEdge(**e) for e in db_traj.edges],
                total_latency_ms=db_traj.total_latency_ms,
                total_tokens=db_traj.total_tokens,
                total_cost_usd=db_traj.total_cost_usd,
                is_success=db_traj.is_success,
                created_at=db_traj.created_at,
            )
        finally:
            session.close()

    def list_trajectories(self, limit: int = 50) -> List[Trajectory]:
        session = self._get_session()
        try:
            db_trajs = session.query(DBTrajectory).order_by(DBTrajectory.created_at.desc()).limit(limit).all()
            result = []
            for t in db_trajs:
                result.append(
                    Trajectory(
                        trajectory_id=UUID(t.trajectory_id),
                        trace_id=t.trace_id,
                        agent_id=t.agent_id,
                        agent_version=t.agent_version,
                        nodes=[TrajectoryNode(**n) for n in t.nodes],
                        edges=[TrajectoryEdge(**e) for e in t.edges],
                        total_latency_ms=t.total_latency_ms,
                        total_tokens=t.total_tokens,
                        total_cost_usd=t.total_cost_usd,
                        is_success=t.is_success,
                        created_at=t.created_at,
                    )
                )
            return list(reversed(result))
        finally:
            session.close()

    def save_evaluations(self, trace_id: str, evals: List[Evaluation]):
        if not evals:
            return
        session = self._get_session()
        try:
            for ev in evals:
                db_ev = DBEvaluation(
                    eval_id=str(ev.eval_id),
                    trace_id=trace_id,
                    target_node_id=ev.target_node_id,
                    evaluator_name=ev.evaluator_name,
                    evaluator_layer=ev.evaluator_layer,
                    evaluator_version=ev.evaluator_version,
                    score=ev.score,
                    confidence=ev.confidence,
                    passed=ev.passed,
                    rationale=ev.rationale,
                    details=ev.details,
                    created_at=ev.created_at,
                )
                session.add(db_ev)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_evaluations(self, trace_id: str) -> List[Evaluation]:
        session = self._get_session()
        try:
            db_evals = session.query(DBEvaluation).filter_by(trace_id=trace_id).all()
            return [
                Evaluation(
                    eval_id=UUID(e.eval_id),
                    trace_id=e.trace_id,
                    trajectory_id=uuid4(),
                    target_node_id=e.target_node_id,
                    evaluator_name=e.evaluator_name,
                    evaluator_layer=e.evaluator_layer,
                    evaluator_version=e.evaluator_version,
                    score=e.score,
                    confidence=e.confidence,
                    passed=e.passed,
                    rationale=e.rationale,
                    details=e.details,
                    created_at=e.created_at,
                )
                for e in db_evals
            ]
        finally:
            session.close()

    def save_failures(self, trace_id: str, failures: List[Failure]):
        if not failures:
            return
        session = self._get_session()
        try:
            for f in failures:
                db_f = DBFailure(
                    failure_id=str(f.failure_id),
                    trace_id=trace_id,
                    node_id=f.node_id,
                    category=f.category.value,
                    subcategory=f.subcategory,
                    severity=f.severity,
                    description=f.description,
                    is_terminal=f.is_terminal,
                )
                session.add(db_f)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_failures(self, trace_id: str) -> List[Failure]:
        session = self._get_session()
        try:
            db_fails = session.query(DBFailure).filter_by(trace_id=trace_id).all()
            return [
                Failure(
                    failure_id=UUID(f.failure_id),
                    trajectory_id=uuid4(),
                    node_id=f.node_id,
                    category=FailureCategory(f.category),
                    subcategory=f.subcategory,
                    severity=f.severity,
                    description=f.description,
                    is_terminal=f.is_terminal,
                )
                for f in db_fails
            ]
        finally:
            session.close()

    def save_root_cause(self, trace_id: str, root_cause: RootCause):
        session = self._get_session()
        try:
            existing = session.query(DBRootCause).filter_by(trace_id=trace_id).first()
            if existing:
                existing.primary_failure_node_id = root_cause.primary_failure_node_id
                existing.primary_category = root_cause.primary_category.value
                existing.confidence_score = root_cause.confidence_score
                existing.propagation_chain = root_cause.propagation_chain
                existing.explanation = root_cause.explanation
            else:
                db_rc = DBRootCause(
                    root_cause_id=str(root_cause.root_cause_id),
                    trace_id=trace_id,
                    primary_failure_node_id=root_cause.primary_failure_node_id,
                    primary_category=root_cause.primary_category.value,
                    confidence_score=root_cause.confidence_score,
                    propagation_chain=root_cause.propagation_chain,
                    explanation=root_cause.explanation,
                )
                session.add(db_rc)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_root_cause(self, trace_id: str) -> Optional[RootCause]:
        session = self._get_session()
        try:
            db_rc = session.query(DBRootCause).filter_by(trace_id=trace_id).first()
            if not db_rc:
                return None
            return RootCause(
                root_cause_id=UUID(db_rc.root_cause_id),
                trajectory_id=uuid4(),
                primary_failure_node_id=db_rc.primary_failure_node_id,
                primary_category=FailureCategory(db_rc.primary_category),
                confidence_score=db_rc.confidence_score,
                propagation_chain=db_rc.propagation_chain,
                explanation=db_rc.explanation,
            )
        finally:
            session.close()

    def save_dataset_item(self, item: DatasetItem):
        session = self._get_session()
        try:
            db_item = DBDatasetItem(
                item_id=str(item.item_id),
                dataset_id=item.dataset_id,
                source_trace_id=item.source_trace_id,
                input_prompt=item.input_prompt,
                expected_outcome=item.expected_outcome,
                expected_trajectory_schema=item.expected_trajectory_schema,
                assertions=item.assertions,
                tags=item.tags,
                created_at=item.created_at,
            )
            session.add(db_item)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_dataset_items(self, dataset_id: str) -> List[DatasetItem]:
        session = self._get_session()
        try:
            db_items = session.query(DBDatasetItem).filter_by(dataset_id=dataset_id).all()
            return [
                DatasetItem(
                    item_id=UUID(i.item_id),
                    dataset_id=i.dataset_id,
                    source_trace_id=i.source_trace_id,
                    input_prompt=i.input_prompt,
                    expected_outcome=i.expected_outcome,
                    expected_trajectory_schema=i.expected_trajectory_schema,
                    assertions=i.assertions,
                    tags=i.tags,
                    created_at=i.created_at,
                )
                for i in db_items
            ]
        finally:
            session.close()

    def list_datasets(self) -> Dict[str, int]:
        session = self._get_session()
        try:
            items = session.query(DBDatasetItem).all()
            counts: Dict[str, int] = {}
            for i in items:
                counts[i.dataset_id] = counts.get(i.dataset_id, 0) + 1
            return counts
        finally:
            session.close()

    def get_health_summary(self) -> Dict[str, Any]:
        """Inspired by OpenSearch agent-health: aggregates activity, tool stats, and error distribution."""
        session = self._get_session()
        try:
            trajs = session.query(DBTrajectory).all()
            total_trajectories = len(trajs)
            if total_trajectories == 0:
                return {
                    "total_trajectories": 0,
                    "success_rate": 1.0,
                    "tool_usage_counts": {},
                    "failure_category_counts": {},
                    "total_cost_usd": 0.0,
                    "avg_latency_ms": 0.0,
                }

            successful = sum(1 for t in trajs if t.is_success is not False)
            total_cost = sum(t.total_cost_usd for t in trajs)
            total_latency = sum(t.total_latency_ms for t in trajs)

            tool_counts: Dict[str, int] = {}
            for t in trajs:
                for node in (t.nodes or []):
                    if node.get("event_type") == "tool_call":
                        tname = node.get("payload", {}).get("tool_call", {}).get("tool_name", "unknown")
                        tool_counts[tname] = tool_counts.get(tname, 0) + 1

            failures = session.query(DBFailure).all()
            failure_counts: Dict[str, int] = {}
            for f in failures:
                failure_counts[f.category] = failure_counts.get(f.category, 0) + 1

            return {
                "total_trajectories": total_trajectories,
                "success_rate": round(successful / total_trajectories, 3),
                "tool_usage_counts": tool_counts,
                "failure_category_counts": failure_counts,
                "total_cost_usd": round(total_cost, 6),
                "avg_latency_ms": round(total_latency / total_trajectories, 2),
            }
        finally:
            session.close()


# Alias for backward compatibility across server and CLI
MemoryRepository = PersistentRepository
default_repository = PersistentRepository()
