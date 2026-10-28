// web/src/services/api.ts - Client API Service for Evalora Backend

import type { GoldenPathComparison, HealthSummary, Trajectory, TrajectoryDetailResponse } from '../types';

const BASE_URL = '';

export async function fetchHealthSummary(): Promise<HealthSummary> {
  const res = await fetch(`${BASE_URL}/api/v1/health-summary`);
  if (!res.ok) throw new Error(`Failed to fetch health summary: ${res.statusText}`);
  return res.json();
}

export async function fetchTrajectories(): Promise<Trajectory[]> {
  const res = await fetch(`${BASE_URL}/api/v1/trajectories`);
  if (!res.ok) throw new Error(`Failed to fetch trajectories: ${res.statusText}`);
  return res.json();
}

export async function fetchTrajectoryDetails(traceId: string): Promise<TrajectoryDetailResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/trajectories/${traceId}`);
  if (!res.ok) throw new Error(`Failed to fetch trajectory details for ${traceId}: ${res.statusText}`);
  return res.json();
}

export async function compareGoldenPath(
  actualTraceId: string,
  expectedToolSequence: string[]
): Promise<GoldenPathComparison> {
  const res = await fetch(`${BASE_URL}/api/v1/golden-path/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      actual_trace_id: actualTraceId,
      expected_tool_sequence: expectedToolSequence,
    }),
  });
  if (!res.ok) throw new Error(`Failed to compare golden path: ${res.statusText}`);
  return res.json();
}

export async function runLiveAgent(agentMode: 'flawed_v1' | 'fixed_v2', prompt?: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/v1/agent/run-live`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      agent_mode: agentMode,
      prompt,
    }),
  });
  if (!res.ok) throw new Error(`Failed to run live agent: ${res.statusText}`);
  return res.json();
}

export async function curateTraceToDataset(
  datasetId: string,
  traceId: string,
  customPrompt?: string,
  expectedOutcome?: string
): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/v1/datasets/${datasetId}/items/from-trace/${traceId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      dataset_id: datasetId,
      custom_prompt: customPrompt,
      expected_outcome: expectedOutcome,
    }),
  });
  if (!res.ok) throw new Error(`Failed to curate trace to dataset: ${res.statusText}`);
  return res.json();
}
