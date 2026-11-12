import { useQuery } from '@tanstack/react-query';
import { portfolioService } from '../services/portfolioService';
import type { PortfolioValuationResult } from '../types/portfolio';

export function usePortfolioValuation(portfolioId: string, asOfDate?: string) {
  return useQuery<PortfolioValuationResult, Error>({
    queryKey: ['portfolio', 'valuation', portfolioId, asOfDate || 'default'],
    queryFn: () => portfolioService.getValuation(portfolioId, asOfDate),
    enabled: Boolean(portfolioId.trim()),
    staleTime: 30_000,
  });
}

