// web/src/App.tsx - Evalora Phonic Clean Minimalistic Observability & Evaluation Platform

import React, { useEffect, useState, useCallback } from 'react';
import {
  Layers,
  GitCompare,
  Clock,
  RefreshCw,
  Search,
  Sun,
  Moon,
  Home,
  SlidersHorizontal,
} from 'lucide-react';

import type { HealthSummary, Trajectory, TrajectoryDetailResponse, TrajectoryNode } from './types';
import { fetchHealthSummary, fetchTrajectories, fetchTrajectoryDetails } from './services/api';
import { FlowCanvas } from './components/trajectory/FlowCanvas';
import { TimelineWaterfall } from './components/trajectory/TimelineWaterfall';
import { GoldenPathComparator } from './components/comparison/GoldenPathComparator';
import { InspectorDrawer } from './components/trajectory/InspectorDrawer';
import { HealthKPIStrip } from './components/dashboard/HealthKPIStrip';
import { LiveAgentRunner } from './components/studio/LiveAgentRunner';
import { LandingPage } from './components/home/LandingPage';

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
  const [_isLoading, setIsLoading] = useState<boolean>(true);

  // Page Routing State (Homepage vs Studio)
  const [page, setPage] = useState<'home' | 'studio'>(() => {
    if (window.location.hash === '#studio') return 'studio';
    return 'home';
  });

  useEffect(() => {
    const handleHashChange = () => {
      if (window.location.hash === '#studio') setPage('studio');
      else if (window.location.hash === '#home') setPage('home');
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Clean Theme Toggle State
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('evalora_theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('evalora_theme', theme);
  }, [theme]);

  // Stable load health summary and trajectory list (never re-created on trace selection)
  const loadInitialData = useCallback(async () => {
    try {
      const [summary, trajs] = await Promise.all([
        fetchHealthSummary(),
        fetchTrajectories(),
      ]);
      setHealthSummary(summary);
      setTrajectories(trajs);

      // Default select the latest trajectory if none active
      setActiveTraceId((prev) => (!prev && trajs.length > 0 ? trajs[0].trace_id : prev));
    } catch (e) {
      console.error('Error fetching initial data:', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

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

  // Initial load once on mount
  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Auto-sync polling: only when on studio, autoSync enabled, and tab is visible
  useEffect(() => {
    if (!autoSync || page !== 'studio') return;

    const interval = setInterval(() => {
      if (document.hidden) return; // Zero network/CPU consumption when tab is hidden
      fetchHealthSummary().then(setHealthSummary).catch(() => {});
      fetchTrajectories().then(setTrajectories).catch(() => {});
    }, 5000);

    return () => clearInterval(interval);
  }, [autoSync, page]);

  // Real-Time WebSocket Streaming Listener
  const [isWsConnected, setIsWsConnected] = useState<boolean>(false);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connectWebSocket = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host || 'localhost:8000';
        ws = new WebSocket(`${protocol}//${host}/ws/live-traces`);

        ws.onopen = () => {
          setIsWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'TRACE_INGESTED' || data.type === 'EVALUATION_COMPLETED') {
              fetchHealthSummary().then(setHealthSummary).catch(() => {});
              fetchTrajectories().then(setTrajectories).catch(() => {});
              if (activeTraceId && data.trace_id === activeTraceId) {
                fetchTrajectoryDetails(activeTraceId).then(setActiveDetail).catch(() => {});
              }
            }
          } catch (e) {
            console.error('WS message parse error:', e);
          }
        };

        ws.onclose = () => {
          setIsWsConnected(false);
          reconnectTimeout = setTimeout(connectWebSocket, 4000);
        };

        ws.onerror = () => {
          setIsWsConnected(false);
          ws?.close();
        };
      } catch (err) {
        setIsWsConnected(false);
        reconnectTimeout = setTimeout(connectWebSocket, 5000);
      }
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, [activeTraceId]);

  // High-performance deferred search & memoized filtering
  const deferredSearch = React.useDeferredValue(searchQuery);

  const filteredTrajectories = React.useMemo(() => {
    const q = deferredSearch.toLowerCase().trim();
    return trajectories.filter((t) => {
      const matchesSearch =
        !q ||
        t.trace_id.toLowerCase().includes(q) ||
        (t.goal || '').toLowerCase().includes(q) ||
        t.agent_id.toLowerCase().includes(q);

      if (!matchesSearch) return false;
      if (statusFilter === 'failed') return t.is_success === false;
      if (statusFilter === 'passed') return t.is_success !== false;
      return true;
    });
  }, [trajectories, deferredSearch, statusFilter]);

  // Render Homepage if active
  if (page === 'home') {
    return (
      <LandingPage
        theme={theme}
        onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        onLaunchStudio={() => {
          setPage('studio');
          window.location.hash = '#studio';
        }}
        healthSummary={healthSummary}
      />
    );
  }

  // Render Full Observability Studio
  return (
    <div className="app-container">
      {/* 1. Topbar */}
      <header className="topbar">
        <div className="brand-section">
          {/* Page Switcher Pill */}
          <div style={{ display: 'flex', background: 'var(--bg-canvas)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: 2 }}>
            <button
              onClick={() => {
                setPage('home');
                window.location.hash = '#home';
              }}
              className="view-btn"
              style={{ padding: '3px 8px', fontSize: 11 }}
              title="Return to 3D Homepage Overview"
            >
              <Home size={12} /> Overview
            </button>
            <button
              className="view-btn active"
              style={{ padding: '3px 8px', fontSize: 11 }}
            >
              <SlidersHorizontal size={12} /> Studio
            </button>
          </div>

          <div className="brand-badge">EVALORA</div>
          <div>
            <div className="brand-title">Agent Observability & Causal Evaluation</div>
            <div className="brand-subtitle">OTLP Spans • Trajectory DAGs • Causal Root-Cause Engine</div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* WebSocket Status Indicator */}
          <span
            className="badge"
            style={{
              fontSize: 9.5,
              background: isWsConnected ? 'rgba(34, 197, 94, 0.15)' : 'rgba(234, 179, 8, 0.15)',
              color: isWsConnected ? 'var(--color-green, #22c55e)' : 'var(--color-yellow, #eab308)',
              border: `1px solid ${isWsConnected ? 'rgba(34, 197, 94, 0.3)' : 'rgba(234, 179, 8, 0.3)'}`,
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
            title={isWsConnected ? 'Real-Time WebSocket Stream Connected' : 'Polling HTTP Fallback Active'}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: isWsConnected ? '#22c55e' : '#eab308',
                display: 'inline-block',
                boxShadow: isWsConnected ? '0 0 6px #22c55e' : 'none',
              }}
            />
            {isWsConnected ? 'WS STREAMING' : 'POLLING'}
          </span>

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
              <span style={{ color: 'var(--text-muted)' }}>AUTO-SYNC PAUSED</span>
            )}
          </button>

          {/* Theme Toggle Button */}
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="btn btn-secondary theme-toggle-btn"
            title={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
          >
            {theme === 'dark' ? <Sun size={12} /> : <Moon size={12} />}
            <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>

          {/* OpenClaw Plugin Badge */}
          <span className="badge badge-purple" style={{ fontSize: 9.5 }}>
            OpenClaw Plugin
          </span>

          {/* Refresh Button */}
          <button
            onClick={loadInitialData}
            className="btn btn-secondary"
            title="Refresh fleet telemetry"
          >
            <RefreshCw size={12} />
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
            <div style={{ display: 'flex', gap: 3 }}>
              <button
                onClick={() => setStatusFilter('all')}
                className={`btn ${statusFilter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '2px 6px', fontSize: 9.5 }}
              >
                All
              </button>
              <button
                onClick={() => setStatusFilter('failed')}
                className={`btn ${statusFilter === 'failed' ? 'btn-danger' : 'btn-secondary'}`}
                style={{ padding: '2px 6px', fontSize: 9.5 }}
              >
                Failed
              </button>
              <button
                onClick={() => setStatusFilter('passed')}
                className={`btn ${statusFilter === 'passed' ? 'btn-success' : 'btn-secondary'}`}
                style={{ padding: '2px 6px', fontSize: 9.5 }}
              >
                Passed
              </button>
            </div>
          </div>

          {/* Search Box */}
          <div style={{ padding: '7px 10px', borderBottom: '1px solid var(--border-subtle)' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '4px 8px',
              }}
            >
              <Search size={12} color="var(--text-muted)" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter by trace ID, agent, or goal..."
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-primary)',
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
              <div style={{ padding: 18, textAlign: 'center', color: 'var(--text-muted)', fontSize: 11.5 }}>
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
                <span style={{ fontSize: 10.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Active Trace:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
                  {activeTraceId}
                </span>
                {activeDetail?.root_cause && (
                  <span className="badge badge-rose" style={{ fontSize: 9.5 }}>
                    Root Cause: {activeDetail.root_cause.primary_category}
                  </span>
                )}
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', marginTop: 2 }}>
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
                  <Layers size={12} /> Causal Flow DAG
                </button>
                <button
                  onClick={() => setActiveView('waterfall')}
                  className={`view-btn ${activeView === 'waterfall' ? 'active' : ''}`}
                  title="Gantt Duration Waterfall View"
                >
                  <Clock size={12} /> Span Waterfall
                </button>
                <button
                  onClick={() => setActiveView('comparator')}
                  className={`view-btn ${activeView === 'comparator' ? 'active' : ''}`}
                  title="Golden Path Sequence Comparator"
                >
                  <GitCompare size={12} /> Golden Path
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
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
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
