export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'pending':
      return 'bg-gray-100 text-gray-700 border-gray-300';
    case 'active':
      return 'bg-blue-50 text-blue-700 border-blue-300 animate-pulse-soft';
    case 'completed':
      return 'bg-green-50 text-green-700 border-green-300';
    case 'error':
      return 'bg-red-50 text-red-700 border-red-300';
    default:
      return 'bg-gray-100 text-gray-700';
  }
}

export function getLogLevelColor(level: string): string {
  switch (level) {
    case 'INFO':
      return 'text-green-400';
    case 'WARNING':
      return 'text-yellow-400';
    case 'ERROR':
      return 'text-red-400';
    default:
      return 'text-gray-400';
  }
}
