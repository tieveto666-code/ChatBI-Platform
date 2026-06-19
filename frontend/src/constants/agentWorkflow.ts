import type { WorkflowNodeConfig, WorkflowTemplate } from '../services/agents';

/** 生产环境支持的 LLM 提供商（问数由智能体 / 工作流节点配置决定） */
export const PROVIDER_OPTIONS = [
  { value: 'deepseek', label: 'DeepSeek' },
] as const;

export type WorkflowNodesState = Record<string, WorkflowNodeConfig>;

export function emptyWorkflowFromTemplate(template: WorkflowTemplate | null): WorkflowNodesState {
  return (template?.defaults as WorkflowNodesState) ?? {};
}

export function workflowPayload(nodes: WorkflowNodesState) {
  return { nodes };
}
