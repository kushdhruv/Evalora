// web/src/components/comparison/GoldenPathComparator.tsx - Clean Minimalist Golden Path Comparator

import React, { useState } from 'react';
import { GitCompare, Check, AlertTriangle, ArrowRight, Zap } from 'lucide-react';
import type { GoldenPathComparison, TrajectoryDetailResponse } from '../../types';
import { compareGoldenPath } from '../../services/api';

interface GoldenPathComparatorProps {
  detail: TrajectoryDetailResponse;
}

export function GoldenPathComparator({ detail }: GoldenPathComparatorProps) {
  const { trajectory } = detail;
  const [expectedInput, setExpectedInput] = useState<string>('sqlite_query, send_email');
  const [comparison, setComparison] = useState<GoldenPathComparison | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunComparison = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const tools = expectedInput
        .split(',')
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      const res = await compareGoldenPath(trajectory.trace_id, tools);
      setComparison(res);
    } catch (err: any) {
      setError(err.message || 'Comparison failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ padding: 18, height: '100%', overflowY: 'auto', background: 'var(--bg-canvas)' }}>
      {/* Comparator Header */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '14px 18px',
          marginBottom: 16,
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <GitCompare size={15} color="var(--text-primary)" />
          <h3 style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-primary)' }}>
            Golden Path Trajectory Comparator
          </h3>
        </div>
        <p style={{ fontSize: 11.5, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Benchmark actual tool invocations against an optimal Golden Path sequence to verify algorithmic fidelity and identify hallucinated steps.
        </p>

        {/* Target Sequence Config Bar */}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
              Expected Golden Tool Sequence (comma separated)
            </label>
            <input
              type="text"
              value={expectedInput}
              onChange={(e) => setExpectedInput(e.target.value)}
              placeholder="e.g. sqlite_query, send_email"
              style={{
                width: '100%',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '6px 10px',
                color: 'var(--text-primary)',
                fontSize: 12,
                fontFamily: 'var(--font-mono)',
                marginTop: 4,
              }}
            />
          </div>
          <button
            onClick={handleRunComparison}
            disabled={isLoading}
            className="btn btn-primary"
            style={{ marginTop: 18, height: 32 }}
          >
            <Zap size={13} /> {isLoading ? 'Comparing...' : 'Compare Trajectory'}
          </button>
        </div>
        {error && <div style={{ color: 'var(--rose-text)', fontSize: 11, marginTop: 8 }}>{error}</div>}
      </div>

      {/* Comparison Results */}
      {comparison && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Metrics Match Card */}
          <div
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '14px 18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              boxShadow: 'var(--card-shadow)',
            }}
          >
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Sequence Fidelity Score
              </div>
              <div
                style={{
                  fontSize: 24,
                  fontWeight: 700,
                  fontFamily: 'var(--font-mono)',
                  color: comparison.exact_match ? 'var(--emerald-text)' : 'var(--amber-text)',
                  marginTop: 2,
                }}
              >
                {(comparison.sequence_match_ratio * 100).toFixed(0)}%
              </div>
            </div>
            <div>
              {comparison.exact_match ? (
                <span className="badge badge-emerald" style={{ fontSize: 11, padding: '4px 10px' }}>
                  <Check size={12} /> Exact Sequence Match
                </span>
              ) : (
                <span className="badge badge-rose" style={{ fontSize: 11, padding: '4px 10px' }}>
                  <AlertTriangle size={12} /> Sequence Divergence
                </span>
              )}
            </div>
          </div>

          {/* Side-by-Side Path Diff */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {/* Actual Path */}
            <div
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '12px 16px',
                boxShadow: 'var(--card-shadow)',
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10 }}>
                Actual Executed Sequence
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {comparison.actual_tool_sequence.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>No tools called in this trace</div>
                ) : (
                  comparison.actual_tool_sequence.map((tool, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: 'var(--bg-elevated)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '6px 10px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        fontSize: 11.5,
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-primary)',
                      }}
                    >
                      <span style={{ color: 'var(--text-muted)', width: 16 }}>{idx + 1}.</span>
                      <span>{tool}()</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Expected Golden Path */}
            <div
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '12px 16px',
                boxShadow: 'var(--card-shadow)',
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10 }}>
                Target Golden Path
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {comparison.expected_tool_sequence.map((tool, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '6px 10px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      fontSize: 11.5,
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--text-primary)',
                    }}
                  >
                    <span style={{ color: 'var(--text-muted)', width: 16 }}>{idx + 1}.</span>
                    <span>{tool}()</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
