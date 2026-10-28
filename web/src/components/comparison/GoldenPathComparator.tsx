// web/src/components/comparison/GoldenPathComparator.tsx - OpenSearch Inspired Trajectory & Golden Path Comparison

import React, { useState } from 'react';
import { GitCompare, Check, AlertTriangle, ArrowRight, Zap } from 'lucide-react';
import { GoldenPathComparison, TrajectoryDetailResponse } from '../../types';
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
    <div style={{ padding: 18, height: '100%', overflowY: 'auto', background: '#07090e' }}>
      {/* Comparator Header */}
      <div
        style={{
          background: '#0e131d',
          border: '1px solid #1c2638',
          borderRadius: 8,
          padding: '14px 18px',
          marginBottom: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <GitCompare size={16} color="#60a5fa" />
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>
            Golden Path Trajectory Comparator
          </h3>
        </div>
        <p style={{ fontSize: 12, color: '#94a3b8', marginBottom: 12 }}>
          Benchmark actual tool invocations against an optimal Golden Path sequence to verify algorithmic fidelity and identify hallucinated steps.
        </p>

        {/* Target Sequence Config Bar */}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>
              Expected Golden Tool Sequence (comma separated)
            </label>
            <input
              type="text"
              value={expectedInput}
              onChange={(e) => setExpectedInput(e.target.value)}
              placeholder="e.g. sqlite_query, send_email"
              style={{
                width: '100%',
                background: '#07090e',
                border: '1px solid #2a3852',
                borderRadius: 4,
                padding: '6px 10px',
                color: '#f8fafc',
                fontSize: 12,
                fontFamily: 'monospace',
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
        {error && <div style={{ color: '#fb7185', fontSize: 11, marginTop: 8 }}>{error}</div>}
      </div>

      {/* Comparison Results */}
      {comparison && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Metrics Match Card */}
          <div
            style={{
              background: '#0e131d',
              border: `1px solid ${comparison.exact_match ? '#10b981' : '#f59e0b'}`,
              borderRadius: 8,
              padding: '14px 18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase' }}>
                Trajectory Fidelity
              </div>
              <div
                style={{
                  fontSize: 22,
                  fontWeight: 800,
                  fontFamily: 'monospace',
                  color: comparison.exact_match ? '#34d399' : '#fbbf24',
                }}
              >
                {(comparison.sequence_match_ratio * 100).toFixed(0)}% Match
              </div>
            </div>

            <div>
              {comparison.exact_match ? (
                <span className="badge badge-emerald" style={{ padding: '6px 12px', fontSize: 12 }}>
                  <Check size={14} /> EXACT GOLDEN PATH ADHERENCE
                </span>
              ) : (
                <span className="badge badge-amber" style={{ padding: '6px 12px', fontSize: 12 }}>
                  <AlertTriangle size={14} /> SEQUENCE ANOMALIES DETECTED
                </span>
              )}
            </div>
          </div>

          {/* Side-by-Side Table */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            {/* Left: Expected */}
            <div
              style={{
                background: '#0e131d',
                border: '1px solid #1c2638',
                borderRadius: 8,
                padding: '12px 14px',
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 700, color: '#60a5fa', marginBottom: 10 }}>
                Target Golden Sequence
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {comparison.expected_tool_sequence.map((tool, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: '#131b2c',
                      border: '1px solid #2a3852',
                      borderRadius: 4,
                      padding: '8px 10px',
                      fontSize: 11,
                      fontFamily: 'monospace',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                    }}
                  >
                    <span style={{ color: '#64748b' }}>#{idx + 1}</span>
                    <span style={{ color: '#f8fafc', fontWeight: 600 }}>{tool}()</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: Actual */}
            <div
              style={{
                background: '#0e131d',
                border: '1px solid #1c2638',
                borderRadius: 8,
                padding: '12px 14px',
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc', marginBottom: 10 }}>
                Actual Executed Sequence
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {comparison.actual_tool_sequence.length === 0 ? (
                  <div style={{ fontSize: 11, color: '#64748b', fontStyle: 'italic', padding: 8 }}>
                    No tool calls recorded in this trajectory.
                  </div>
                ) : (
                  comparison.actual_tool_sequence.map((tool, idx) => {
                    const expectedTool = comparison.expected_tool_sequence[idx];
                    const isMatch = tool === expectedTool;
                    return (
                      <div
                        key={idx}
                        style={{
                          background: isMatch ? 'rgba(16, 185, 129, 0.08)' : 'rgba(244, 63, 94, 0.08)',
                          border: `1px solid ${isMatch ? '#10b981' : '#f43f5e'}`,
                          borderRadius: 4,
                          padding: '8px 10px',
                          fontSize: 11,
                          fontFamily: 'monospace',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ color: '#64748b' }}>#{idx + 1}</span>
                          <span style={{ color: '#f8fafc', fontWeight: 600 }}>{tool}()</span>
                        </div>
                        {isMatch ? (
                          <span className="badge badge-emerald" style={{ fontSize: 9 }}>MATCH</span>
                        ) : (
                          <span className="badge badge-rose" style={{ fontSize: 9 }}>DEVIATION</span>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
