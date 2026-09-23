export type AgentState =
  | "IDLE"
  | "LISTENING"
  | "THINKING"
  | "EXECUTING"
  | "SPEAKING"
  | "INTERRUPTED"
  | "REPLANNING";

export type TaskStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "CANCELLED"
  | "FAILED"
  | "BLOCKED";

export type PlanDiffAction = "KEEP" | "CANCEL" | "MODIFY" | "ADD";

export interface Task {
  id: string;
  name: string;
  description?: string;
  status: TaskStatus;
  tool: string;
  input: Record<string, any>;
  output?: Record<string, any> | null;
  dependencies: string[];
  priority: number;
  diff_action?: PlanDiffAction | null;
  cancellation_reason?: string | null;
}

export interface PlanDiff {
  keep: string[];
  cancel: string[];
  modify: Array<{ task_id: string; new_input?: any; reason?: string }>;
  add: Array<Record<string, any>>;
  summary?: string;
}

export interface NexusEvent {
  id?: string;
  type: string;
  event_type: string;
  timestamp: string;
  session_id: string;
  data: Record<string, any>;
}

export interface TranscriptMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  isInterruption?: boolean;
  category?: string;
}

export interface SessionSnapshot {
  session_id: string;
  state: AgentState;
  previous_state: AgentState;
  goal: {
    current_goal: {
      id: string;
      summary: string;
      constraints: Record<string, any>;
      version: number;
    } | null;
    history_count: number;
  };
  context: {
    current_goal_summary: string;
    constraints: Record<string, any>;
    preferences: Record<string, any>;
    completed_findings: Array<{
      id: string;
      category: string;
      data: Record<string, any>;
      still_valid: boolean;
    }>;
    interruption_count: number;
  };
  task_graph: {
    tasks: Task[];
    version: number;
  };
  running_tasks: string[];
  interruption_count: number;
}
