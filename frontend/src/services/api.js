/**
 * Lyftr AI API Client Service
 */

const API_BASE_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '');

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }
  return response.json();
}

export async function sendChatMessage({ sessionId, message, systemPrompt, simulateHeader }) {
  const headers = {
    'Content-Type': 'application/json',
  };

  if (simulateHeader && simulateHeader !== 'none') {
    headers['X-Simulate-Failure'] = simulateHeader;
  }

  const payload = {
    session_id: sessionId,
    message: message,
  };

  if (systemPrompt && systemPrompt.trim()) {
    payload.system_prompt = systemPrompt.trim();
  }

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({ detail: 'Failed to parse response' }));

  if (!response.ok) {
    const errorDetail = data?.detail || `Request failed with status ${response.status}`;
    const error = new Error(errorDetail);
    error.status = response.status;
    error.detail = errorDetail;
    throw error;
  }

  return data;
}

export async function fetchSessionMessages(sessionId) {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`);
  if (!response.ok) {
    if (response.status === 404) {
      return { session_id: sessionId, messages: [] };
    }
    throw new Error(`Failed to fetch session messages: ${response.status}`);
  }
  return response.json();
}
