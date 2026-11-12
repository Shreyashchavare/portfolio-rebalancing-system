import { apiRequest } from './client';
import { API_ENDPOINTS } from './endpoints';
import type {
  PolicySearchRequest,
  PolicySearchResponse,
  PolicyAskRequest,
  PolicyAskResponse,
} from '@/types/policies';

export const policyService = {
  /**
   * Search policy documents semantically.
   * Calls POST /api/v1/policies/search
   */
  async search(request: PolicySearchRequest): Promise<PolicySearchResponse> {
    return apiRequest<PolicySearchResponse>({
      method: 'POST',
      url: API_ENDPOINTS.POLICY_SEARCH,
      data: request,
    });
  },

  /**
   * Query policy Q&A grounded in ingested documents.
   * Calls POST /api/v1/policies/ask
   */
  async ask(request: PolicyAskRequest): Promise<PolicyAskResponse> {
    return apiRequest<PolicyAskResponse>({
      method: 'POST',
      url: API_ENDPOINTS.POLICY_ASK,
      data: request,
    });
  },
};
