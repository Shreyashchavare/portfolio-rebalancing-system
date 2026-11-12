import { apiRequest } from './client';
import { API_ENDPOINTS } from './endpoints';
import type { WorkflowRequest, WorkflowResponse } from '@/types/orchestration';

export const workflowService = {
  /**
   * Initiate or resume an orchestrated rebalancing workflow.
   * Calls POST /api/v1/workflows
   */
  async initiateWorkflow(request: WorkflowRequest): Promise<WorkflowResponse> {
    return apiRequest<WorkflowResponse>({
      method: 'POST',
      url: API_ENDPOINTS.WORKFLOWS,
      data: request,
    });
  },

  /**
   * Retrieve workflow execution status and results.
   * Calls GET /api/v1/workflows/{workflow_id}
   */
  async getWorkflow(workflowId: string): Promise<WorkflowResponse> {
    return apiRequest<WorkflowResponse>({
      method: 'GET',
      url: API_ENDPOINTS.WORKFLOW_BY_ID(encodeURIComponent(workflowId)),
    });
  },
};
