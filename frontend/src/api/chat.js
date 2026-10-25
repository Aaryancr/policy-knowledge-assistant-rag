import { apiClient } from './client';

export async function queryChat({ question, top_k = 5, min_similarity = null }) {
  const payload = {
    question: question.trim(),
    top_k,
  };
  if (typeof min_similarity === 'number') {
    payload.min_similarity = min_similarity;
  }

  return apiClient('/api/v1/chat/query', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function listChatLogs({ skip = 0, limit = 50 } = {}) {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  return apiClient(`/api/v1/chat/logs?${params.toString()}`, {
    method: 'GET',
  });
}
