import api from './api';
import type { ApiResponse, Conversation, Message } from '../types/api';

interface ChatMessageParams {
  /** null 表示由服务端新建对话（API 规范） */
  conversation_id?: number | null;
  content: string;
  data_source_type?: 'db' | 'excel' | 'csv' | 'chat';
  db_connection_id?: number | null;
  file_upload_id?: number | null;
  agent_config_id?: number | null;
}

export interface ChatAgentOption {
  id: number;
  name: string;
  is_default: boolean;
  model_provider: string;
  model_name: string | null;
  default_data_source_type: string | null;
  default_db_connection_id: number | null;
  default_file_upload_id: number | null;
}

export const chatService = {
  listChatAgents: () =>
    api
      .get<ApiResponse<{ items: ChatAgentOption[]; default_id: number | null }>>('/chat/agents')
      .then((r) => r.data.data),

  createConversation: (data: Partial<Conversation> & { title?: string; agent_config_id?: number | null } = {}) =>
    api.post<ApiResponse<Conversation>>('/conversations', data).then((r) => r.data),

  getConversations: (page = 1, pageSize = 20) =>
    api
      .get<ApiResponse<{ items: Conversation[]; total: number }>>('/conversations', {
        params: { page, page_size: pageSize },
      })
      .then((r) => r.data),

  deleteConversation: (id: number) =>
    api.delete<ApiResponse<null>>(`/conversations/${id}`).then((r) => r.data),

  patchConversation: (id: number, data: Partial<Conversation>) =>
    api.patch<ApiResponse<Conversation>>(`/conversations/${id}`, data).then((r) => r.data),

  getMessages: (conversationId: number) =>
    api
      .get<ApiResponse<{ items: Message[]; total: number }>>(`/conversations/${conversationId}/messages`)
      .then((r) => r.data),

  chatStream: (params: ChatMessageParams, onEvent: (event: string, data: string) => void) => {
    const token = localStorage.getItem('token');
    const url = '/api/chat/stream';

    const controller = new AbortController();

    const run = async () => {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: params.content,
          conversation_id:
            params.conversation_id === undefined || params.conversation_id === null
              ? null
              : params.conversation_id,
          data_source_type: params.data_source_type,
          db_connection_id: params.db_connection_id,
          file_upload_id: params.file_upload_id,
          agent_config_id: params.agent_config_id,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader available');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = '';
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ') && currentEvent) {
            const data = line.slice(6);
            onEvent(currentEvent, data);
            currentEvent = '';
          }
        }
      }
    };

    run().catch((err) => {
      if (err.name !== 'AbortError') {
        onEvent('error', err.message);
      }
    });

    return () => controller.abort();
  },

  executeSql: (conversationId: number, sql: string) =>
    api
      .post<ApiResponse<{
        sql: string;
        table_data: import('../types/api').TableData;
        chart_data?: import('../types/api').ChartData | null;
        chart_type?: string | null;
      }>>(`/conversations/${conversationId}/execute-sql`, { sql })
      .then((r) => r.data.data),
};
