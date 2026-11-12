import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
  isAxiosError,
  isCancel,
} from 'axios';
import { ApiError, type ApiErrorDetail } from '@/types/api';

/**
 * Resolves the backend API base URL from Vite environment variables.
 * - When VITE_API_BASE_URL is provided, it is sanitized (trailing slash removed).
 * - When omitted or empty in development, an empty string is used so requests are
 *   handled by the Vite development proxy (/api and /health forwarded to http://127.0.0.1:8000).
 */
export function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return '';
}

/**
 * Global token accessor for attaching reviewer bearer tokens to outgoing requests.
 */
let currentAuthToken: string | null = null;

export function setAuthToken(token: string | null): void {
  currentAuthToken = token;
}

export function getAuthToken(): string | null {
  return currentAuthToken;
}

/**
 * Factory for creating the configured Axios client.
 */
export function createApiClient(baseURL = getApiBaseUrl()): AxiosInstance {
  const instance = axios.create({
    baseURL,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
  });

  // Request interceptor: attach bearer token if available
  instance.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token = currentAuthToken;
      if (token && !config.headers.Authorization) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => Promise.reject(error)
  );

  // Response interceptor: normalize responses and map error types
  instance.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error: unknown) => {
      if (isCancel(error)) {
        return Promise.reject(
          new ApiError({
            message: 'Request was cancelled',
            status: 0,
            isCancelled: true,
          })
        );
      }

      if (isAxiosError(error)) {
        const status = error.response?.status ?? 0;
        const responseData = error.response?.data as { detail?: string | ApiErrorDetail[] } | undefined;
        const detail = responseData?.detail;

        let message = error.message;
        if (typeof detail === 'string') {
          message = detail;
        } else if (Array.isArray(detail) && detail.length > 0) {
          message = detail[0]?.msg || 'Validation error';
        } else if (status === 401) {
          message = 'Authentication required or invalid reviewer token.';
        } else if (status === 403) {
          message = 'Access forbidden. Reviewer role has insufficient permissions.';
        } else if (status === 404) {
          message = 'Requested resource was not found.';
        } else if (status === 422) {
          message = 'Business validation failed.';
        } else if (!error.response) {
          message = 'Unable to connect to the backend server. Please verify the service is running.';
        }

        return Promise.reject(
          new ApiError({
            message,
            status,
            detail,
            isNetworkError: !error.response,
          })
        );
      }

      return Promise.reject(
        new ApiError({
          message: error instanceof Error ? error.message : 'An unexpected error occurred',
          status: 500,
        })
      );
    }
  );

  return instance;
}

export const apiClient = createApiClient();

/**
 * Convenient typed wrapper around the Axios client.
 */
export async function apiRequest<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.request<T>(config);
  return response.data;
}
