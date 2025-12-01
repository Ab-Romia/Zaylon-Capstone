'use client';

import { useAgentStream } from '@/hooks/useAgentStream';
import { ChatInterface } from '@/components/ChatInterface';
import { ProcessVisualization } from '@/components/ProcessVisualization';
import { AnalyticsDashboard } from '@/components/AnalyticsDashboard';
import { SystemLogsPanel } from '@/components/SystemLogsPanel';
import { Activity, BarChart3, Terminal } from 'lucide-react';

export default function Home() {
  const { streamMessage, isStreaming, processSteps, logs, analytics, clearState } = useAgentStream();

  const handleMessageSend = (message: string, onResponse: (response: string) => void) => {
    streamMessage(message, (chunk) => {
      if (chunk.type === 'final_response' && chunk.response) {
        onResponse(chunk.response);
      }
    });
  };

  const handleClearLogs = () => {
    clearState();
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-6">
      <div className="max-w-[1920px] mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-zaylon-primary to-zaylon-secondary bg-clip-text text-transparent">
            ZAYLON
          </h1>
          <p className="text-gray-600 mt-1">AI-Powered Customer Engagement That Converts</p>
        </div>

        {/* Main Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-120px)]">
          {/* Left Column - Chat Interface */}
          <div className="lg:col-span-2 h-full">
            <ChatInterface onMessageSend={handleMessageSend} isStreaming={isStreaming} />
          </div>

          {/* Right Column - Panels */}
          <div className="flex flex-col gap-6 h-full">
            {/* Process Visualization */}
            <div className="bg-white rounded-lg shadow-lg border border-gray-200 flex-1 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-zaylon-primary" />
                  <h3 className="font-semibold text-gray-900">Process Flow</h3>
                </div>
              </div>
              <div className="overflow-y-auto h-[calc(100%-60px)]">
                <ProcessVisualization steps={processSteps} />
              </div>
            </div>

            {/* Analytics Dashboard */}
            <div className="bg-white rounded-lg shadow-lg border border-gray-200">
              <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-zaylon-primary" />
                  <h3 className="font-semibold text-gray-900">Analytics</h3>
                </div>
              </div>
              <AnalyticsDashboard analytics={analytics} />
            </div>
          </div>
        </div>

        {/* Bottom Panel - System Logs */}
        <div className="mt-6 bg-white rounded-lg shadow-lg border border-gray-200 h-64 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
            <div className="flex items-center gap-2">
              <Terminal className="w-5 h-5 text-zaylon-primary" />
              <h3 className="font-semibold text-gray-900">System Logs</h3>
            </div>
          </div>
          <div className="h-[calc(100%-60px)]">
            <SystemLogsPanel logs={logs} onClear={handleClearLogs} />
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center text-sm text-gray-500">
          <p>Created by Abdelrahman Abouroumia (Romia) & Abdelrahman Mashaal</p>
          <p className="mt-1">ZAYLON v1.0 • Multi-Agent Architecture • Production Ready</p>
        </div>
      </div>
    </main>
  );
}
