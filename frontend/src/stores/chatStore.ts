import { create } from 'zustand';
import type { Conversation, Message } from '../types/api';
import { chatService } from '../services/chat';
import { chartPayloadToChartData, type ChartPayload } from '../utils/chartConvert';

interface ChatState {
  conversations: Conversation[];
  activeConversationId: number | null;
  messages: Record<number, Message[]>;
  isStreaming: boolean;
  setConversations: (conversations: Conversation[]) => void;
  setActiveConversation: (id: number | null) => void;
  addConversation: (conversation: Conversation) => void;
  removeConversation: (id: number) => void;
  updateConversation: (id: number, data: Partial<Conversation>) => void;
  setMessages: (conversationId: number, messages: Message[]) => void;
  updateMessage: (conversationId: number, messageId: number, updates: Partial<Message>) => void;
  addMessage: (conversationId: number, message: Message) => void;
  updateLastMessage: (conversationId: number, updates: Partial<Message>) => void;
  setIsStreaming: (isStreaming: boolean) => void;
  /** 将流式 token 追加到该对话最后一条助手消息的 content（对齐 SSE token 事件） */
  appendToken: (conversationId: number, token: string) => void;
  /** 占位对话首次落库后，用服务端 id 替换本地临时 id */
  reconcilePlaceholderConversation: (tempId: number, serverConversationId: number) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  messages: {},
  isStreaming: false,

  setConversations: (conversations) => set({ conversations }),

  setActiveConversation: (id) => {
    set({ activeConversationId: id });
    if (id && !get().messages[id]) {
      chatService.getMessages(id).then((res) => {
        set((state) => ({
          messages: { ...state.messages, [id]: (res.data?.items || []).map(hydrateMessage) },
        }));
      }).catch(() => {
        /* 本地占位 id 或会话尚未落库：保持空消息列表 */
      });
    }
  },

  addConversation: (conversation) =>
    set((state) => ({
      conversations: [conversation, ...state.conversations],
      activeConversationId: conversation.id,
    })),

  removeConversation: (id) =>
    set((state) => {
      const newMessages = { ...state.messages };
      delete newMessages[id];
      return {
        conversations: state.conversations.filter((c) => c.id !== id),
        activeConversationId: state.activeConversationId === id ? null : state.activeConversationId,
        messages: newMessages,
      };
    }),

  updateConversation: (id, data) =>
    set((state) => ({
      conversations: state.conversations.map((c) => (c.id === id ? { ...c, ...data } : c)),
    })),

  setMessages: (conversationId, messages) =>
    set((state) => ({
      messages: { ...state.messages, [conversationId]: messages.map(hydrateMessage) },
    })),

  updateMessage: (conversationId, messageId, updates) =>
    set((state) => {
      const msgs = state.messages[conversationId];
      if (!msgs?.length) return state;
      return {
        messages: {
          ...state.messages,
          [conversationId]: msgs.map((m) => (m.id === messageId ? { ...m, ...updates } : m)),
        },
      };
    }),

  addMessage: (conversationId, message) =>
    set((state) => ({
      messages: {
        ...state.messages,
        [conversationId]: [...(state.messages[conversationId] || []), message],
      },
    })),

  updateLastMessage: (conversationId, updates) =>
    set((state) => {
      const msgs = state.messages[conversationId];
      if (!msgs || msgs.length === 0) return state;
      const updated = [...msgs];
      updated[updated.length - 1] = { ...updated[updated.length - 1], ...updates };
      return { messages: { ...state.messages, [conversationId]: updated } };
    }),

  setIsStreaming: (isStreaming) => set({ isStreaming }),

  appendToken: (conversationId, token) =>
    set((state) => {
      const msgs = state.messages[conversationId];
      if (!msgs?.length) return state;
      const updated = [...msgs];
      const last = updated[updated.length - 1];
      if (last.role !== 'assistant') return state;
      updated[updated.length - 1] = { ...last, content: (last.content || '') + token };
      return { messages: { ...state.messages, [conversationId]: updated } };
    }),

  reconcilePlaceholderConversation: (tempId, serverConversationId) =>
    set((state) => {
      const newConversations = state.conversations.map((c) => {
        if (c.id !== tempId) return c;
        const { data_empty: _d, ...rest } = c as Conversation & { data_empty?: boolean };
        return { ...rest, id: serverConversationId };
      });
      const newMessages = { ...state.messages };
      if (newMessages[tempId]) {
        newMessages[serverConversationId] = newMessages[tempId].map((m) => ({
          ...m,
          conversation_id: serverConversationId,
        }));
        delete newMessages[tempId];
      }
      return {
        conversations: newConversations,
        messages: newMessages,
        activeConversationId:
          state.activeConversationId === tempId ? serverConversationId : state.activeConversationId,
      };
    }),
}));

function hydrateMessage(message: Message): Message {
  const meta = message.metadata_json;
  if (!meta) return message;
  const chartPayload = meta.chart_data as ChartPayload | undefined;
  const converted = chartPayloadToChartData(chartPayload);
  return {
    ...message,
    sql: message.sql || meta.sql,
    table_data: message.table_data || meta.table_data,
    chart_view: message.chart_view || converted.chartView,
    chart_data: message.chart_data || converted.chartData,
    chart_type: message.chart_type || meta.chart_type || converted.chartType || chartPayload?.default_type || chartPayload?.type,
  };
}
