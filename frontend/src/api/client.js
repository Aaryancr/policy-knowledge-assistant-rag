/**
 * Centralized API client for Policy & Knowledge Assistant.
 * Handles Bearer token injection, response parsing, and HTTP error normalization.
 */

const TOKEN_KEY = 'policy_rag_token';
const USER_KEY = 'policy_rag_user';

export const tokenStorage = {
  get: () => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (token) => {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      // Storage unavailable or disabled
    }
  },
  clear: () => {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch {
      // Storage unavailable
    }
  },
  getUser: () => {
    try {
      const data = localStorage.getItem(USER_KEY);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },
  setUser: (user) => {
    try {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch {
      // Storage unavailable
    }
  },
};

export class ApiError extends Error {
  constructor(message, status = 500, detail = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

let onUnauthorizedCallback = null;

export function setOnUnauthorizedCallback(cb) {
  onUnauthorizedCallback = cb;
}

export async function apiClient(endpoint, options = {}) {
  const token = tokenStorage.get();
  const headers = new Headers(options.headers || {});

  // Set Authorization header if token exists and not already provided
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Set Content-Type: application/json if sending a JSON body and not a FormData object
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const config = {
    ...options,
    headers,
  };

  try {
    const response = await fetch(endpoint, config);

    // 401 Unauthorized handling
    if (response.status === 401) {
      tokenStorage.clear();
      if (typeof onUnauthorizedCallback === 'function') {
        onUnauthorizedCallback();
      }
      const errorData = await response.json().catch(() => null);
      const message = errorData?.detail || 'Session expired or unauthorized. Please log in again.';
      throw new ApiError(message, 401, errorData);
    }

    // 204 No Content
    if (response.status === 204) {
      return null;
    }

    // Parse JSON or text
    const contentType = response.headers.get('content-type') || '';
    let data;
    if (contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      let errorMessage = 'An unexpected server error occurred.';
      if (data && typeof data === 'object' && data.detail) {
        if (typeof data.detail === 'string') {
          errorMessage = data.detail;
        } else if (Array.isArray(data.detail)) {
          // Pydantic validation errors array
          errorMessage = data.detail.map((err) => `${err.loc?.slice(-1)[0] || 'field'}: ${err.msg}`).join(', ');
        }
      }
      throw new ApiError(errorMessage, response.status, data);
    }

    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network failure, DNS issue, or server offline
    throw new ApiError(
      'Unable to connect to the backend server. Please verify the service is running.',
      0,
      error
    );
  }
}
