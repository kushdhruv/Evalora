// web/src/components/dashboard/HealthKPIStrip.tsx - Clean Minimalist Fleet Health KPI Metrics Strip

import React from 'react';
import { Clock, ShieldCheck, DollarSign, Wrench, AlertTriangle } from 'lucide-react';
import type { HealthSummary } from '../../types';

interface HealthKPIStripProps {
  summary: HealthSummary | null;
}

export function HealthKPIStrip({ summary }: HealthKPIStripProps) {
  if (!summary) return null;

  const successPct = (summary.success_rate * 100).toFixed(0);
  const failureEntries = Object.entries(summary.failure_category_counts || {});
  const toolEntries = Object.entries(summary.tool_usage_counts || {});

  return (
    <div className="kpi-strip">
      {/* 1. Fleet Success Rate */}
      <div className="kpi-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="kpi-label">Fleet Success</span>
          <ShieldCheck size={13} color={Number(successPct) >= 80 ? 'var(--emerald-text)' : 'var(--amber-text)'} />
        </div>
        <div className="kpi-value" style={{ color: Number(successPct) >= 80 ? 'var(--emerald-text)' : 'var(--amber-text)' }}>
          {successPct}%
        </div>
        <span className="kpi-subtext">Across {summary.total_trajectories} recorded traces</span>
      </div>

      {/* 2. Latency (Avg & P95) */}
      <div className="kpi-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="kpi-label">Avg / p95 Latency</span>
          <Clock size={13} color="var(--text-muted)" />
        </div>
        <div className="kpi-value">
          {summary.avg_latency_ms.toFixed(1)} ms
        </div>
        <span className="kpi-subtext">
          {summary.p95_latency_ms ? `p95: ${summary.p95_latency_ms.toFixed(0)}ms` : 'Target < 5000ms'}
        </span>
      </div>

      {/* 3. Total Cost / Tokens */}
      <div className="kpi-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="kpi-label">Fleet Spend</span>
          <DollarSign size={13} color="var(--text-muted)" />
        </div>
        <div className="kpi-value">
          ${summary.total_cost_usd.toFixed(4)}
        </div>
        <span className="kpi-subtext">Zero-cost local runtime judge</span>
      </div>

      {/* 4. Failure Categorization */}
      <div className="kpi-card" style={{ gridColumn: 'span 2' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 2 }}>
          <span className="kpi-label">Failure Breakdown</span>
          <AlertTriangle size={12} color="var(--rose-text)" />
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 4 }}>
          {failureEntries.length === 0 ? (
            <span style={{ fontSize: 11, color: 'var(--emerald-text)', fontWeight: 500 }}>Zero failures detected across fleet</span>
          ) : (
            failureEntries.map(([cat, count]) => (
              <span key={cat} className="badge badge-rose" style={{ fontSize: 9.5 }}>
                {cat}: {count}
              </span>
            ))
          )}
        </div>
      </div>

      {/* 5. Tool Call Activity */}
      <div className="kpi-card" style={{ gridColumn: 'span 2' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 2 }}>
          <span className="kpi-label">Active Tool Volumes</span>
          <Wrench size={12} color="var(--text-muted)" />
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 4 }}>
          {toolEntries.length === 0 ? (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>No tools recorded</span>
          ) : (
            toolEntries.map(([tool, count]) => (
              <span key={tool} className="badge badge-muted" style={{ fontSize: 9.5, fontFamily: 'var(--font-mono)' }}>
                {tool}: {count}
              </span>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
