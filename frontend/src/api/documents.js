import { apiClient } from './client';

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
