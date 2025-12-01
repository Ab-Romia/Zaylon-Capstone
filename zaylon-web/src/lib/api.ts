const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

export async function invokeAgent(message: string, customerId: string = 'web:demo') {
  const response = await fetch(`${API_URL}/api/v2/agent/invoke`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
    body: JSON.stringify({
      customer_id: customerId,
      message,
      channel: 'instagram',
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

export function createStreamConnection(message: string, customerId: string = 'web:demo') {
  // Note: For SSE with POST, we need to use fetch with a special setup
  // This is a simplified version - in production, you'd handle this differently
  return fetch(`${API_URL}/api/v2/agent/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
    body: JSON.stringify({
      customer_id: customerId,
      message,
      channel: 'instagram',
    }),
  });
}
