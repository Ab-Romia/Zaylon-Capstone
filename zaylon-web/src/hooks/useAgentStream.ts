import { useState, useCallback } from 'react';
import { v4 as uuid } from 'uuid';
import type { AgentStreamChunk, ProcessStep, LogEntry, Analytics } from '@/types/agent';

export function useAgentStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [processSteps, setProcessSteps] = useState<ProcessStep[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);

  const streamMessage = useCallback(async (
    message: string,
    onFinalResponse: (chunk: AgentStreamChunk) => void
  ) => {
    setIsStreaming(true);
    setProcessSteps([]);
    setLogs([]);
    setAnalytics(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

    try {
      const response = await fetch(`${API_URL}/api/v2/agent/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': API_KEY,
        },
        body: JSON.stringify({
          customer_id: 'web:demo',
          message,
          channel: 'instagram',
        }),
      });

      if (!response.ok) {
        throw new Error(`Stream failed: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No reader available');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            try {
              const chunk: AgentStreamChunk = JSON.parse(data);
              processChunk(chunk, onFinalResponse);
            } catch (e) {
              console.error('Failed to parse chunk:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Stream error:', error);
      setLogs(prev => [...prev, {
        timestamp: new Date().toLocaleTimeString(),
        level: 'ERROR',
        message: error instanceof Error ? error.message : 'Unknown error',
      }]);
    } finally {
      setIsStreaming(false);
    }
  }, []);

  const processChunk = (chunk: AgentStreamChunk, onFinalResponse: (chunk: AgentStreamChunk) => void) => {
    switch (chunk.type) {
      case 'log':
        setLogs(prev => [...prev, {
          timestamp: new Date(chunk.timestamp).toLocaleTimeString(),
          level: 'INFO',
          message: chunk.content || '',
          node: chunk.node,
        }]);
        break;

      case 'thinking':
        setProcessSteps(prev => [...prev, {
          id: uuid(),
          label: chunk.node === 'supervisor' ? 'Routing Decision' : 'Agent Thinking',
          status: 'active',
          details: chunk.content,
          timestamp: chunk.execution_time_ms,
          node: chunk.node,
        }]);
        break;

      case 'tool_call':
        setProcessSteps(prev => [...prev, {
          id: uuid(),
          label: `Tool: ${chunk.tool_name}`,
          status: 'active',
          details: chunk.content,
          timestamp: chunk.execution_time_ms,
          node: chunk.node,
        }]);
        break;

      case 'tool_result':
        setProcessSteps(prev => prev.map((step, idx) =>
          idx === prev.length - 1 && step.label.includes(chunk.tool_name || '')
            ? { ...step, status: 'completed' }
            : step
        ));
        break;

      case 'agent_processing':
        setProcessSteps(prev => [...prev, {
          id: uuid(),
          label: 'Generating Response',
          status: 'active',
          details: chunk.content,
          timestamp: chunk.execution_time_ms,
          node: chunk.node,
        }]);
        break;

      case 'final_response':
        // Mark all steps as completed
        setProcessSteps(prev => prev.map(step => ({ ...step, status: 'completed' as const })));

        // Set analytics
        if (chunk.success) {
          setAnalytics({
            totalTime: chunk.execution_time_ms || 0,
            agent: chunk.agent_used || 'unknown',
            toolCalls: chunk.tool_calls?.length || 0,
            thoughtsCount: chunk.chain_of_thought?.length || 0,
          });
        }

        // Call final response callback
        onFinalResponse(chunk);
        break;
    }
  };

  const clearState = useCallback(() => {
    setProcessSteps([]);
    setLogs([]);
    setAnalytics(null);
  }, []);

  return {
    streamMessage,
    isStreaming,
    processSteps,
    logs,
    analytics,
    clearState,
  };
}
