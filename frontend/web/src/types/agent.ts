// © 2026 BUPT_Mint-Green
// All rights reserved.

export type AgentTask =
  | "chat"
  | "generate"
  | "review"
  | "appreciate"
  | "recite"
  | "compare"
  | "expand";

export interface ChatMessage {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  branch_id: string;
  created_at: string;
}

export interface AgentMemory {
  id: number;
  session_id: string;
  kind: "preference" | "weakness" | "revision" | string;
  content: string;
  task: AgentTask | "";
  confidence: number;
  active: number;
  created_at: string;
}

export interface ConversationBranch {
  id: string;
  conversation_id: string;
  parent_branch_id: string | null;
  fork_message_id: number | null;
  name: string;
  created_at: string;
  message_count: number;
}

export interface WorkspaceState {
  conversation_id: string;
  branch_id: string;
  history?: ChatMessage[];
  branches?: ConversationBranch[];
  memories?: AgentMemory[];
  trace?: Record<string, unknown>[];
  versions?: Record<string, unknown>[];
  work_state?: Record<string, unknown>;
}

export interface AgentRequest {
  task: AgentTask;
  query: string;
  poem: string;
  form: string;
  emotion: string;
  themes: string[];
  session_id: string;
  conversation_id: string;
  branch_id: string;
  followup: boolean;
  content: string;
}

export type RealtimeServerEvent =
  | { type: "voice.ready"; mode: "full_duplex"; input_sample_rate: number; output_sample_rate: number }
  | { type: "audio.delta"; audio: string }
  | { type: "input.transcript.delta" | "input.transcript" | "assistant.transcript.delta"; text: string }
  | { type: "input.transcription.completed"; text?: string }
  | { type: "input_audio_buffer.speech_started" | "input_audio_buffer.speech_stopped" | "response.done" | "response.cancelled" }
  | { type: "error"; message: string };
