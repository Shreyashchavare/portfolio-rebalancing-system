import { createContext } from 'react';
import type { DevMockTokenOption, ReviewerContext, BusinessPersona } from '@/types/auth';

export interface AuthContextValue {
  token: string | null;
  reviewer: ReviewerContext | null;
  activeMockToken: DevMockTokenOption | null;
  persona: BusinessPersona;
  isDevelopment: boolean;
  canApprove: boolean;
  canGenerateProposals: boolean;
  isAdmin: boolean;
  isCustomer: boolean;
  isAnalyst: boolean;
  isCompliance: boolean;
  setToken: (token: string | null) => void;
  selectMockToken: (tokenString: string) => void;
  setPersona: (persona: BusinessPersona) => void;
  clearToken: () => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
