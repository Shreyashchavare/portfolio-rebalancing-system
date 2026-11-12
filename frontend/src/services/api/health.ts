import { apiRequest } from './client';
import { API_ENDPOINTS } from './endpoints';
import type { HealthResponse } from '@/types/api';

/**
 * Checks the operational health of the FastAPI backend.
 */
export async function checkBackendHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiRequest<HealthResponse>({
    method: 'GET',
    url: API_ENDPOINTS.HEALTH,
    signal,
  });
}
