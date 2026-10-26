import { apiClient } from './client.js';

/**
 * Normalizes document list responses from the backend API.
 * Supports standard FastAPI `{ items: [...], total: N }`, legacy `{ documents: [...], total: N }`,
 * or direct array `[...]` formats.
 */
export function parseDocumentListResponse(response) {
  if (!response) {
    return { items: [], total: 0 };
  }
  if (Array.isArray(response)) {
    return { items: response, total: response.length };
  }
  const items = Array.isArray(response.items)
    ? response.items
    : Array.isArray(response.documents)
    ? response.documents
    : [];
  const total = typeof response.total === 'number' ? response.total : items.length;
  return { items, total };
}

/**
 * Derives aggregate document status statistics from document records and server total.
 */
export function calculateDocumentStats(documents, serverTotal = null) {
  const safeDocs = Array.isArray(documents) ? documents : [];
  const completed = safeDocs.filter((d) => d.status === 'completed').length;
  const processing = safeDocs.filter(
    (d) => d.status === 'processing' || d.status === 'queued' || d.status === 'pending'
  ).length;
  const failed = safeDocs.filter((d) => d.status === 'failed').length;
  const total = typeof serverTotal === 'number' ? serverTotal : safeDocs.length;
  return {
    total,
    completed,
    processing,
    failed,
  };
}

export async function listDocuments({ skip = 0, limit = 50, status = null } = {}) {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  if (status) {
    params.set('status', status);
  }
  return apiClient(`/api/v1/documents?${params.toString()}`, {
    method: 'GET',
  });
}

export async function uploadDocument(file, title = '') {
  const formData = new FormData();
  formData.append('file', file);
  if (title && title.trim()) {
    formData.append('title', title.trim());
  }

  return apiClient('/api/v1/documents/upload', {
    method: 'POST',
    body: formData,
  });
}

export async function deleteDocument(documentId) {
  return apiClient(`/api/v1/documents/${documentId}`, {
    method: 'DELETE',
  });
}

export async function getDocument(documentId) {
  return apiClient(`/api/v1/documents/${documentId}`, {
    method: 'GET',
  });
}

export async function getDocumentChunks(documentId, { skip = 0, limit = 50 } = {}) {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
  return apiClient(`/api/v1/documents/${documentId}/chunks?${params.toString()}`, {
    method: 'GET',
  });
}
