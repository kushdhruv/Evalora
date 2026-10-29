// web/src/components/trajectory/InspectorDrawer.tsx - Clean Minimalist Node & Root-Cause Inspector Drawer

import React, { useState } from 'react';
import {
  X,
  AlertTriangle,
  Brain,
  ThumbsUp,
  ThumbsDown,
  BookmarkPlus,
} from 'lucide-react';
import type { Evaluation, Failure, RootCause, TrajectoryNode } from '../../types';
import { curateTraceToDataset } from '../../services/api';

interface InspectorDrawerProps {
  node: TrajectoryNode | null;
  evaluations: Evaluation[];
  failures: Failure[];
  rootCause: RootCause | null;
  traceId: string;
  onClose: () => void;
}

export function InspectorDrawer({
  node,
  evaluations,
  failures,
  rootCause,
  traceId,
  onClose,
}: InspectorDrawerProps) {
  const [curating, setCurating] = useState<boolean>(false);
  const [curatedSuccess, setCuratedSuccess] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  if (!node) return null;

  const nodeEvaluations = evaluations.filter((e) => e.target_node_id === node.node_id);
  const nodeFailures = failures.filter((f) => f.node_id === node.node_id);
  const isRootCause = rootCause?.primary_failure_node_id === node.node_id;

  const handleCurate = async () => {
    setCurating(true);
    try {
      await curateTraceToDataset(
        'regression_benchmark_set',
        traceId,
        node.label,
        node.payload.content || 'Expected correct execution'
      );
      setCuratedSuccess(true);
      setTimeout(() => setCuratedSuccess(false), 3000);
    } catch (e) {
      console.error('Failed to curate:', e);
    } finally {
      setCurating(false);
    }
  };

  return (
    <aside className="inspector-panel">
      {/* Header */}
      <div className="inspector-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <span className="badge badge-muted" style={{ fontSize: 9.5 }}>
              {node.event_type.toUpperCase()}
            </span>
            {node.agent_id && (
              <span className="badge badge-purple" style={{ fontSize: 9.5 }}>
                Agent: {node.agent_id}
              </span>
            )}
            {node.recipient_agent && (
              <span className="badge badge-blue" style={{ fontSize: 9.5 }}>
                → {node.recipient_agent}
              </span>
            )}
            <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
              {node.node_id}
            </span>
          </div>
          <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-primary)', marginTop: 3 }}>
            {node.label}
          </div>
        </div>
        <button
          onClick={onClose}
          style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          title="Close inspector"
        >
          <X size={16} />
        </button>
      </div>

      {/* Body */}
      <div className="inspector-body">
        {/* Root Cause Alert Banner */}
        {isRootCause && rootCause && (
          <div
            style={{
              background: 'var(--rose-bg)',
              border: '1px solid var(--rose-border)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 14px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--rose-text)', fontWeight: 700, fontSize: 11.5 }}>
              <AlertTriangle size={14} /> PRIMARY ROOT CAUSE IDENTIFIED
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--text-primary)', marginTop: 6, lineHeight: 1.4 }}>
              {rootCause.explanation}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>
              Attribution Confidence: {(rootCause.confidence_score * 100).toFixed(0)}%
            </div>
          </div>
        )}

        {/* Human Feedback Bar */}
        <div
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '8px 12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>
            Human Verification
          </span>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              onClick={() => setFeedback('up')}
              className={`btn ${feedback === 'up' ? 'btn-success' : 'btn-secondary'}`}
              style={{ padding: '3px 7px', fontSize: 10.5 }}
              title="Mark response as accurate"
            >
              <ThumbsUp size={11} /> Accurate
            </button>
            <button
              onClick={() => setFeedback('down')}
              className={`btn ${feedback === 'down' ? 'btn-danger' : 'btn-secondary'}`}
              style={{ padding: '3px 7px', fontSize: 10.5 }}
              title="Mark response as flawed"
            >
              <ThumbsDown size={11} /> Flawed
            </button>
          </div>
        </div>

        {/* Curate to Dataset Button */}
        <button
          onClick={handleCurate}
          disabled={curating}
          className="btn btn-secondary"
          style={{ width: '100%', justifyContent: 'center', padding: '7px 12px' }}
        >
          <BookmarkPlus size={13} />
          {curatedSuccess
            ? '✓ Added to CI Regression Set!'
            : curating
            ? 'Curating...'
            : 'Curate Trace to CI Regression Gate'}
        </button>

        {/* Step Timing & Cost */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <div className="kpi-card" style={{ padding: '8px 10px' }}>
            <span className="kpi-label" style={{ fontSize: 9.5 }}>Duration</span>
            <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)' }}>
              {(node.duration_ms ?? node.payload.duration_ms ?? 0).toFixed(1)} ms
            </span>
          </div>
          <div className="kpi-card" style={{ padding: '8px 10px' }}>
            <span className="kpi-label" style={{ fontSize: 9.5 }}>Cost</span>
            <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--emerald-text)' }}>
              ${(node.cost_usd ?? node.payload.cost_usd ?? 0).toFixed(4)}
            </span>
          </div>
        </div>

        {/* 4-Layer Evaluator Judgments */}
        <div>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Brain size={13} color="var(--purple-text)" /> Evaluator Judgments ({nodeEvaluations.length})
          </div>
          {nodeEvaluations.length === 0 ? (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
              No individual evaluations recorded on this step.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {nodeEvaluations.map((ev) => (
                <div
                  key={ev.eval_id}
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {ev.evaluator_name} <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>({ev.evaluator_layer})</span>
                    </span>
                    <span className={`badge ${ev.passed ? 'badge-emerald' : 'badge-rose'}`} style={{ fontSize: 9.5 }}>
                      {(ev.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  {ev.rationale && (
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.35 }}>
                      {ev.rationale}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Failures on this Node */}
        {nodeFailures.length > 0 && (
          <div>
            <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--rose-text)', marginBottom: 8 }}>
              Detected Failures ({nodeFailures.length})
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {nodeFailures.map((f) => (
                <div
                  key={f.failure_id}
                  style={{
                    background: 'var(--rose-bg)',
                    border: '1px solid var(--rose-border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, fontWeight: 700, color: 'var(--rose-text)' }}>
                    <span>{f.category.toUpperCase()}</span>
                    <span>{f.severity}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-primary)', marginTop: 4 }}>
                    {f.description}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Raw Payload Inspector */}
        <div>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 6 }}>
            Raw Step Payload
          </div>
          <pre className="code-block">
            {JSON.stringify(node.payload, null, 2)}
          </pre>
        </div>
      </div>
    </aside>
  );
}
