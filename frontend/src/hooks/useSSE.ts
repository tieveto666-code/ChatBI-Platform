import { useCallback, useRef } from 'react';
import { chatService } from '../services/chat';
import { useChatStore } from '../stores/chatStore';
import { isLikelySql } from '../utils/sqlDetect';
import { chartPayloadToChartData, type ChartPayload } from '../utils/chartConvert';
import type { TableData } from '../types/api';

interface SendMessageParams {
  /** 本地 Store 中的对话 id（用于更新 messages；占位对话时为临时 id） */
  clientConversationId: number;
  /** 发往服务端的 conversation_id；新建对话（含占位首条消息）时为 null */
  serverConversationId: number | null;
  content: string;
  dataSourceType?: 'db' | 'excel' | 'csv' | 'chat';
  dbConnectionId?: number | null;
  fileUploadId?: number | null;
  agentConfigId?: number | null;
}

interface DonePayload {
  conversation_id?: number;
  message_id?: number;
  token_usage?: unknown;
}

interface UseSSEHandlers {
  onSQL?: (sql: string) => void;
  onChart?: (chartData: string) => void;
  onTable?: (tableData: string) => void;
  onError?: (error: string) => void;
  onDone?: (payload: DonePayload) => void;
}

/** SSE table 事件：rows 可为对象数组或二维数组（与 API 规范一致） */
function normalizeTablePayload(raw: Record<string, unknown>): TableData {
  const columns = (raw.columns as string[]) || [];
  let rows = (raw.rows as unknown[]) || [];
  if (rows.length > 0 && Array.isArray(rows[0])) {
    rows = (rows as unknown[][]).map((cells) => {
      const row: Record<string, unknown> = {};
      columns.forEach((col, i) => {
        row[col] = cells[i] ?? '';
      });
      return row;
    });
  }
  return { columns, rows: rows as Record<string, unknown>[] };
}

export function useSSE() {
  const abortRef = useRef<(() => void) | null>(null);
  const { setIsStreaming, appendToken, updateLastMessage, reconcilePlaceholderConversation } =
    useChatStore();

  const sendMessage = useCallback(
    (params: SendMessageParams, handlers?: UseSSEHandlers) => {
      const {
        clientConversationId,
        serverConversationId,
        content,
        dataSourceType,
        dbConnectionId,
        fileUploadId,
        agentConfigId,
      } = params;

      setIsStreaming(true);

      const abort = chatService.chatStream(
        {
          conversation_id: serverConversationId,
          content,
          data_source_type: dataSourceType,
          db_connection_id: dbConnectionId,
          file_upload_id: fileUploadId,
          agent_config_id: agentConfigId,
        },
        (event, data) => {
          const convKey = clientConversationId;
          switch (event) {
            case 'token':
              try {
                const o = JSON.parse(data) as { text?: string };
                const text = o.text ?? '';
                if (text) appendToken(convKey, text);
              } catch {
                appendToken(convKey, data);
              }
              break;
            case 'sql':
              try {
                const o = JSON.parse(data) as { sql?: string };
                const rawSql = o.sql ?? data;
                if (isLikelySql(rawSql)) {
                  updateLastMessage(convKey, { sql: rawSql });
                } else {
                  const msgs = useChatStore.getState().messages[convKey];
                  const last = msgs?.[msgs.length - 1];
                  const merged = [last?.content?.trim(), rawSql.trim()].filter(Boolean).join('\n\n');
                  updateLastMessage(convKey, { content: merged });
                }
              } catch {
                if (isLikelySql(data)) {
                  updateLastMessage(convKey, { sql: data });
                } else {
                  updateLastMessage(convKey, { content: data });
                }
              }
              handlers?.onSQL?.(data);
              break;
            case 'chart':
              try {
                const parsed = JSON.parse(data) as ChartPayload;
                const converted = chartPayloadToChartData(parsed);
                updateLastMessage(convKey, {
                  chart_type: converted.chartType || parsed.default_type || parsed.type,
                  ...(converted.chartView ? { chart_view: converted.chartView } : {}),
                  ...(converted.chartData ? { chart_data: converted.chartData } : {}),
                });
              } catch {
                // ignore parse errors
              }
              handlers?.onChart?.(data);
              break;
            case 'table':
              try {
                const raw = JSON.parse(data) as Record<string, unknown>;
                const tableData = normalizeTablePayload(raw);
                updateLastMessage(convKey, { table_data: tableData });
              } catch {
                // ignore parse errors
              }
              handlers?.onTable?.(data);
              break;
            case 'error':
              setIsStreaming(false);
              try {
                const o = JSON.parse(data) as { message?: string };
                handlers?.onError?.(o.message ?? data);
              } catch {
                handlers?.onError?.(data);
              }
              break;
            case 'done':
              setIsStreaming(false);
              try {
                const payload = JSON.parse(data) as DonePayload;
                if (
                  payload.conversation_id != null &&
                  serverConversationId === null &&
                  payload.conversation_id !== clientConversationId
                ) {
                  reconcilePlaceholderConversation(clientConversationId, payload.conversation_id);
                }
                handlers?.onDone?.(payload);
              } catch {
                handlers?.onDone?.({});
              }
              break;
          }
        }
      );

      abortRef.current = abort;
    },
    [setIsStreaming, appendToken, updateLastMessage, reconcilePlaceholderConversation]
  );

  const cancel = useCallback(() => {
    abortRef.current?.();
    setIsStreaming(false);
  }, [setIsStreaming]);

  return { sendMessage, cancel };
}
