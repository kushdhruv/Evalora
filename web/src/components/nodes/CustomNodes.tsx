// web/src/components/nodes/CustomNodes.tsx - Custom React Flow Node Components

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
  AlertTriangle,
  RotateCcw,
} from 'lucide-react';
import { TrajectoryNode } from '../../types';

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
        background: '#131b2c',
        border: `1.5px solid ${isRootCause ? '#f43f5e' : isSelected ? '#3b82f6' : '#2a3852'}`,
        borderRadius: 8,
        padding: '10px 12px',
        color: '#f8fafc',
        boxShadow: isRootCause
          ? '0 0 16px rgba(244, 63, 94, 0.45)'
          : isSelected
          ? '0 0 14px rgba(59, 130, 246, 0.35)'
          : '0 4px 10px rgba(0,0,0,0.3)',
      }}
      className={isRootCause ? 'root-cause-glow' : ''}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#3b82f6' }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 700, color: '#60a5fa' }}>
          <Compass size={14} />
          <span>PLAN</span>
        </div>
        <span style={{ fontSize: 10, fontFamily: 'monospace', color: '#94a3b8' }}>
          {node.node_id}
        </span>
      </div>
      <div style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc', marginBottom: 6 }}>
        {node.label || 'Strategy Plan'}
      </div>
      {node.payload.content && (
        <div
          style={{
            fontSize: 11,
            color: '#94a3b8',
            maxHeight: 36,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
          }}
        >
          {node.payload.content}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: '#3b82f6' }} />
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
        background: '#131b2c',
        border: `1.5px solid ${isRootCause ? '#f43f5e' : isError ? '#f43f5e' : isSelected ? '#3b82f6' : '#2a3852'}`,
        borderRadius: 8,
        padding: '10px 12px',
        color: '#f8fafc',
        boxShadow: isRootCause
          ? '0 0 18px rgba(244, 63, 94, 0.5)'
          : isSelected
          ? '0 0 14px rgba(59, 130, 246, 0.35)'
          : '0 4px 10px rgba(0,0,0,0.3)',
      }}
      className={isRootCause ? 'root-cause-glow' : ''}
    >
      <Handle type="target" position={Position.Top} style={{ background: isError ? '#f43f5e' : '#10b981' }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 700, color: '#f59e0b' }}>
          <Wrench size={14} />
          <span>TOOL CALL</span>
        </div>
        {isRootCause ? (
          <span className="badge badge-rose" style={{ fontSize: 9.5 }}>ROOT CAUSE</span>
        ) : isError ? (
          <span className="badge badge-rose" style={{ fontSize: 9.5 }}>ERROR</span>
        ) : (
          <span className="badge badge-emerald" style={{ fontSize: 9.5 }}>OK</span>
        )}
      </div>

      <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginBottom: 4, fontFamily: 'monospace' }}>
        {toolName}()
      </div>

      {isError && node.payload.tool_call?.error_message && (
        <div
          style={{
            fontSize: 10.5,
            color: '#fb7185',
            background: 'rgba(244, 63, 94, 0.1)',
            padding: '3px 6px',
            borderRadius: 4,
            marginBottom: 6,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {node.payload.tool_call.error_message}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10.5, color: '#64748b' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <Clock size={11} /> {duration.toFixed(1)}ms
        </span>
        {cost > 0 && (
          <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <Coins size={11} /> ${cost.toFixed(4)}
          </span>
        )}
        <span style={{ fontFamily: 'monospace' }}>{node.node_id}</span>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: isError ? '#f43f5e' : '#10b981' }} />
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
        background: '#131b2c',
        border: `1.5px solid ${isRootCause ? '#f43f5e' : isSelected ? '#3b82f6' : '#2a3852'}`,
        borderRadius: 8,
        padding: '10px 12px',
        color: '#f8fafc',
        boxShadow: isRootCause
          ? '0 0 16px rgba(244, 63, 94, 0.45)'
          : isSelected
          ? '0 0 14px rgba(59, 130, 246, 0.35)'
          : '0 4px 10px rgba(0,0,0,0.3)',
      }}
      className={isRootCause ? 'root-cause-glow' : ''}
    >
      <Handle type="target" position={Position.Top} style={{ background: '#06b6d4' }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 700, color: '#06b6d4' }}>
          <Database size={14} />
          <span>{isRead ? 'MEMORY READ' : 'MEMORY WRITE'}</span>
        </div>
        <span className="badge badge-blue" style={{ fontSize: 9.5 }}>
          {mem.operation || 'query'}
        </span>
      </div>

      <div style={{ fontSize: 12, fontWeight: 600, color: '#f8fafc', marginBottom: 4 }}>
        {node.label || 'Context Retrieval'}
      </div>

      {mem.retrieved_keys && mem.retrieved_keys.length > 0 && (
        <div style={{ fontSize: 10.5, color: '#94a3b8', marginBottom: 4 }}>
          Keys: {mem.retrieved_keys.slice(0, 2).join(', ')}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10.5, color: '#64748b' }}>
        <span>Node: {node.node_id}</span>
        {mem.similarity_scores && mem.similarity_scores.length > 0 && (
          <span style={{ color: '#34d399' }}>
            Sim: {(mem.similarity_scores[0] * 100).toFixed(0)}%
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: '#06b6d4' }} />
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
        background: '#131b2c',
        border: `1.5px solid ${isRootCause ? '#f43f5e' : isFailed ? '#f43f5e' : isSelected ? '#3b82f6' : '#2a3852'}`,
        borderRadius: 8,
        padding: '10px 12px',
        color: '#f8fafc',
        boxShadow: isRootCause
          ? '0 0 18px rgba(244, 63, 94, 0.5)'
          : isSelected
          ? '0 0 14px rgba(59, 130, 246, 0.35)'
          : '0 4px 10px rgba(0,0,0,0.3)',
      }}
      className={isRootCause ? 'root-cause-glow' : ''}
    >
      <Handle type="target" position={Position.Top} style={{ background: isFailed ? '#f43f5e' : '#10b981' }} />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 11,
            fontWeight: 700,
            color: isFailed ? '#fb7185' : '#34d399',
          }}
        >
          {isFailed ? <AlertOctagon size={14} /> : <CheckCircle2 size={14} />}
          <span>FINAL OUTCOME</span>
        </div>
        <span className={`badge ${isFailed ? 'badge-rose' : 'badge-emerald'}`} style={{ fontSize: 9.5 }}>
          {isFailed ? 'FAILED' : 'SUCCESS'}
        </span>
      </div>

      {node.payload.content && (
        <div
          style={{
            fontSize: 11,
            color: '#cbd5e1',
            maxHeight: 48,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            display: '-webkit-box',
            WebkitLineClamp: 3,
            WebkitBoxOrient: 'vertical',
            marginBottom: 6,
          }}
        >
          "{node.payload.content}"
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10.5, color: '#64748b' }}>
        <span>Node: {node.node_id}</span>
        {evaluationScore !== undefined && (
          <span style={{ fontWeight: 600, color: evaluationScore >= 0.85 ? '#34d399' : '#fb7185' }}>
            Score: {(evaluationScore * 100).toFixed(0)}%
          </span>
        )}
      </div>
    </div>
  );
}
