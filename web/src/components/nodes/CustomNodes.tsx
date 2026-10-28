// web/src/components/nodes/CustomNodes.tsx - Clean Minimalistic Phonic Node Components

import React from 'react';
import { Handle, Position } from '@xyflow/react';
import {
  Compass,
  Wrench,
  Database,
  CheckCircle2,
  AlertOctagon,
  Clock,
  Coins,
} from 'lucide-react';
import type { TrajectoryNode } from '../../types';

interface NodeData {
  node: TrajectoryNode;
  isRootCause: boolean;
  isInCascadePath: boolean;
  isSelected: boolean;
  evaluationScore?: number;
  hasFailed?: boolean;
}

export function PlanNode({ data }: { data: NodeData }) {
  const { node, isRootCause, isSelected } = data;
  return (
    <div
      style={{
        width: 240,
        background: 'var(--node-bg)',
        border: `1px solid ${
          isRootCause
            ? 'var(--rose)'
            : isSelected
            ? 'var(--border-focus)'
            : 'var(--border-subtle)'
        }`,
        borderRadius: 'var(--radius-md)',
        padding: '10px 12px',
        color: 'var(--text-primary)',
        boxShadow: isRootCause
          ? '0 0 0 1.5px var(--rose), 0 2px 8px var(--rose-glow)'
          : isSelected
          ? '0 0 0 1.5px var(--border-focus), var(--node-shadow)'
          : 'var(--node-shadow)',
        transition: 'all 0.15s ease',
      }}
      className={isRootCause ? 'root-cause-glow' : ''}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: 'var(--text-muted)', border: 'none', width: 6, height: 6 }}
      />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10.5, fontWeight: 700, color: 'var(--blue-text)' }}>
          <Compass size={13} />
          <span>PLAN</span>
        </div>
        <span style={{ fontSize: 9.5, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
          {node.node_id}
        </span>
      </div>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 5 }}>
        {node.label || 'Strategy Plan'}
      </div>
      {node.payload.content && (
        <div
          style={{
            fontSize: 11,
            color: 'var(--text-secondary)',
            maxHeight: 34,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            lineHeight: 1.4,
          }}
        >
          {node.payload.content}
        </div>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: 'var(--text-muted)', border: 'none', width: 6, height: 6 }}
      />
    </div>
  );
}

export function ToolCallNode({ data }: { data: NodeData }) {
  const { node, isRootCause, isSelected, hasFailed } = data;
  const toolName = node.payload.tool_call?.tool_name || node.label || 'tool';
  const isError = hasFailed || node.payload.tool_call?.is_error;
  const duration = node.duration_ms ?? node.payload.duration_ms ?? 0;
  const cost = node.cost_usd ?? node.payload.cost_usd ?? 0;

  return (
    <div
      style={{
        width: 250,
        background: 'var(--node-bg)',
        border: `1px solid ${
          isRootCause
            ? 'var(--rose)'
            : isError
            ? 'var(--rose-border)'
            : isSelected
            ? 'var(--border-focus)'
            : 'var(--border-subtle)'
        }`,
        borderRadius: 'var(--radius-md)',
        padding: '10px 12px',
        color: 'var(--text-primary)',
        boxShadow: isRootCause
          ? '0 0 0 1.5px var(--rose), 0 2px 8px var(--rose-glow)'
          : isSelected
          ? '0 0 0 1.5px var(--border-focus), var(--node-shadow)'
          : 'var(--node-shadow)',
        transition: 'all 0.15s ease',
      }}
      className={isRootCause ? 'root-cause-glow' : ''}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{
          background: isError ? 'var(--rose)' : 'var(--emerald)',
          border: 'none',
          width: 6,
          height: 6,
        }}
      />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10.5, fontWeight: 700, color: 'var(--amber-text)' }}>
          <Wrench size={13} />
          <span>TOOL CALL</span>
        </div>
        {isRootCause ? (
          <span className="badge badge-rose" style={{ fontSize: 9 }}>ROOT CAUSE</span>
        ) : isError ? (
          <span className="badge badge-rose" style={{ fontSize: 9 }}>ERROR</span>
        ) : (
          <span className="badge badge-emerald" style={{ fontSize: 9 }}>OK</span>
        )}
      </div>

      <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>
        {toolName}()
      </div>

      {isError && node.payload.tool_call?.error_message && (
        <div
          style={{
            fontSize: 10,
            color: 'var(--rose-text)',
            background: 'var(--rose-bg)',
            border: '1px solid var(--rose-border)',
            padding: '2px 6px',
            borderRadius: 'var(--radius-xs)',
            marginBottom: 6,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {node.payload.tool_call.error_message}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <Clock size={11} /> {duration.toFixed(1)}ms
        </span>
        {cost > 0 && (
          <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <Coins size={11} /> ${cost.toFixed(4)}
          </span>
        )}
        <span style={{ fontFamily: 'var(--font-mono)' }}>{node.node_id}</span>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          background: isError ? 'var(--rose)' : 'var(--emerald)',
          border: 'none',
          width: 6,
          height: 6,
        }}
      />
    </div>
  );
}

export function MemoryNode({ data }: { data: NodeData }) {
  const { node, isRootCause, isSelected } = data;
  const mem = node.payload.memory_event || {};
  const isRead = node.event_type === 'memory_read';

  return (
    <div
      style={{
        width: 240,
        background: 'var(--node-bg)',
        border: `1px solid ${
          isRootCause
            ? 'var(--rose)'
            : isSelected
            ? 'var(--border-focus)'
            : 'var(--border-subtle)'
        }`,
        borderRadius: 'var(--radius-md)',
        padding: '10px 12px',
        color: 'var(--text-primary)',
        boxShadow: isRootCause
          ? '0 0 0 1.5px var(--rose), 0 2px 8px var(--rose-glow)'
          : isSelected
          ? '0 0 0 1.5px var(--border-focus), var(--node-shadow)'
          : 'var(--node-shadow)',
        transition: 'all 0.15s ease',
      }}
      className={isRootCause ? 'root-cause-glow' : ''}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: 'var(--purple)', border: 'none', width: 6, height: 6 }}
      />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 10.5, fontWeight: 700, color: 'var(--purple-text)' }}>
          <Database size={13} />
          <span>{isRead ? 'MEMORY READ' : 'MEMORY WRITE'}</span>
        </div>
        <span className="badge badge-purple" style={{ fontSize: 9 }}>
          {mem.operation || 'query'}
        </span>
      </div>

      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
        {node.label || 'Context Retrieval'}
      </div>

      {mem.retrieved_keys && mem.retrieved_keys.length > 0 && (
        <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginBottom: 4 }}>
          Keys: {mem.retrieved_keys.slice(0, 2).join(', ')}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)' }}>
        <span style={{ fontFamily: 'var(--font-mono)' }}>{node.node_id}</span>
        {mem.similarity_scores && mem.similarity_scores.length > 0 && (
          <span style={{ color: 'var(--emerald-text)', fontWeight: 600 }}>
            Sim: {(mem.similarity_scores[0] * 100).toFixed(0)}%
          </span>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: 'var(--purple)', border: 'none', width: 6, height: 6 }}
      />
    </div>
  );
}

export function OutcomeNode({ data }: { data: NodeData }) {
  const { node, isRootCause, isSelected, hasFailed, evaluationScore } = data;
  const isFailed = hasFailed;

  return (
    <div
      style={{
        width: 260,
        background: 'var(--node-bg)',
        border: `1px solid ${
          isRootCause
            ? 'var(--rose)'
            : isFailed
            ? 'var(--rose-border)'
            : isSelected
            ? 'var(--border-focus)'
            : 'var(--border-subtle)'
        }`,
        borderRadius: 'var(--radius-md)',
        padding: '10px 12px',
        color: 'var(--text-primary)',
        boxShadow: isRootCause
          ? '0 0 0 1.5px var(--rose), 0 2px 8px var(--rose-glow)'
          : isSelected
          ? '0 0 0 1.5px var(--border-focus), var(--node-shadow)'
          : 'var(--node-shadow)',
        transition: 'all 0.15s ease',
      }}
      className={isRootCause ? 'root-cause-glow' : ''}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{
          background: isFailed ? 'var(--rose)' : 'var(--emerald)',
          border: 'none',
          width: 6,
          height: 6,
        }}
      />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            fontSize: 10.5,
            fontWeight: 700,
            color: isFailed ? 'var(--rose-text)' : 'var(--emerald-text)',
          }}
        >
          {isFailed ? <AlertOctagon size={13} /> : <CheckCircle2 size={13} />}
          <span>FINAL OUTCOME</span>
        </div>
        <span className={`badge ${isFailed ? 'badge-rose' : 'badge-emerald'}`} style={{ fontSize: 9 }}>
          {isFailed ? 'FAILED' : 'SUCCESS'}
        </span>
      </div>

      {node.payload.content && (
        <div
          style={{
            fontSize: 11,
            color: 'var(--text-secondary)',
            maxHeight: 46,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            marginBottom: 6,
            lineHeight: 1.4,
          }}
        >
          "{node.payload.content}"
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)' }}>
        <span style={{ fontFamily: 'var(--font-mono)' }}>{node.node_id}</span>
        {evaluationScore !== undefined && (
          <span style={{ fontWeight: 600, color: evaluationScore >= 0.85 ? 'var(--emerald-text)' : 'var(--rose-text)' }}>
            Score: {(evaluationScore * 100).toFixed(0)}%
          </span>
        )}
      </div>
    </div>
  );
}
