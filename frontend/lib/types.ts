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
  imageUrl?: string;
  sportsFixtures?: SportsFixturesPayload;
}

export interface ChatSessionMeta {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messageCount: number;
  preview: string;
}

export interface StoredChatSession {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: TranscriptMessage[];
  sportsFixtures?: SportsFixturesPayload | null;
  goalSummary?: string;
  tasks?: Task[];
}


export interface SessionSnapshot {
  session_id: string;
  state: AgentState;
  previous_state: AgentState;
  plan_version?: number;
  plan_status?: string;
  goal: {
    current_goal: {
      id: string;
      summary: string;
      constraints: Record<string, any>;
      version: number;
      status?: string;
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

export type MatchStatus =
  | "SCHEDULED"
  | "LIVE"
  | "HALFTIME"
  | "FINISHED"
  | "POSTPONED"
  | "CANCELLED";

export interface TeamInfo {
  name: string;
  short_name: string;
  logo?: string | null;
}

export interface MatchItem {
  id: string;
  sport: string;
  competition: string;
  stage?: string | null;
  group?: string | null;
  start_time: string;
  local_start_time: string;
  local_date: string;
  timezone: string;
  status: MatchStatus;
  status_detail?: string | null;
  elapsed_time?: string | null;
  home_team: TeamInfo;
  away_team: TeamInfo;
  home_score?: number | string | null;
  away_score?: number | string | null;
  venue?: string | null;
  source: string;
}

export interface SportsFixturesPayload {
  query: {
    sport?: string | null;
    competition?: string | null;
    team?: string | null;
    date_from?: string | null;
    date_to?: string | null;
    timezone?: string | null;
    status?: string | null;
  };
  matches: MatchItem[];
  summary?: string;
  generated_at?: string;
  timezone?: string;
}

export interface AuthUser {
  id: number;
  email: string;
  display_name: string;
  created_at?: number;
}

