// web/src/components/studio/LiveAgentRunner.tsx - Clean Minimalist Live Agent Runner Studio

import React, { useState } from 'react';
import { Bug, CheckCircle, Sparkles, RefreshCw } from 'lucide-react';
import { runLiveAgent } from '../../services/api';

interface LiveAgentRunnerProps {
  onRunComplete: (newTraceId: string) => void;
}

export function LiveAgentRunner({ onRunComplete }: LiveAgentRunnerProps) {
  const [prompt, setPrompt] = useState<string>(
    'Check the overdue balance for customer acct_982 and email the summary to their billing address.'
  );
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [lastResult, setLastResult] = useState<any | null>(null);

  const handleRun = async (mode: 'flawed_v1' | 'fixed_v2') => {
    setIsRunning(true);
    setLastResult(null);
    try {
      const res = await runLiveAgent(mode, prompt);
      setLastResult(res);
      if (res.trace_id) {
        onRunComplete(res.trace_id);
      }
    } catch (e: any) {
      console.error('Run failed:', e);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '10px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        transition: 'background-color 0.2s ease, border-color 0.2s ease',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, fontWeight: 700, color: 'var(--text-primary)' }}>
          <Sparkles size={13} color="var(--text-primary)" />
          <span>Interactive Live Agent Studio</span>
        </div>
        <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>
          Direct telemetry execution against local SQLite runtime
        </span>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter goal or prompt for autonomous agent..."
          style={{
            flex: 1,
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 10px',
            color: 'var(--text-primary)',
            fontSize: 12,
            fontFamily: 'inherit',
          }}
        />

        <button
          onClick={() => handleRun('flawed_v1')}
          disabled={isRunning}
          className="btn btn-danger"
          style={{ whiteSpace: 'nowrap' }}
          title="Executes Agent v1 (contains SQL schema fault)"
        >
          {isRunning ? <RefreshCw size={11} className="animate-spin" /> : <Bug size={12} />}
          Run Flawed Agent (v1)
        </button>

        <button
          onClick={() => handleRun('fixed_v2')}
          disabled={isRunning}
          className="btn btn-success"
          style={{ whiteSpace: 'nowrap' }}
          title="Executes Agent v2 (self-correcting SQL schema)"
        >
          {isRunning ? <RefreshCw size={11} className="animate-spin" /> : <CheckCircle size={12} />}
          Run Fixed Agent (v2)
        </button>
      </div>

      {lastResult && (
        <div style={{ fontSize: 10.5, color: 'var(--text-muted)', display: 'flex', gap: 14 }}>
          <span>Mode: <strong style={{ color: 'var(--text-primary)' }}>{lastResult.agent_mode}</strong></span>
          <span>Trace ID: <code style={{ color: 'var(--text-primary)' }}>{lastResult.trace_id}</code></span>
          <span>Score: <strong style={{ color: lastResult.passed ? 'var(--emerald-text)' : 'var(--rose-text)' }}>{(lastResult.mean_score * 100).toFixed(0)}%</strong></span>
        </div>
      )}
    </div>
  );
}
