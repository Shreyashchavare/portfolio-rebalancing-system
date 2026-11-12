import { useQuery } from '@tanstack/react-query';
import { checkBackendHealth } from '@/services/api/health';
import type { HealthResponse } from '@/types/api';

/**
 * Hook to poll and monitor the FastAPI backend health status.
 */
export function useHealth(refetchInterval = 15000) {
  return useQuery<HealthResponse, Error>({
    queryKey: ['backend-health'],
    queryFn: ({ signal }) => checkBackendHealth(signal),
    refetchInterval,
    retry: 1,
    staleTime: 10000,
  });
}
