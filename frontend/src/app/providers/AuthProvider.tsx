import {
  useEffect,
  useState,
  type ReactNode,
  useCallback,
} from 'react';
import { setAuthToken } from '@/services/api/client';
import {
  DEV_MOCK_TOKENS,
  type ReviewerContext,
} from '@/types/auth';
import { AuthContext } from './AuthContext';

const STORAGE_KEY = 'yottaflex_reviewer_token';

function resolveReviewerFromToken(token: string | null): ReviewerContext | null {
  if (!token) return null;
  const match = DEV_MOCK_TOKENS.find((m) => m.token === token);
  if (match) {
    return {
      reviewer_id: match.reviewerId,
      role: match.role,
      email: `${match.reviewerId.toLowerCase()}@yottaflex.local`,
    };
  }
  // Generic / external token (e.g. from an IdP)
  return {
    reviewer_id: 'EXTERNAL-REVIEWER',
    role: 'REVIEWER',
    email: 'reviewer@yottaflex.local',
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const isDevelopment =
    import.meta.env.MODE === 'development' ||
    import.meta.env.MODE === 'test' ||
    import.meta.env.VITE_APP_ENV === 'development';

  const [token, setTokenState] = useState<string | null>(() => {
    const saved = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null;
    if (saved) return saved;
    if (isDevelopment) {
      return import.meta.env.VITE_DEFAULT_MOCK_TOKEN || 'dev-reviewer-token';
    }
    return null;
  });

  const [reviewer, setReviewer] = useState<ReviewerContext | null>(() =>
    resolveReviewerFromToken(token)
  );

  const setToken = useCallback((newToken: string | null) => {
    setTokenState(newToken);
    if (newToken) {
      localStorage.setItem(STORAGE_KEY, newToken);
      setAuthToken(newToken);
      setReviewer(resolveReviewerFromToken(newToken));
    } else {
      localStorage.removeItem(STORAGE_KEY);
      setAuthToken(null);
      setReviewer(null);
    }
  }, []);

  const selectMockToken = useCallback(
    (tokenString: string) => {
      setToken(tokenString);
    },
    [setToken]
  );

  const clearToken = useCallback(() => {
    setToken(null);
  }, [setToken]);

  // Sync token to API client upon initial mount
  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  const activeMockToken = DEV_MOCK_TOKENS.find((m) => m.token === token) || null;

  return (
    <AuthContext.Provider
      value={{
        token,
        reviewer,
        activeMockToken,
        isDevelopment,
        setToken,
        selectMockToken,
        clearToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
