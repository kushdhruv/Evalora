// web/src/components/dashboard/HealthKPIStrip.tsx - Fleet Health KPI Metrics Strip

import React from 'react';
import { Activity, Clock, ShieldCheck, DollarSign, Wrench, AlertTriangle } from 'lucide-react';
import { HealthSummary } from '../../types';

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
          <ShieldCheck size={14} color={Number(successPct) >= 80 ? '#10b981' : '#f59e0b'} />
        </div>
        <div className="kpi-value" style={{ color: Number(successPct) >= 80 ? '#34d399' : '#fbbf24' }}>
          {successPct}%
        </div>
        <span className="kpi-subtext">Across {summary.total_trajectories} recorded traces</span>
      </div>

      {/* 2. Latency (Avg & P95) */}
      <div className="kpi-card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="kpi-label">Avg / p95 Latency</span>
          <Clock size={14} color="#3b82f6" />
        </div>
        <div className="kpi-value" style={{ color: '#60a5fa' }}>
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
          <DollarSign size={14} color="#10b981" />
        </div>
        <div className="kpi-value" style={{ color: '#34d399' }}>
          ${summary.total_cost_usd.toFixed(4)}
        </div>
        <span className="kpi-subtext">Zero-cost local judge active</span>
      </div>

      {/* 4. Failure Categorization */}
      <div className="kpi-card" style={{ gridColumn: 'span 2' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 2 }}>
          <span className="kpi-label">Failure Breakdown</span>
          <AlertTriangle size={13} color="#f43f5e" />
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
          {failureEntries.length === 0 ? (
            <span style={{ fontSize: 11, color: '#34d399', fontWeight: 500 }}>Zero failures detected across fleet</span>
          ) : (
            failureEntries.map(([cat, count]) => (
              <span key={cat} className="badge badge-rose" style={{ fontSize: 10 }}>
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
          <Wrench size={13} color="#f59e0b" />
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
          {toolEntries.length === 0 ? (
            <span style={{ fontSize: 11, color: '#64748b' }}>No tools recorded</span>
          ) : (
            toolEntries.map(([tool, count]) => (
              <span key={tool} className="badge badge-amber" style={{ fontSize: 10, fontFamily: 'monospace' }}>
                {tool}: {count}
              </span>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
