import {
  useEffect,
  useState,
  type ReactNode,
  useCallback,
  useMemo,
} from 'react';
import { setAuthToken } from '@/services/api/client';
import {
  DEV_MOCK_TOKENS,
  getPersonaFromRole,
  type BusinessPersona,
  type ReviewerContext,
} from '@/types/auth';
import { AuthContext } from './AuthContext';

const TOKEN_STORAGE_KEY = 'yottaflex_reviewer_token';
const PERSONA_STORAGE_KEY = 'yottaflex_active_persona';

function resolveReviewerFromToken(token: string | null): ReviewerContext | null {
  if (!token) return null;
  const match = DEV_MOCK_TOKENS.find((m) => m.token === token);
  if (match) {
    return {
      reviewer_id: match.reviewerId,
      role: match.role,
      email: `${match.reviewerId.toLowerCase()}@yottaflex.local`,
      persona: match.persona,
    };
  }
  // Generic / external token (e.g. from an IdP)
  return {
    reviewer_id: 'EXTERNAL-REVIEWER',
    role: 'REVIEWER',
    email: 'reviewer@yottaflex.local',
    persona: 'COMPLIANCE',
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const isDevelopment =
    import.meta.env.MODE === 'development' ||
    import.meta.env.MODE === 'test' ||
    import.meta.env.VITE_APP_ENV === 'development';

  const [token, setTokenState] = useState<string | null>(() => {
    const saved = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_STORAGE_KEY) : null;
    if (saved) return saved;
    if (isDevelopment) {
      return import.meta.env.VITE_DEFAULT_MOCK_TOKEN || 'dev-reviewer-token';
    }
    return null;
  });

  const [reviewer, setReviewer] = useState<ReviewerContext | null>(() =>
    resolveReviewerFromToken(token)
  );

  const [persona, setPersonaState] = useState<BusinessPersona>(() => {
    const saved = typeof window !== 'undefined' ? (localStorage.getItem(PERSONA_STORAGE_KEY) as BusinessPersona) : null;
    if (saved) return saved;
    return getPersonaFromRole(reviewer?.role);
  });

  const setToken = useCallback((newToken: string | null) => {
    setTokenState(newToken);
    if (newToken) {
      localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
      setAuthToken(newToken);
      const rev = resolveReviewerFromToken(newToken);
      setReviewer(rev);
      if (rev) {
        setPersonaState(rev.persona || getPersonaFromRole(rev.role));
      }
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      setAuthToken(null);
      setReviewer(null);
      setPersonaState('CUSTOMER');
    }
  }, []);

  const selectMockToken = useCallback(
    (tokenString: string) => {
      const match = DEV_MOCK_TOKENS.find((m) => m.token === tokenString);
      setToken(tokenString);
      if (match) {
        setPersonaState(match.persona);
        localStorage.setItem(PERSONA_STORAGE_KEY, match.persona);
      }
    },
    [setToken]
  );

  const setPersona = useCallback((newPersona: BusinessPersona) => {
    setPersonaState(newPersona);
    localStorage.setItem(PERSONA_STORAGE_KEY, newPersona);
    // Align mock token in dev if applicable
    const match = DEV_MOCK_TOKENS.find((m) => m.persona === newPersona);
    if (match) {
      setToken(match.token);
    }
  }, [setToken]);

  const clearToken = useCallback(() => {
    setToken(null);
  }, [setToken]);

  // Sync token to API client upon mount & token changes
  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  const activeMockToken = useMemo(
    () => DEV_MOCK_TOKENS.find((m) => m.token === token && m.persona === persona) || DEV_MOCK_TOKENS.find((m) => m.token === token) || null,
    [token, persona]
  );

  const role = reviewer?.role || 'VIEWER';
  const canApprove = role === 'ADMIN' || role === 'REVIEWER' || role === 'COMPLIANCE_OFFICER';
  const canGenerateProposals = role === 'ADMIN' || role === 'PORTFOLIO_MANAGER' || persona === 'ANALYST';
  const isAdmin = role === 'ADMIN' || persona === 'ADMIN';
  const isCustomer = persona === 'CUSTOMER' || role === 'VIEWER';
  const isAnalyst = persona === 'ANALYST' || role === 'PORTFOLIO_MANAGER';
  const isCompliance = persona === 'COMPLIANCE' || role === 'REVIEWER' || role === 'COMPLIANCE_OFFICER';

  return (
    <AuthContext.Provider
      value={{
        token,
        reviewer,
        activeMockToken,
        persona,
        isDevelopment,
        canApprove,
        canGenerateProposals,
        isAdmin,
        isCustomer,
        isAnalyst,
        isCompliance,
        setToken,
        selectMockToken,
        setPersona,
        clearToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
