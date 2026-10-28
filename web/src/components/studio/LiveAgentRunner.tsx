// web/src/components/studio/LiveAgentRunner.tsx - Real-time Live Agent Runner Studio

import React, { useState } from 'react';
import { Play, Bug, CheckCircle, Sparkles, RefreshCw } from 'lucide-react';
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
        background: '#0e131d',
        borderBottom: '1px solid #1c2638',
        padding: '12px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>
          <Sparkles size={14} color="#3b82f6" />
          <span>Interactive Live Agent Studio</span>
        </div>
        <span style={{ fontSize: 11, color: '#64748b' }}>
          Live tool execution against local SQLite database
        </span>
      </div>

      <div style={{ display: 'flex', gap: 10 }}>
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter goal or prompt for autonomous agent..."
          style={{
            flex: 1,
            background: '#07090e',
            border: '1px solid #2a3852',
            borderRadius: 6,
            padding: '7px 12px',
            color: '#f8fafc',
            fontSize: 12,
            fontFamily: 'inherit',
          }}
        />

        <button
          onClick={() => handleRun('flawed_v1')}
          disabled={isRunning}
          className="btn btn-danger"
          style={{ whiteSpace: 'nowrap' }}
          title="Executes Agent v1 (has SQL schema bug)"
        >
          {isRunning ? <RefreshCw size={12} className="animate-spin" /> : <Bug size={13} />}
          Run Flawed Agent (v1)
        </button>

        <button
          onClick={() => handleRun('fixed_v2')}
          disabled={isRunning}
          className="btn btn-success"
          style={{ whiteSpace: 'nowrap' }}
          title="Executes Agent v2 (self-correcting SQL schema)"
        >
          {isRunning ? <RefreshCw size={12} className="animate-spin" /> : <CheckCircle size={13} />}
          Run Fixed Agent (v2)
        </button>
      </div>

      {lastResult && (
        <div style={{ fontSize: 11, color: '#94a3b8', display: 'flex', gap: 14 }}>
          <span>Executed Mode: <strong style={{ color: '#fff' }}>{lastResult.agent_mode}</strong></span>
          <span>Trace ID: <code style={{ color: '#60a5fa' }}>{lastResult.trace_id}</code></span>
          <span>Score: <strong style={{ color: lastResult.passed ? '#34d399' : '#fb7185' }}>{(lastResult.mean_score * 100).toFixed(0)}%</strong></span>
          {lastResult.root_cause && (
            <span style={{ color: '#fb7185' }}>
              Fault: {lastResult.root_cause.primary_category} at {lastResult.root_cause.primary_failure_node_id}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
