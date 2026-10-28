// web/src/components/trajectory/TimelineWaterfall.tsx - Minimalistic Phonic Span Duration Waterfall View

import React, { useMemo } from 'react';
import type { TrajectoryDetailResponse, TrajectoryNode } from '../../types';

interface TimelineWaterfallProps {
  detail: TrajectoryDetailResponse;
  selectedNodeId: string | null;
  onSelectNode: (node: TrajectoryNode) => void;
}

export function TimelineWaterfall({ detail, selectedNodeId, onSelectNode }: TimelineWaterfallProps) {
  const { trajectory, failures, root_cause } = detail;

  const failureNodeIds = useMemo(() => new Set(failures.map((f) => f.node_id)), [failures]);
  const rootCauseNodeId = root_cause?.primary_failure_node_id || null;

  // Calculate timeline relative offsets
  const { sortedNodes, totalDurationMs } = useMemo(() => {
    const nodes = [...trajectory.nodes];
    const totalMs = Math.max(1, trajectory.total_latency_ms || 100);

    let cumulativeOffset = 0;
    const computed = nodes.map((node) => {
      const dur = Math.max(5, node.duration_ms ?? node.payload.duration_ms ?? 10);
      const startOffset = cumulativeOffset;
      cumulativeOffset += dur;
      return {
        ...node,
        computedDuration: dur,
        computedOffset: startOffset,
      };
    });

    return {
      sortedNodes: computed,
      totalDurationMs: Math.max(cumulativeOffset, totalMs),
    };
  }, [trajectory]);

  return (
    <div style={{ padding: 18, height: '100%', overflowY: 'auto', background: 'var(--bg-canvas)' }}>
      {/* Waterfall Header Summary */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '12px 16px',
          marginBottom: 16,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
            Span Execution Waterfall
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Sub-millisecond duration distribution across {trajectory.nodes.length} agent steps
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Total Latency
            </div>
            <div style={{ fontSize: 15, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
              {totalDurationMs.toFixed(1)} ms
            </div>
          </div>
        </div>
      </div>

      {/* Waterfall Axis Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 10,
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: 6,
          marginBottom: 12,
        }}
      >
        <span>0 ms</span>
        <span>{(totalDurationMs * 0.25).toFixed(0)} ms</span>
        <span>{(totalDurationMs * 0.5).toFixed(0)} ms</span>
        <span>{(totalDurationMs * 0.75).toFixed(0)} ms</span>
        <span>{totalDurationMs.toFixed(0)} ms</span>
      </div>

      {/* Waterfall Span Rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
        {sortedNodes.map((item, idx) => {
          const isSelected = item.node_id === selectedNodeId;
          const isError = failureNodeIds.has(item.node_id) || item.payload.tool_call?.is_error;
          const isRoot = item.node_id === rootCauseNodeId;

          const leftPercent = (item.computedOffset / totalDurationMs) * 100;
          const widthPercent = Math.max(3, (item.computedDuration / totalDurationMs) * 100);

          let barColor = 'var(--text-muted)';
          if (item.event_type === 'tool_call') barColor = isError ? 'var(--rose)' : 'var(--amber)';
          else if (item.event_type.startsWith('memory')) barColor = 'var(--purple)';
          else if (item.event_type === 'final_outcome') barColor = isError ? 'var(--rose)' : 'var(--emerald)';

          return (
            <div
              key={item.node_id}
              onClick={() => onSelectNode(item)}
              style={{
                background: isSelected ? 'var(--bg-elevated)' : 'var(--bg-surface)',
                border: `1px solid ${
                  isRoot
                    ? 'var(--rose)'
                    : isSelected
                    ? 'var(--border-focus)'
                    : 'var(--border-subtle)'
                }`,
                borderRadius: 'var(--radius-sm)',
                padding: '8px 12px',
                cursor: 'pointer',
                transition: 'all 0.12s ease',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
                boxShadow: isSelected ? '0 1px 3px rgba(0,0,0,0.08)' : undefined,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 10,
                      color: 'var(--text-muted)',
                      width: 20,
                    }}
                  >
                    #{idx + 1}
                  </span>
                  <span
                    className={`badge ${
                      item.event_type === 'tool_call'
                        ? isError
                          ? 'badge-rose'
                          : 'badge-amber'
                        : item.event_type === 'final_outcome'
                        ? isError
                          ? 'badge-rose'
                          : 'badge-emerald'
                        : item.event_type.startsWith('memory')
                        ? 'badge-purple'
                        : 'badge-muted'
                    }`}
                    style={{ fontSize: 9 }}
                  >
                    {item.event_type.toUpperCase()}
                  </span>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
                    {item.label}
                  </span>
                  {isRoot && <span className="badge badge-rose">ROOT CAUSE</span>}
                  {isError && !isRoot && <span className="badge badge-rose">ERROR</span>}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                  <span>{item.computedDuration.toFixed(1)} ms</span>
                </div>
              </div>

              {/* Relative Timeline Bar */}
              <div
                style={{
                  height: 5,
                  width: '100%',
                  background: 'var(--bg-canvas)',
                  borderRadius: 3,
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    position: 'absolute',
                    left: `${leftPercent}%`,
                    width: `${widthPercent}%`,
                    height: '100%',
                    background: barColor,
                    borderRadius: 3,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
