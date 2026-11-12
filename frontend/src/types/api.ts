/**
 * Standard API error structure mirroring FastAPI's HTTPException and RequestValidationError.
 */
export interface ApiErrorDetail {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
}

export class ApiError extends Error {
  public status: number;
  public detail: string | ApiErrorDetail[];
  public isNetworkError: boolean;
  public isCancelled: boolean;

  constructor(params: {
    message: string;
    status: number;
    detail?: string | ApiErrorDetail[];
    isNetworkError?: boolean;
    isCancelled?: boolean;
  }) {
    super(params.message);
    this.name = 'ApiError';
    this.status = params.status;
    this.detail = params.detail || params.message;
    this.isNetworkError = params.isNetworkError || false;
    this.isCancelled = params.isCancelled || false;
  }

  get userMessage(): string {
    if (typeof this.detail === 'string') {
      return this.detail;
    }
    if (Array.isArray(this.detail) && this.detail.length > 0) {
      const first = this.detail[0];
      return first?.msg || this.message;
    }
    return this.message;
  }
}

export interface HealthResponse {
  status: 'healthy' | 'unhealthy' | string;
}
