// web/src/types/index.ts - Core TypeScript Definitions for Evalora

export type EventType =
  | 'plan'
  | 'tool_call'
  | 'memory_read'
  | 'memory_write'
  | 'reasoning'
  | 'state_update'
  | 'observation'
  | 'final_outcome';

export type FailureCategory =
  | 'planning'
  | 'tool'
  | 'context_memory'
  | 'reasoning_state'
  | 'environment'
  | 'outcome';

export interface TrajectoryNode {
  node_id: string;
  event_id: string;
  timestamp: string;
  event_type: EventType;
  label: string;
  payload: {
    content?: string;
    tool_call?: {
      tool_name?: string;
      input_args?: Record<string, any>;
      output_result?: any;
      is_error?: boolean;
      error_message?: string;
    };
    memory_event?: {
      operation?: string;
      key?: string;
      retrieved_keys?: string[];
      retrieved_content?: any[];
      similarity_scores?: number[];
    };
    duration_ms?: number;
    tokens?: number;
    cost_usd?: number;
    [key: string]: any;
  };
  parent_node_id?: string;
  duration_ms?: number;
  tokens?: number;
  cost_usd?: number;
}

export interface TrajectoryEdge {
  source_node_id: string;
  target_node_id: string;
  edge_type: 'sequence' | 'invocation' | 'data_flow' | string;
  metadata?: Record<string, any>;
}

export interface Trajectory {
  trajectory_id: string;
  trace_id: string;
  agent_id: string;
  agent_version: string;
  goal?: string;
  nodes: TrajectoryNode[];
  edges: TrajectoryEdge[];
  total_latency_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  is_success?: boolean;
  created_at?: string;
}

export interface Evaluation {
  eval_id: string;
  target_node_id: string;
  evaluator_name: string;
  evaluator_layer: 'deterministic' | 'semantic' | 'llm_judge' | 'trajectory';
  evaluator_version: string;
  score: number;
  confidence: number;
  passed: boolean;
  rationale?: string;
  details?: Record<string, any>;
  created_at?: string;
}

export interface Failure {
  failure_id: string;
  node_id: string;
  category: FailureCategory;
  subcategory?: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL' | 'FATAL';
  description: string;
  is_terminal: boolean;
  created_at?: string;
}

export interface RootCause {
  primary_failure_node_id: string;
  primary_category: FailureCategory;
  confidence_score: number;
  propagation_chain: string[];
  explanation: string;
}

export interface MemoryAudit {
  has_memory_events: boolean;
  retrieval_relevance_score: number;
  prompt_retention_score: number;
  causal_usefulness_score: number;
  staleness_detected: boolean;
  findings: string[];
  passed: boolean;
}

export interface TrajectoryDetailResponse {
  trajectory: Trajectory;
  evaluations: Evaluation[];
  failures: Failure[];
  root_cause: RootCause | null;
  memory_audit: MemoryAudit;
}

export interface HealthSummary {
  total_trajectories: number;
  success_rate: number;
  tool_usage_counts: Record<string, number>;
  failure_category_counts: Record<string, number>;
  total_cost_usd: number;
  avg_latency_ms: number;
  p50_latency_ms?: number;
  p95_latency_ms?: number;
  p99_latency_ms?: number;
  active_agents_count?: number;
}

export interface GoldenPathComparison {
  trace_id: string;
  actual_tool_sequence: string[];
  expected_tool_sequence: string[];
  sequence_match_ratio: number;
  exact_match: boolean;
}
