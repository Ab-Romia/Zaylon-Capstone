'use client';

import { useEffect, useRef } from 'react';
import { LogEntry } from '@/types/agent';
import { getLogLevelColor } from '@/lib/utils';
import { Trash2 } from 'lucide-react';

interface SystemLogsPanelProps {
  logs: LogEntry[];
  onClear?: () => void;
}

export function SystemLogsPanel({ logs, onClear }: SystemLogsPanelProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-700">
        <span className="text-green-400 font-mono text-sm font-bold">System Logs</span>
        {onClear && (
          <button
            onClick={onClear}
            className="text-gray-400 hover:text-white transition-colors"
            title="Clear logs"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>
      <div className="flex-1 bg-black text-green-400 font-mono text-xs overflow-y-auto p-4">
        {logs.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            System logs will appear here...
          </div>
        ) : (
          <>
            {logs.map((log, idx) => (
              <div
                key={idx}
                className="hover:bg-gray-900 px-2 py-1 transition-colors cursor-default"
              >
                <span className="text-gray-500">[{log.timestamp}]</span>
                <span className={`ml-2 font-bold ${getLogLevelColor(log.level)}`}>
                  {log.level}
                </span>
                {log.node && (
                  <span className="ml-2 text-blue-400">({log.node})</span>
                )}
                <span className="ml-2">{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </>
        )}
      </div>
    </div>
  );
}
