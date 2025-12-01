export interface AgentThought {
  node: string;
  reasoning: string;
  timestamp: string;
}

export interface AgentToolCall {
  tool_name: string;
  arguments: Record<string, any>;
  result?: string;
  success: boolean;
}

export interface AgentStreamChunk {
  type: 'log' | 'thinking' | 'tool_call' | 'tool_result' | 'agent_processing' | 'final_response';
  content?: string;
  node?: string;
  tool_name?: string;
  tool_args?: Record<string, any>;
  tool_result?: string;
  timestamp: string;
  execution_time_ms?: number;
  done: boolean;

  // Final response fields
  success?: boolean;
  response?: string;
  agent_used?: string;
  chain_of_thought?: AgentThought[];
  tool_calls?: AgentToolCall[];
  user_profile?: Record<string, any>;
  thread_id?: string;
  error?: string;
}

export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  streaming?: boolean;
}

export interface ProcessStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  timestamp?: number;
  details?: string;
  node?: string;
}

export interface LogEntry {
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  node?: string;
}

export interface Analytics {
  totalTime: number;
  agent: string;
  toolCalls: number;
  thoughtsCount: number;
}
