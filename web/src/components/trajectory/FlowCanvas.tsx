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

import { PlanNode, ToolCallNode, MemoryNode, OutcomeNode } from '../nodes/CustomNodes';
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

  const { layoutedNodes, layoutedEdges } = useMemo(() => {
    const rawNodes: Node[] = trajectory.nodes.map((node) => {
      const isRootCause = node.node_id === rootCauseNodeId;
      const isInCascadePath = propagationChain.has(node.node_id);
      const isSelected = node.node_id === selectedNodeId;
      const hasFailed = failureNodeIds.has(node.node_id);
      const evalItem = evaluations.find((e) => e.target_node_id === node.node_id);

      return {
        id: node.node_id,
        type: node.event_type in nodeTypes ? node.event_type : 'tool_call',
        position: { x: 0, y: 0 },
        data: {
          node,
          isRootCause,
          isInCascadePath,
          isSelected,
          hasFailed,
          evaluationScore: evalItem?.score,
        },
      };
    });

    const rawEdges: Edge[] = trajectory.edges.map((edge, idx) => {
      const isCascadeEdge =
        propagationChain.has(edge.source_node_id) && propagationChain.has(edge.target_node_id);

      return {
        id: `e-${edge.source_node_id}-${edge.target_node_id}-${idx}`,
        source: edge.source_node_id,
        target: edge.target_node_id,
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

    const { nodes: lNodes, edges: lEdges } = getLayoutedElements(rawNodes, rawEdges, direction);
    return { layoutedNodes: lNodes, layoutedEdges: lEdges };
  }, [trajectory, evaluations, failureNodeIds, rootCauseNodeId, propagationChain, selectedNodeId, direction]);

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
