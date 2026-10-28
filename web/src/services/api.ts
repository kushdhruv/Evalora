// web/src/services/api.ts - Client API Service for Evalora Backend

import type { GoldenPathComparison, HealthSummary, Trajectory, TrajectoryDetailResponse } from '../types';

const BASE_URL = '';

// In-memory cache and promise deduplication map
interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

const cache = new Map<string, CacheEntry<any>>();
const inFlightRequests = new Map<string, Promise<any>>();

const DEFAULT_TTL_MS = 25_000; // 25 seconds for details

export function clearApiCache() {
  cache.clear();
}

async function dedupeRequest<T>(key: string, fetcher: () => Promise<T>, ttlMs = DEFAULT_TTL_MS): Promise<T> {
  const cached = cache.get(key);
  if (cached && Date.now() - cached.timestamp < ttlMs) {
    return cached.data;
  }

  const existingPromise = inFlightRequests.get(key);
  if (existingPromise) {
    return existingPromise as Promise<T>;
  }

  const promise = fetcher()
    .then((data) => {
      cache.set(key, { data, timestamp: Date.now() });
      inFlightRequests.delete(key);
      return data;
    })
    .catch((err) => {
      inFlightRequests.delete(key);
      throw err;
    });

  inFlightRequests.set(key, promise);
  return promise;
}

export async function fetchHealthSummary(): Promise<HealthSummary> {
  return dedupeRequest('health_summary', async () => {
    const res = await fetch(`${BASE_URL}/api/v1/health-summary`);
    if (!res.ok) throw new Error(`Failed to fetch health summary: ${res.statusText}`);
    return res.json();
  }, 4_000); // 4 second TTL
}

export async function fetchTrajectories(): Promise<Trajectory[]> {
  return dedupeRequest('trajectories_list', async () => {
    const res = await fetch(`${BASE_URL}/api/v1/trajectories`);
    if (!res.ok) throw new Error(`Failed to fetch trajectories: ${res.statusText}`);
    return res.json();
  }, 3_000); // 3 second TTL
}

export async function fetchTrajectoryDetails(traceId: string): Promise<TrajectoryDetailResponse> {
  return dedupeRequest(`trajectory_detail_${traceId}`, async () => {
    const res = await fetch(`${BASE_URL}/api/v1/trajectories/${traceId}`);
    if (!res.ok) throw new Error(`Failed to fetch trajectory details for ${traceId}: ${res.statusText}`);
    return res.json();
  }, 60_000); // 60 second TTL for completed trajectory details
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
