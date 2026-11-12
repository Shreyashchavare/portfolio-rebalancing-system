import { createContext } from 'react';
import type { DevMockTokenOption, ReviewerContext } from '@/types/auth';

export interface AuthContextValue {
  token: string | null;
  reviewer: ReviewerContext | null;
  activeMockToken: DevMockTokenOption | null;
  isDevelopment: boolean;
  setToken: (token: string | null) => void;
  selectMockToken: (tokenString: string) => void;
  clearToken: () => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
