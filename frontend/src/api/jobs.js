import { apiClient } from './client';

export async function getJobStatus(jobId) {
  return apiClient(`/api/v1/jobs/${jobId}`, {
    method: 'GET',
  });
}
