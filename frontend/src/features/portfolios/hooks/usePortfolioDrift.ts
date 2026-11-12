import { useQuery } from '@tanstack/react-query';
import { portfolioService } from '../services/portfolioService';
import type { PortfolioDriftResult } from '../types/portfolio';

export function usePortfolioDrift(portfolioId: string, asOfDate?: string) {
  return useQuery<PortfolioDriftResult, Error>({
    queryKey: ['portfolio', 'drift', portfolioId, asOfDate || 'default'],
    queryFn: () => portfolioService.getDrift(portfolioId, asOfDate),
    enabled: Boolean(portfolioId.trim()),
    staleTime: 30_000,
  });
}

