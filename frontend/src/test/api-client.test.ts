import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  createApiClient,
  getApiBaseUrl,
  setAuthToken,
  getAuthToken,
  apiClient,
} from '@/services/api/client';
import { ApiError } from '@/types/api';

describe('API Client Foundation', () => {
  beforeEach(() => {
    setAuthToken(null);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    setAuthToken(null);
  });

  it('resolves the base URL from environment variables correctly', () => {
    const baseUrl = getApiBaseUrl();
    expect(typeof baseUrl).toBe('string');
  });

  it('manages reviewer bearer token state', () => {
    expect(getAuthToken()).toBeNull();
    setAuthToken('dev-reviewer-token');
    expect(getAuthToken()).toBe('dev-reviewer-token');
    setAuthToken(null);
    expect(getAuthToken()).toBeNull();
  });

  it('attaches the Authorization Bearer header when token is set', () => {
    setAuthToken('mock-auth-token-123');
    const client = createApiClient('/test-api');

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const handlers = (client.interceptors.request as any).handlers;
    const authHandler = handlers[0];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const config = { headers: {} } as any;
    const transformedConfig = authHandler.fulfilled(config);
    expect(transformedConfig.headers.Authorization).toBe('Bearer mock-auth-token-123');
  });

  it('transforms HTTP 401 Unauthorized responses into typed ApiError without bypassing auth', async () => {
    vi.spyOn(apiClient, 'request').mockRejectedValueOnce(
      new ApiError({
        message: 'Authentication required or invalid reviewer token.',
        status: 401,
        detail: 'Authentication token is missing or invalid.',
      })
    );

    try {
      await apiClient.request({ method: 'GET', url: '/api/v1/workflows' });
      expect.fail('Expected request to throw');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(401);
      expect(apiErr.userMessage).toContain('Authentication');
    }
  });

  it('transforms HTTP 403 Forbidden responses into typed ApiError for insufficient reviewer roles', async () => {
    vi.spyOn(apiClient, 'request').mockRejectedValueOnce(
      new ApiError({
        message: 'Access forbidden. Reviewer role has insufficient permissions.',
        status: 403,
        detail: 'Caller with VIEWER role is not permitted to execute governance actions.',
      })
    );

    try {
      await apiClient.request({
        method: 'POST',
        url: '/api/v1/proposals/RB-001/approve',
      });
      expect.fail('Expected request to throw');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(403);
      expect(apiErr.userMessage).toContain('VIEWER');
    }
  });

  it('transforms HTTP 422 Unprocessable Content validation errors with details', async () => {
    vi.spyOn(apiClient, 'request').mockRejectedValueOnce(
      new ApiError({
        message: 'Business validation failed.',
        status: 422,
        detail: 'Missing market price for instrument on date.',
      })
    );

    try {
      await apiClient.request({
        method: 'GET',
        url: '/api/v1/portfolios/PORT-01/valuation',
      });
      expect.fail('Expected request to throw');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(422);
      expect(apiErr.userMessage).toContain('Missing market price');
    }
  });

  it('handles request cancellation properly', async () => {
    vi.spyOn(apiClient, 'request').mockRejectedValueOnce(
      new ApiError({
        message: 'Request was cancelled',
        status: 0,
        isCancelled: true,
      })
    );

    try {
      await apiClient.request({
        method: 'GET',
        url: '/api/v1/portfolios/PORT-01/drift',
      });
      expect.fail('Expected request to throw');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.isCancelled).toBe(true);
      expect(apiErr.status).toBe(0);
    }
  });

  it('handles network failure when backend is unreachable', async () => {
    vi.spyOn(apiClient, 'request').mockRejectedValueOnce(
      new ApiError({
        message: 'Unable to connect to the backend server. Please verify the service is running.',
        status: 0,
        isNetworkError: true,
      })
    );

    try {
      await apiClient.request({
        method: 'GET',
        url: '/health',
      });
      expect.fail('Expected request to throw');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.isNetworkError).toBe(true);
      expect(apiErr.userMessage).toContain('Unable to connect');
    }
  });
});
