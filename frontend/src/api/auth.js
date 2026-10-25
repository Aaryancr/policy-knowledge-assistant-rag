import { apiClient, tokenStorage } from './client';

export async function login({ email, password }) {
  const data = await apiClient('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

  if (data?.access_token) {
    tokenStorage.set(data.access_token);
  }
  return data;
}

export async function getCurrentUser() {
  const user = await apiClient('/api/v1/auth/me', {
    method: 'GET',
  });
  if (user) {
    tokenStorage.setUser(user);
  }
  return user;
}

export function logout() {
  tokenStorage.clear();
}
