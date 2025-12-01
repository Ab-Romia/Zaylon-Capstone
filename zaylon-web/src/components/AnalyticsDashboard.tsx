'use client';

import { Analytics } from '@/types/agent';
import { formatDuration } from '@/lib/utils';
import { Clock, User, Wrench, Brain } from 'lucide-react';

interface AnalyticsDashboardProps {
  analytics: Analytics | null;
}

export function AnalyticsDashboard({ analytics }: AnalyticsDashboardProps) {
  if (!analytics) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-400">
        <p className="text-sm">Analytics will appear after response...</p>
      </div>
    );
  }

  const metrics = [
    {
      label: 'Total Time',
      value: formatDuration(analytics.totalTime),
      icon: Clock,
      color: 'text-blue-600',
    },
    {
      label: 'Agent',
      value: analytics.agent.toUpperCase(),
      icon: User,
      color: 'text-purple-600',
    },
    {
      label: 'Tool Calls',
      value: analytics.toolCalls.toString(),
      icon: Wrench,
      color: 'text-green-600',
    },
    {
      label: 'Thoughts',
      value: analytics.thoughtsCount.toString(),
      icon: Brain,
      color: 'text-orange-600',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 p-4">
      {metrics.map((metric) => {
        const Icon = metric.icon;
        return (
          <div
            key={metric.label}
            className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center gap-2 mb-2">
              <Icon className={`w-5 h-5 ${metric.color}`} />
              <span className="text-xs font-medium text-gray-600">{metric.label}</span>
            </div>
            <p className="text-2xl font-bold text-gray-900">{metric.value}</p>
          </div>
        );
      })}
    </div>
  );
}
