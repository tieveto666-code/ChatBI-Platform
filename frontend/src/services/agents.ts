import api from './api';
import type { ApiResponse } from '../types/api';

export interface WorkflowNodeConfig {
  system_prompt?: string | null;
  user_prompt_template?: string | null;
  model_provider?: string | null;
  model_name?: string | null;
  temperature?: number | null;
  max_tokens?: number | null;
}

export interface WorkflowStepMeta {
  id: string;
  kind: 'llm' | 'system';
  title: string;
  description: string;
  path: 'main' | 'other' | 'ask_data';
}

export interface WorkflowTemplate {
  steps: WorkflowStepMeta[];
  llm_nodes: string[];
  node_fields: Record<string, {
    system_prompt?: { label: string; hint?: string; placeholder?: string };
    user_prompt_template?: { label: string; hint?: string };
    fields: string[];
  }>;
  defaults: Record<string, WorkflowNodeConfig>;
}

export interface AgentConfigRow {
  id: number;
  name: string;
  description: string | null;
  system_prompt: string | null;
  workflow_config: Record<string, WorkflowNodeConfig> | null;
  synonym_map: Record<string, string> | null;
  model_provider: string;
  model_name: string | null;
  temperature: number;
  max_tokens: number;
  is_default: boolean;
  is_active: boolean;
  created_by: number | null;
  created_by_name?: string | null;
  visibility: string;
  default_data_source_type: string | null;
  default_db_connection_id: number | null;
  default_file_upload_id: number | null;
  shared_role_ids: number[];
  permission: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface DatasourceOptions {
  db_connections: { id: number; name: string; db_type: string; visibility: string }[];
  file_uploads: { id: number; original_name: string; query_db_ready: boolean; visibility: string }[];
}

export interface RoleShareOption {
  id: number;
  name: string;
  code: string;
}

export interface AgentConfigPayload {
  name: string;
  description?: string;
  system_prompt?: string;
  workflow_config?: { nodes: Record<string, WorkflowNodeConfig> };
  synonym_map?: Record<string, string>;
  model_provider?: string;
  model_name?: string;
  temperature?: number;
  max_tokens?: number;
  visibility?: string;
  default_data_source_type?: string | null;
  default_db_connection_id?: number | null;
  default_file_upload_id?: number | null;
  shared_role_ids?: number[];
}

export const agentService = {
  listAgents: () =>
    api
      .get<ApiResponse<{ items: AgentConfigRow[]; total: number }>>('/agents')
      .then((res) => res.data.data),

  getWorkflowTemplate: () =>
    api
      .get<ApiResponse<WorkflowTemplate>>('/agents/workflow-template')
      .then((res) => res.data.data),

  getDatasourceOptions: () =>
    api
      .get<ApiResponse<DatasourceOptions>>('/agents/datasource-options')
      .then((res) => res.data.data),

  getShareRoleOptions: () =>
    api
      .get<ApiResponse<RoleShareOption[]>>('/agents/share-role-options')
      .then((res) => res.data.data ?? []),

  createAgent: (payload: AgentConfigPayload) =>
    api.post<ApiResponse<AgentConfigRow>>('/agents', payload).then((res) => res.data.data),

  updateAgent: (id: number, payload: Partial<AgentConfigPayload>) =>
    api.put<ApiResponse<AgentConfigRow>>(`/agents/${id}`, payload).then((res) => res.data.data),

  deleteAgent: (id: number) =>
    api.delete<ApiResponse<{ message: string }>>(`/agents/${id}`).then((res) => res.data.data),
};
