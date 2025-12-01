'use client';

import { ProcessStep } from '@/types/agent';
import { getStatusColor, formatDuration } from '@/lib/utils';
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react';

interface ProcessVisualizationProps {
  steps: ProcessStep[];
}

export function ProcessVisualization({ steps }: ProcessVisualizationProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-600" />;
      case 'active':
        return <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <Circle className="w-5 h-5 text-gray-400" />;
    }
  };

  if (steps.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-400">
        <p className="text-sm">Process steps will appear here...</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 p-4 max-h-[400px] overflow-y-auto">
      {steps.map((step, idx) => (
        <div
          key={step.id}
          className={`p-3 rounded-lg border transition-all duration-300 ${getStatusColor(step.status)}`}
          style={{
            animation: 'slideUp 0.3s ease-out',
            animationDelay: `${idx * 50}ms`,
            animationFillMode: 'both',
          }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {getStatusIcon(step.status)}
              <span className="font-medium text-sm">{step.label}</span>
            </div>
            {step.timestamp && (
              <span className="text-xs text-gray-500">{formatDuration(step.timestamp)}</span>
            )}
          </div>
          {step.details && (
            <div className="mt-2 text-xs text-gray-600 ml-7 italic">
              {step.details}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
