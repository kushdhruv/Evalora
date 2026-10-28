// web/src/components/home/LandingPage.tsx - Modern 3D Rendered Homepage for Evalora

import React, { useState } from 'react';
import {
  Sparkles,
  ArrowRight,
  GitBranch,
  ShieldCheck,
  Zap,
  Activity,
  Layers,
  Brain,
  GitCompare,
  Terminal,
  ExternalLink,
  Sun,
  Moon,
  CheckCircle2,
  Bug,
  Database,
  ChevronRight,
  Code2,
} from 'lucide-react';
import { CausalCanvas3D } from './CausalCanvas3D';
import type { HealthSummary } from '../../types';
import { runLiveAgent } from '../../services/api';

interface LandingPageProps {
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  onLaunchStudio: () => void;
  healthSummary: HealthSummary | null;
}

export function LandingPage({
  theme,
  onToggleTheme,
  onLaunchStudio,
  healthSummary,
}: LandingPageProps) {
  const [simulationPrompt, setSimulationPrompt] = useState<string>(
    'Check overdue balance for customer acct_982 and email the summary to billing.'
  );
  const [simRunning, setSimRunning] = useState<boolean>(false);
  const [simResult, setSimResult] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<'cli' | 'python' | 'plugin'>('cli');

  const handleRunSim = async (mode: 'flawed_v1' | 'fixed_v2') => {
    setSimRunning(true);
    setSimResult(null);
    try {
      const res = await runLiveAgent(mode, simulationPrompt);
      setSimResult(res);
    } catch (e: any) {
      console.error('Simulation error:', e);
    } finally {
      setSimRunning(false);
    }
  };

  const successRate = healthSummary ? (healthSummary.success_rate * 100).toFixed(0) : '94';
  const totalTraces = healthSummary ? healthSummary.total_trajectories : 18;
  const avgLatency = healthSummary ? healthSummary.avg_latency_ms.toFixed(0) : '312';

  return (
    <div className="landing-wrapper">
      {/* 1. Navigation Bar */}
      <nav className="landing-nav">
        <div className="landing-nav-content">
          <div className="brand-section">
            <div className="brand-badge">EVALORA</div>
            <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--text-primary)' }}>
              Evalora
            </span>
            <span className="badge badge-muted" style={{ fontSize: 9.5 }}>
              v1.0.0
            </span>
          </div>

          <div className="landing-nav-links">
            <a href="#features" className="nav-link">Features</a>
            <a href="#architecture" className="nav-link">Architecture</a>
            <a href="#demo" className="nav-link">Live Sandbox</a>
            <a href="#quickstart" className="nav-link">Quickstart</a>
            <a
              href="https://github.com/kushdhruv/Evalora"
              target="_blank"
              rel="noreferrer"
              className="nav-link"
              style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
            >
              GitHub <ExternalLink size={11} />
            </a>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Theme Switcher */}
            <button
              onClick={onToggleTheme}
              className="btn btn-secondary theme-toggle-btn"
              title={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
            >
              {theme === 'dark' ? <Sun size={12} /> : <Moon size={12} />}
              <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
            </button>

            {/* Launch Studio CTA */}
            <button onClick={onLaunchStudio} className="btn btn-primary" style={{ padding: '6px 14px' }}>
              Launch Studio <ArrowRight size={13} />
            </button>
          </div>
        </div>
      </nav>

      {/* 2. Hero Section with Interactive 3D Canvas */}
      <section className="hero-section">
        {/* Three.js 3D Interactive WebGL Causal Constellation */}
        <CausalCanvas3D theme={theme} />

        {/* Ambient Soothing Glow Layer */}
        <div className="hero-ambient-glow" />

        <div className="hero-content">
          <div className="hero-badge-pill">
            <Sparkles size={12} color="var(--emerald-text)" />
            <span>FRAMEWORK-AGNOSTIC AGENT OBSERVABILITY & EVALUATION</span>
          </div>

          <h1 className="hero-title">
            Observability and Causal Diagnostics for AI Agents
          </h1>

          <p className="hero-subtitle">
            Reconstruct asynchronous agent telemetry into causal trajectory DAGs. Stop blaming terminal
            symptoms—isolate root-cause failure cascades and enforce continuous integration regression gates with mathematical precision.
          </p>

          <div className="hero-actions">
            <button onClick={onLaunchStudio} className="btn btn-primary hero-btn-lg">
              Open Observability Studio <ArrowRight size={14} />
            </button>
            <a
              href="#demo"
              className="btn btn-secondary hero-btn-lg"
              style={{ textDecoration: 'none' }}
            >
              <Zap size={14} color="var(--amber-text)" /> Try Live Sandbox
            </a>
            <a
              href="https://github.com/kushdhruv/Evalora"
              target="_blank"
              rel="noreferrer"
              className="btn btn-secondary hero-btn-lg"
              style={{ textDecoration: 'none' }}
            >
              <GitBranch size={14} /> Star on GitHub
            </a>
          </div>

          {/* Value Badges */}
          <div className="hero-pills-row">
            <span className="hero-pill">✓ OTLP 1.1 Ingestion</span>
            <span className="hero-pill">✓ Causal Reverse Blame</span>
            <span className="hero-pill">✓ In-Situ Long-Horizon Memory</span>
            <span className="hero-pill">✓ Zero-Cost Offline Judge</span>
            <span className="hero-pill">✓ CI Regression Gate CLI</span>
          </div>
        </div>
      </section>

      {/* 3. Live Fleet Health Telemetry Strip */}
      <section className="fleet-strip-section">
        <div className="landing-container">
          <div className="fleet-kpi-bar">
            <div className="fleet-kpi-item">
              <span className="fleet-kpi-label">Analyzed Traces</span>
              <span className="fleet-kpi-value">{totalTraces}</span>
              <span className="fleet-kpi-sub">Continuous fleet telemetry</span>
            </div>
            <div className="fleet-kpi-divider" />
            <div className="fleet-kpi-item">
              <span className="fleet-kpi-label">Fleet Success Rate</span>
              <span className="fleet-kpi-value" style={{ color: 'var(--emerald-text)' }}>
                {successRate}%
              </span>
              <span className="fleet-kpi-sub">Target &gt; 85% passed</span>
            </div>
            <div className="fleet-kpi-divider" />
            <div className="fleet-kpi-item">
              <span className="fleet-kpi-label">Mean Latency</span>
              <span className="fleet-kpi-value">{avgLatency} ms</span>
              <span className="fleet-kpi-sub">Sub-millisecond span timing</span>
            </div>
            <div className="fleet-kpi-divider" />
            <div className="fleet-kpi-item">
              <span className="fleet-kpi-label">Local Judge Cost</span>
              <span className="fleet-kpi-value" style={{ color: 'var(--emerald-text)' }}>
                $0.00
              </span>
              <span className="fleet-kpi-sub">100% Free local evaluation</span>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Core Architectural Pillars */}
      <section id="features" className="section-padding">
        <div className="landing-container">
          <div className="section-header">
            <span className="section-tag">ENGINEERING PILLARS</span>
            <h2 className="section-title">Designed for Real-World Agent Reliability</h2>
            <p className="section-desc">
              Conventional APMs treat LLMs like black boxes. Evalora extracts step semantics, tracks state dependencies, and pinpoints where multi-step reasoning collapses.
            </p>
          </div>

          <div className="pillars-grid">
            {/* Pillar 1 */}
            <div className="pillar-card">
              <div className="pillar-icon-box" style={{ color: 'var(--rose-text)', background: 'var(--rose-bg)', borderColor: 'var(--rose-border)' }}>
                <Layers size={20} />
              </div>
              <h3 className="pillar-title">Causal Trajectory DAG & Reverse Blame</h3>
              <p className="pillar-text">
                Instead of falsely blaming the final failed outcome node, our NetworkX causal analyzer computes reverse topological reachability to isolate the earliest faulty tool call or hallucinated schema that initiated the failure cascade.
              </p>
              <div className="pillar-footer">
                <span className="badge badge-rose">Root-Cause Isolation</span>
                <span className="badge badge-muted">Topological Reach</span>
              </div>
            </div>

            {/* Pillar 2 */}
            <div className="pillar-card">
              <div className="pillar-icon-box" style={{ color: 'var(--purple-text)', background: 'var(--purple-bg)', borderColor: 'var(--purple-border)' }}>
                <Brain size={20} />
              </div>
              <h3 className="pillar-title">In-Situ Long-Horizon Memory Auditor</h3>
              <p className="pillar-text">
                Inspired by modern agent evaluations (AMA-Bench). Audits production agent memory operations for fact staleness, retrieval relevance (cosine similarity), and context retention over extended interactions without synthetic probe injections.
              </p>
              <div className="pillar-footer">
                <span className="badge badge-purple">AMA-Bench Pattern</span>
                <span className="badge badge-muted">Fact Retention</span>
              </div>
            </div>

            {/* Pillar 3 */}
            <div className="pillar-card">
              <div className="pillar-icon-box" style={{ color: 'var(--blue-text)', background: 'var(--blue-bg)', borderColor: 'var(--blue-border)' }}>
                <GitCompare size={20} />
              </div>
              <h3 className="pillar-title">Side-by-Side Golden Path Benchmark</h3>
              <p className="pillar-text">
                Compares actual runtime tool invocations against reference golden paths using Levenshtein sequence alignment. Instantly flags omitted verification steps, infinite loops, and hallucinated API invocations.
              </p>
              <div className="pillar-footer">
                <span className="badge badge-blue">Levenshtein Alignment</span>
                <span className="badge badge-muted">Sequence Fidelity</span>
              </div>
            </div>

            {/* Pillar 4 */}
            <div className="pillar-card">
              <div className="pillar-icon-box" style={{ color: 'var(--emerald-text)', background: 'var(--emerald-bg)', borderColor: 'var(--emerald-border)' }}>
                <ShieldCheck size={20} />
              </div>
              <h3 className="pillar-title">CI/CD Regression Quality Gate CLI</h3>
              <p className="pillar-text">
                Enforce automated PR quality gates via `aieval gate`. Fails the continuous integration pipeline if agent success scores drop or if execution latency regresses beyond tolerance thresholds, preventing buggy prompt changes from shipping.
              </p>
              <div className="pillar-footer">
                <span className="badge badge-emerald">Exit Code 0/1</span>
                <span className="badge badge-muted">PR Quality Gate</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Interactive Live Sandbox */}
      <section id="demo" className="section-padding" style={{ background: 'var(--bg-surface)', borderTop: '1px solid var(--border-subtle)', borderBottom: '1px solid var(--border-subtle)' }}>
        <div className="landing-container">
          <div className="section-header">
            <span className="section-tag">INTERACTIVE SANDBOX</span>
            <h2 className="section-title">Test Real Agent Telemetry Live</h2>
            <p className="section-desc">
              Execute real autonomous agent workflows against a local SQLite database and watch Evalora's causal analyzer evaluate the execution trajectory.
            </p>
          </div>

          <div className="sandbox-card">
            <div className="sandbox-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Database size={15} color="var(--text-primary)" />
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                  Local Runtime Agent Execution
                </span>
              </div>
              <span className="badge badge-emerald">Zero-Cost Offline Runtime</span>
            </div>

            <div style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Target Autonomous Goal Prompt:
                </label>
                <input
                  type="text"
                  value={simulationPrompt}
                  onChange={(e) => setSimulationPrompt(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 12px',
                    color: 'var(--text-primary)',
                    fontSize: 12,
                    fontFamily: 'inherit',
                    marginTop: 6,
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button
                  onClick={() => handleRunSim('flawed_v1')}
                  disabled={simRunning}
                  className="btn btn-danger"
                  style={{ padding: '8px 14px' }}
                >
                  <Bug size={13} /> Run Flawed Agent (v1 - SQL Schema Bug)
                </button>
                <button
                  onClick={() => handleRunSim('fixed_v2')}
                  disabled={simRunning}
                  className="btn btn-success"
                  style={{ padding: '8px 14px' }}
                >
                  <CheckCircle2 size={13} /> Run Fixed Agent (v2 - Self Correcting)
                </button>
                <button
                  onClick={onLaunchStudio}
                  className="btn btn-secondary"
                  style={{ marginLeft: 'auto', padding: '8px 14px' }}
                >
                  Inspect in Visual Studio <ChevronRight size={13} />
                </button>
              </div>

              {simRunning && (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '12px 0' }}>
                  Executing autonomous agent workflow against local SQLite database...
                </div>
              )}

              {simResult && (
                <div className="sandbox-result-box">
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="badge badge-muted">Trace: {simResult.trace_id}</span>
                      <span className={`badge ${simResult.passed ? 'badge-emerald' : 'badge-rose'}`}>
                        {simResult.passed ? 'PASSED (100%)' : 'FAULT DETECTED'}
                      </span>
                    </div>
                    <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      Nodes: {simResult.nodes_count}
                    </span>
                  </div>

                  {simResult.root_cause ? (
                    <div style={{ fontSize: 12, color: 'var(--rose-text)', marginTop: 4 }}>
                      <strong>🚨 Root Cause Identified:</strong> {simResult.root_cause.explanation}
                    </div>
                  ) : (
                    <div style={{ fontSize: 12, color: 'var(--emerald-text)', marginTop: 4 }}>
                      <strong>✓ Healthy Execution:</strong> Agent completed all sub-goals and verified database schema correctly.
                    </div>
                  )}

                  <div style={{ marginTop: 12 }}>
                    <button onClick={onLaunchStudio} className="btn btn-primary" style={{ fontSize: 11 }}>
                      View Full Causal DAG in Studio <ArrowRight size={12} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* 6. Quickstart / CLI Integration */}
      <section id="quickstart" className="section-padding">
        <div className="landing-container">
          <div className="section-header">
            <span className="section-tag">DEVELOPER EXPERIENCE</span>
            <h2 className="section-title">Get Started in Under Two Minutes</h2>
            <p className="section-desc">
              Evalora is 100% self-hosted, lightweight, and framework-agnostic. Run locally with zero external cloud dependencies.
            </p>
          </div>

          <div className="code-tabs-card">
            <div className="code-tabs-header">
              <div style={{ display: 'flex', gap: 6 }}>
                <button
                  onClick={() => setActiveTab('cli')}
                  className={`btn ${activeTab === 'cli' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ fontSize: 11 }}
                >
                  <Terminal size={12} /> CI Gate CLI
                </button>
                <button
                  onClick={() => setActiveTab('python')}
                  className={`btn ${activeTab === 'python' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ fontSize: 11 }}
                >
                  <Code2 size={12} /> Local Quickstart
                </button>
                <button
                  onClick={() => setActiveTab('plugin')}
                  className={`btn ${activeTab === 'plugin' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ fontSize: 11 }}
                >
                  <Zap size={12} /> OpenClaw Plugin
                </button>
              </div>
            </div>

            <pre className="code-block" style={{ margin: 0, borderRadius: '0 0 var(--radius-md) var(--radius-md)', padding: 18 }}>
              {activeTab === 'cli' &&
`# Run Automated CI/CD Regression Quality Gate on Pull Request
python -m cli.main gate \\
  --experiment prod_release_v2 \\
  --threshold 0.85 \\
  --max-latency 4500.0

# Exit code 0 on Pass | Exit code 1 on Regression (blocks PR)`}

              {activeTab === 'python' &&
`# 1. Clone repository
git clone https://github.com/kushdhruv/Evalora.git
cd Evalora

# 2. Install dependencies (zero cloud cost required)
pip install -r requirements.txt

# 3. Launch Observability Server & Embedded Studio
python -m uvicorn server.main:app --port 8000

# Open http://127.0.0.1:8000/ to view the interactive studio`}

              {activeTab === 'plugin' &&
`// OpenClaw Native Plugin Integration (plugins/openclaw-aieval)
import { createAiEvalPlugin } from 'openclaw-aieval';

const plugin = createAiEvalPlugin({
  collectorUrl: 'http://127.0.0.1:8000/v1/traces',
  autoAuditMemory: true,
  enableSelfCorrection: true
});

agent.registerPlugin(plugin);`}
            </pre>
          </div>
        </div>
      </section>

      {/* 7. Footer */}
      <footer className="landing-footer">
        <div className="landing-container">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div className="brand-badge" style={{ fontSize: 11 }}>EVALORA</div>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Autonomous Agent Evaluation & Causal Observability Platform • MIT License
              </span>
            </div>

            <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
              <a href="https://github.com/kushdhruv/Evalora" target="_blank" rel="noreferrer" className="nav-link">
                GitHub Repository
              </a>
              <button onClick={onLaunchStudio} className="nav-link" style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                Open Studio
              </button>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
