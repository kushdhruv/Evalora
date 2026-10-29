// web/src/components/trajectory/FlowCanvas.tsx - Clean Minimalist React Flow Causal DAG Visualizer

import { useMemo, useState } from 'react';
import {
  ReactFlow,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  MarkerType,
} from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { PlanNode, ToolCallNode, MemoryNode, OutcomeNode, AgentMessageNode } from '../nodes/CustomNodes';
import { getLayoutedElements } from '../../utils/layout';
import type { TrajectoryDetailResponse, TrajectoryNode } from '../../types';
import { LayoutGrid, Rows } from 'lucide-react';

const nodeTypes = {
  plan: PlanNode,
  tool_call: ToolCallNode,
  memory_read: MemoryNode,
  memory_write: MemoryNode,
  final_outcome: OutcomeNode,
  reasoning: PlanNode,
  state_update: PlanNode,
  observation: PlanNode,
  agent_message: AgentMessageNode,
  agent_delegate: AgentMessageNode,
};

interface FlowCanvasProps {
  detail: TrajectoryDetailResponse;
  selectedNodeId: string | null;
  onSelectNode: (node: TrajectoryNode) => void;
}

export function FlowCanvas({ detail, selectedNodeId, onSelectNode }: FlowCanvasProps) {
  const [direction, setDirection] = useState<'TB' | 'LR'>('TB');
  const { trajectory, evaluations, failures, root_cause } = detail;

  const failureNodeIds = useMemo(() => new Set(failures.map((f) => f.node_id)), [failures]);
  const rootCauseNodeId = root_cause?.primary_failure_node_id || null;
  const propagationChain = useMemo(() => new Set(root_cause?.propagation_chain || []), [root_cause]);

  // 1. Structural Dagre Layout - only recomputed when graph topology or direction changes
  const baseLayout = useMemo(() => {
    const rawNodes: Node[] = trajectory.nodes.map((node) => ({
      id: node.node_id,
      type: node.event_type in nodeTypes ? node.event_type : 'tool_call',
      position: { x: 0, y: 0 },
      data: { node },
    }));

    const rawEdges: Edge[] = trajectory.edges.map((edge, idx) => ({
      id: `e-${edge.source_node_id}-${edge.target_node_id}-${idx}`,
      source: edge.source_node_id,
      target: edge.target_node_id,
    }));

    return getLayoutedElements(rawNodes, rawEdges, direction);
  }, [trajectory.trace_id, trajectory.nodes, trajectory.edges, direction]);

  // 2. High-speed O(N) presentation mapping - 0ms overhead on node click/selection!
  const layoutedNodes = useMemo(() => {
    return baseLayout.nodes.map((node) => {
      const origNode = node.data.node as TrajectoryNode;
      const isRootCause = origNode.node_id === rootCauseNodeId;
      const isInCascadePath = propagationChain.has(origNode.node_id);
      const isSelected = origNode.node_id === selectedNodeId;
      const hasFailed = failureNodeIds.has(origNode.node_id);
      const evalItem = evaluations.find((e) => e.target_node_id === origNode.node_id);

      return {
        ...node,
        data: {
          node: origNode,
          isRootCause,
          isInCascadePath,
          isSelected,
          hasFailed,
          evaluationScore: evalItem?.score,
        },
      };
    });
  }, [baseLayout.nodes, rootCauseNodeId, propagationChain, selectedNodeId, failureNodeIds, evaluations]);

  const layoutedEdges = useMemo(() => {
    return baseLayout.edges.map((edge) => {
      const isCascadeEdge =
        propagationChain.has(edge.source) && propagationChain.has(edge.target);

      return {
        ...edge,
        animated: isCascadeEdge,
        style: {
          stroke: isCascadeEdge ? 'var(--rose)' : 'var(--edge-stroke)',
          strokeWidth: isCascadeEdge ? 2 : 1.2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isCascadeEdge ? 'var(--rose)' : 'var(--edge-arrow)',
        },
      };
    });
  }, [baseLayout.edges, propagationChain]);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      {/* Direction Switcher Overlay */}
      <div
        style={{
          position: 'absolute',
          top: 12,
          right: 12,
          zIndex: 10,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          padding: 2,
          display: 'flex',
          gap: 3,
          boxShadow: 'var(--card-shadow)',
        }}
      >
        <button
          onClick={() => setDirection('TB')}
          className={`btn ${direction === 'TB' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '3px 8px', fontSize: 10.5 }}
          title="Vertical Hierarchy Layout"
        >
          <Rows size={12} /> Vertical
        </button>
        <button
          onClick={() => setDirection('LR')}
          className={`btn ${direction === 'LR' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '3px 8px', fontSize: 10.5 }}
          title="Horizontal Flow Layout"
        >
          <LayoutGrid size={12} /> Horizontal
        </button>
      </div>

      <ReactFlow
        nodes={layoutedNodes}
        edges={layoutedEdges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => {
          const matched = trajectory.nodes.find((n) => n.node_id === node.id);
          if (matched) onSelectNode(matched);
        }}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(n) => {
            if (n.id === rootCauseNodeId) return 'var(--rose)';
            if (failureNodeIds.has(n.id)) return 'var(--rose)';
            return 'var(--edge-arrow)';
          }}
          maskColor="var(--canvas-mask)"
        />
      </ReactFlow>
    </div>
  );
}
