// web/src/App.tsx - Evalora Production-Grade Agent Observability & Evaluation Platform

import React, { useEffect, useState, useCallback } from 'react';
import {
  Activity,
  Layers,
  GitCompare,
  Clock,
  Filter,
  RefreshCw,
  Search,
  ExternalLink,
  ShieldAlert,
  SlidersHorizontal,
  ChevronRight,
} from 'lucide-react';

import { HealthSummary, Trajectory, TrajectoryDetailResponse, TrajectoryNode } from './types';
import { fetchHealthSummary, fetchTrajectories, fetchTrajectoryDetails } from './services/api';
import { FlowCanvas } from './components/trajectory/FlowCanvas';
import { TimelineWaterfall } from './components/trajectory/TimelineWaterfall';
import { GoldenPathComparator } from './components/comparison/GoldenPathComparator';
import { InspectorDrawer } from './components/trajectory/InspectorDrawer';
import { HealthKPIStrip } from './components/dashboard/HealthKPIStrip';
import { LiveAgentRunner } from './components/studio/LiveAgentRunner';

export function App() {
  const [trajectories, setTrajectories] = useState<Trajectory[]>([]);
  const [activeTraceId, setActiveTraceId] = useState<string | null>(null);
  const [activeDetail, setActiveDetail] = useState<TrajectoryDetailResponse | null>(null);
  const [healthSummary, setHealthSummary] = useState<HealthSummary | null>(null);
  const [selectedNode, setSelectedNode] = useState<TrajectoryNode | null>(null);
  const [activeView, setActiveView] = useState<'flow' | 'waterfall' | 'comparator'>('flow');
  
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'failed' | 'passed'>('all');
  const [autoSync, setAutoSync] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Load health summary and trajectory list
  const loadInitialData = useCallback(async () => {
    try {
      const [summary, trajs] = await Promise.all([
        fetchHealthSummary(),
        fetchTrajectories(),
      ]);
      setHealthSummary(summary);
      setTrajectories(trajs);

      // Default select the latest trajectory if none active
      if (trajs.length > 0 && !activeTraceId) {
        setActiveTraceId(trajs[0].trace_id);
      }
    } catch (e) {
      console.error('Error fetching initial data:', e);
    } finally {
      setIsLoading(false);
    }
  }, [activeTraceId]);

  // Load details whenever activeTraceId changes
  useEffect(() => {
    if (!activeTraceId) return;
    let isMounted = true;
    fetchTrajectoryDetails(activeTraceId)
      .then((detail) => {
        if (isMounted) {
          setActiveDetail(detail);
          // Auto select root cause node if available, else first node
          if (detail.root_cause) {
            const rootNode = detail.trajectory.nodes.find(
              (n) => n.node_id === detail.root_cause?.primary_failure_node_id
            );
            if (rootNode) setSelectedNode(rootNode);
          } else if (detail.trajectory.nodes.length > 0) {
            setSelectedNode(detail.trajectory.nodes[0]);
          }
        }
      })
      .catch((err) => console.error('Error fetching trajectory detail:', err));

    return () => {
      isMounted = false;
    };
  }, [activeTraceId]);

  // Initial load
  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Auto-sync polling every 3 seconds
  useEffect(() => {
    if (!autoSync) return;
    const interval = setInterval(() => {
      fetchHealthSummary().then(setHealthSummary).catch(() => {});
      fetchTrajectories().then(setTrajectories).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [autoSync]);

  // Filter trajectories
  const filteredTrajectories = trajectories.filter((t) => {
    const matchesSearch =
      t.trace_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.goal || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.agent_id.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;
    if (statusFilter === 'failed') return t.is_success === false;
    if (statusFilter === 'passed') return t.is_success !== false;
    return true;
  });

  return (
    <div className="app-container">
      {/* 1. Topbar */}
      <header className="topbar">
        <div className="brand-section">
          <div className="brand-badge">EVALORA</div>
          <div>
            <div className="brand-title">Agent Observability & Causal Evaluation</div>
            <div className="brand-subtitle">OTLP Spans • Trajectory DAGs • Causal Root-Cause Engine</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Live Auto-Sync Toggle */}
          <button
            onClick={() => setAutoSync(!autoSync)}
            className="btn btn-secondary"
            style={{ fontSize: 11 }}
            title={autoSync ? 'Live auto-refresh enabled' : 'Click to enable auto-refresh'}
          >
            {autoSync ? (
              <span className="live-beacon">
                <span className="beacon-dot" /> LIVE AUTO-SYNC
              </span>
            ) : (
              <span style={{ color: '#64748b' }}>AUTO-SYNC PAUSED</span>
            )}
          </button>

          {/* OpenClaw Plugin Badge */}
          <span className="badge badge-purple" style={{ fontSize: 10 }}>
            OpenClaw Plugin Active
          </span>

          {/* Refresh Button */}
          <button
            onClick={loadInitialData}
            className="btn btn-secondary"
            title="Refresh fleet telemetry"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </header>

      {/* 2. Live Agent Studio Strip */}
      <LiveAgentRunner
        onRunComplete={(newTraceId) => {
          setActiveTraceId(newTraceId);
          loadInitialData();
        }}
      />

      {/* 3. Fleet Health KPI Metrics Strip */}
      <HealthKPIStrip summary={healthSummary} />

      {/* 4. Main Observability Workspace */}
      <div className="main-content">
        {/* Left Sidebar: Trajectory List */}
        <aside className="sidebar-panel">
          <div className="sidebar-header">
            <span className="sidebar-title">
              Trajectories ({filteredTrajectories.length})
            </span>
            <div style={{ display: 'flex', gap: 4 }}>
              <button
                onClick={() => setStatusFilter('all')}
                className={`btn ${statusFilter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '2px 6px', fontSize: 10 }}
              >
                All
              </button>
              <button
                onClick={() => setStatusFilter('failed')}
                className={`btn ${statusFilter === 'failed' ? 'btn-danger' : 'btn-secondary'}`}
                style={{ padding: '2px 6px', fontSize: 10 }}
              >
                Failed
              </button>
              <button
                onClick={() => setStatusFilter('passed')}
                className={`btn ${statusFilter === 'passed' ? 'btn-success' : 'btn-secondary'}`}
                style={{ padding: '2px 6px', fontSize: 10 }}
              >
                Passed
              </button>
            </div>
          </div>

          {/* Search Box */}
          <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-subtle)' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                background: 'var(--bg-canvas)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 4,
                padding: '4px 8px',
              }}
            >
              <Search size={12} color="#64748b" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter by trace ID, agent, or goal..."
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#fff',
                  fontSize: 11,
                  outline: 'none',
                  width: '100%',
                }}
              />
            </div>
          </div>

          {/* Trajectory Cards */}
          <div className="sidebar-list">
            {filteredTrajectories.length === 0 ? (
              <div style={{ padding: 18, textAlign: 'center', color: '#64748b', fontSize: 12 }}>
                No trajectories match filter.
              </div>
            ) : (
              filteredTrajectories.map((t) => {
                const isActive = t.trace_id === activeTraceId;
                const isFailed = t.is_success === false;

                return (
                  <div
                    key={t.trace_id}
                    onClick={() => setActiveTraceId(t.trace_id)}
                    className={`trajectory-card ${isActive ? 'active' : ''}`}
                  >
                    <div className="traj-card-top">
                      <span className="traj-trace-id">{t.trace_id}</span>
                      <span className={`badge ${isFailed ? 'badge-rose' : 'badge-emerald'}`}>
                        {isFailed ? 'FAILED' : 'SUCCESS'}
                      </span>
                    </div>

                    <div className="traj-goal">
                      {t.goal || t.agent_id}
                    </div>

                    <div className="traj-meta-row">
                      <span>{t.nodes?.length || 0} nodes</span>
                      <span>•</span>
                      <span>{(t.total_latency_ms || 0).toFixed(0)} ms</span>
                      <span>•</span>
                      <span>{t.agent_version || '1.0'}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* Center Canvas */}
        <main className="workspace-panel">
          {/* Workspace Top Header & Dual-View Switcher */}
          <div className="workspace-header">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 11, color: '#64748b' }}>Active Trace:</span>
                <span style={{ fontFamily: 'monospace', fontSize: 12, fontWeight: 700, color: '#60a5fa' }}>
                  {activeTraceId}
                </span>
                {activeDetail?.root_cause && (
                  <span className="badge badge-rose" style={{ fontSize: 10 }}>
                    Root Cause: {activeDetail.root_cause.primary_category}
                  </span>
                )}
              </div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
                {activeDetail?.trajectory.goal || 'Autonomous Goal Execution'}
              </div>
            </div>

            {/* Dual-View Mode Switcher */}
            <div className="workspace-actions">
              <div className="view-switcher">
                <button
                  onClick={() => setActiveView('flow')}
                  className={`view-btn ${activeView === 'flow' ? 'active' : ''}`}
                  title="Interactive Causal DAG View"
                >
                  <Layers size={13} /> Causal Flow DAG
                </button>
                <button
                  onClick={() => setActiveView('waterfall')}
                  className={`view-btn ${activeView === 'waterfall' ? 'active' : ''}`}
                  title="Gantt Duration Waterfall View"
                >
                  <Clock size={13} /> Span Waterfall
                </button>
                <button
                  onClick={() => setActiveView('comparator')}
                  className={`view-btn ${activeView === 'comparator' ? 'active' : ''}`}
                  title="Golden Path Sequence Comparator"
                >
                  <GitCompare size={13} /> Golden Path
                </button>
              </div>
            </div>
          </div>

          {/* Canvas Render Area */}
          <div className="canvas-container">
            {activeDetail ? (
              activeView === 'flow' ? (
                <FlowCanvas
                  detail={activeDetail}
                  selectedNodeId={selectedNode?.node_id || null}
                  onSelectNode={(node) => setSelectedNode(node)}
                />
              ) : activeView === 'waterfall' ? (
                <TimelineWaterfall
                  detail={activeDetail}
                  selectedNodeId={selectedNode?.node_id || null}
                  onSelectNode={(node) => setSelectedNode(node)}
                />
              ) : (
                <GoldenPathComparator detail={activeDetail} />
              )
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#64748b' }}>
                Select a trajectory to inspect.
              </div>
            )}
          </div>
        </main>

        {/* Right Drawer: Deep Node & Causal Blame Inspector */}
        {selectedNode && activeDetail && (
          <InspectorDrawer
            node={selectedNode}
            evaluations={activeDetail.evaluations}
            failures={activeDetail.failures}
            rootCause={activeDetail.root_cause}
            traceId={activeDetail.trajectory.trace_id}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </div>
    </div>
  );
}

export default App;
