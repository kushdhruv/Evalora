// web/src/components/trajectory/TimelineWaterfall.tsx - New Relic Inspired Span Duration Waterfall View

import React, { useMemo } from 'react';
import { Clock, AlertTriangle, AlertCircle } from 'lucide-react';
import { TrajectoryDetailResponse, TrajectoryNode } from '../../types';

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
    <div style={{ padding: 18, height: '100%', overflowY: 'auto', background: '#07090e' }}>
      {/* Waterfall Header Summary */}
      <div
        style={{
          background: '#0e131d',
          border: '1px solid #1c2638',
          borderRadius: 8,
          padding: '12px 16px',
          marginBottom: 16,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
            Span Execution Waterfall
          </div>
          <div style={{ fontSize: 11, color: '#94a3b8' }}>
            Microsecond duration distribution across {trajectory.nodes.length} agent steps
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase' }}>
              Total Latency
            </div>
            <div style={{ fontSize: 15, fontWeight: 700, fontFamily: 'monospace', color: '#60a5fa' }}>
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
          fontFamily: 'monospace',
          color: '#64748b',
          borderBottom: '1px solid #1c2638',
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {sortedNodes.map((item, idx) => {
          const isSelected = item.node_id === selectedNodeId;
          const isError = failureNodeIds.has(item.node_id) || item.payload.tool_call?.is_error;
          const isRoot = item.node_id === rootCauseNodeId;

          const leftPercent = (item.computedOffset / totalDurationMs) * 100;
          const widthPercent = Math.max(4, (item.computedDuration / totalDurationMs) * 100);

          let barColor = '#3b82f6';
          if (item.event_type === 'tool_call') barColor = isError ? '#f43f5e' : '#f59e0b';
          else if (item.event_type.startsWith('memory')) barColor = '#06b6d4';
          else if (item.event_type === 'final_outcome') barColor = isError ? '#f43f5e' : '#10b981';

          return (
            <div
              key={item.node_id}
              onClick={() => onSelectNode(item)}
              style={{
                background: isSelected ? '#1b263b' : '#0e131d',
                border: `1px solid ${isRoot ? '#f43f5e' : isSelected ? '#3b82f6' : '#1c2638'}`,
                borderRadius: 6,
                padding: '8px 12px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span
                    style={{
                      fontFamily: 'monospace',
                      fontSize: 10,
                      color: '#64748b',
                      width: 18,
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
                        ? 'badge-blue'
                        : 'badge-muted'
                    }`}
                    style={{ fontSize: 9.5 }}
                  >
                    {item.event_type.toUpperCase()}
                  </span>
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc' }}>
                    {item.label}
                  </span>
                  {isRoot && <span className="badge badge-rose">ROOT CAUSE FAULT</span>}
                  {isError && !isRoot && <span className="badge badge-rose">ERROR</span>}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 11, fontFamily: 'monospace', color: '#94a3b8' }}>
                  <span>{item.computedDuration.toFixed(1)} ms</span>
                </div>
              </div>

              {/* Relative Timeline Bar */}
              <div
                style={{
                  height: 6,
                  width: '100%',
                  background: '#07090e',
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
                    boxShadow: isRoot ? '0 0 8px #f43f5e' : undefined,
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
