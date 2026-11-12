import { useState, useMemo, useCallback } from 'react';
import { usePortfolioValuation } from './usePortfolioValuation';
import { usePortfolioDrift } from './usePortfolioDrift';
import { portfolioService } from '../services/portfolioService';
import {
  SEEDED_PORTFOLIO_REFERENCES,
  type PortfolioReference,
} from '../types/portfolio';

const DEFAULT_PORTFOLIO_ID = 'PORT-INV-000001-02';
const DEFAULT_AS_OF_DATE = '2026-01-15';

export function usePortfolios() {
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string>(DEFAULT_PORTFOLIO_ID);
  const [asOfDate, setAsOfDate] = useState<string>(DEFAULT_AS_OF_DATE);
  const [customInputId, setCustomInputId] = useState<string>('');
  const [isCustomMode, setIsCustomMode] = useState<boolean>(false);

  const valuationQuery = usePortfolioValuation(selectedPortfolioId, asOfDate);
  const driftQuery = usePortfolioDrift(selectedPortfolioId, asOfDate);

  const activeReference: PortfolioReference | undefined = useMemo(() => {
    return SEEDED_PORTFOLIO_REFERENCES.find(
      (ref) => ref.portfolio_id === selectedPortfolioId
    );
  }, [selectedPortfolioId]);

  const metrics = useMemo(() => {
    return portfolioService.deriveMetrics(valuationQuery.data, driftQuery.data);
  }, [valuationQuery.data, driftQuery.data]);

  const handleSelectPortfolio = useCallback((id: string) => {
    setSelectedPortfolioId(id);
    setIsCustomMode(false);
  }, []);

  const handleApplyCustomId = useCallback(() => {
    if (customInputId.trim()) {
      setSelectedPortfolioId(customInputId.trim());
      setIsCustomMode(true);
    }
  }, [customInputId]);

  const handleRevalue = useCallback(async () => {
    await Promise.all([valuationQuery.refetch(), driftQuery.refetch()]);
  }, [valuationQuery, driftQuery]);

  const isLoading = valuationQuery.isLoading || driftQuery.isLoading;
  const isFetching = valuationQuery.isFetching || driftQuery.isFetching;
  const isError = valuationQuery.isError || driftQuery.isError;
  const error = valuationQuery.error || driftQuery.error;

  return {
    selectedPortfolioId,
    asOfDate,
    setAsOfDate,
    customInputId,
    setCustomInputId,
    isCustomMode,
    setIsCustomMode,
    activeReference,
    portfolioReferences: SEEDED_PORTFOLIO_REFERENCES,
    valuation: valuationQuery.data,
    drift: driftQuery.data,
    metrics,
    isLoading,
    isFetching,
    isError,
    error,
    selectPortfolio: handleSelectPortfolio,
    applyCustomId: handleApplyCustomId,
    revalue: handleRevalue,
  };
}

