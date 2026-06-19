import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Box, Typography, Snackbar, Alert, Select, MenuItem, FormControl } from '@mui/material';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';
import { keyframes } from '@emotion/react';
import SearchIcon from '@mui/icons-material/Search';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.min.css';
import { useChatStore } from '../stores/chatStore';
import { chatService, type ChatAgentOption } from '../services/chat';
import { useSSE } from '../hooks/useSSE';
import type { Message } from '../types/api';
import type { Conversation } from '../types/api';
import ChartContainer from '../components/chart/ChartContainer';
import DataTable from '../components/chart/DataTable';
import SqlViewLink from '../components/chat/SqlViewLink';
import { resolveAssistantContent } from '../utils/sqlDetect';
import { getVisualChartTypes } from '../utils/chartConvert';

const TITLE_MAX_STORE = 128;
const CHAT_INPUT_MAX_WIDTH = 1240;
const CHAT_AVATAR_OFFSET = 46;
const CHAT_MESSAGE_RAIL_WIDTH = CHAT_INPUT_MAX_WIDTH + CHAT_AVATAR_OFFSET * 2;

/** 与会话标题存储上限一致（见后端 conversations.title） */
function truncateConversationTitle(text: string, max = TITLE_MAX_STORE): string {
  const t = text.trim().replace(/\n/g, ' ');
  if (t.length <= max) return t;
  return t.slice(0, max);
}

type SourcePayload = {
  dataSourceType?: 'db' | 'excel' | 'csv' | 'chat';
  dbConnectionId: number | null;
  fileUploadId: number | null;
};

/* ─── Typing dot animation ─── */
const pulse = keyframes`
  0%, 60%, 100% { opacity: 0.3; }
  30% { opacity: 1; }
`;

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diff = now - date;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 7) return `${days}天前`;
  return new Date(dateStr).toLocaleDateString('zh-CN');
}

/* ─── Avatar colors ─── */
const AI_AVATAR_BG = '#52c41a';
const USER_AVATAR_BG = '#667eea';

const ChatPage: React.FC = () => {
  const { sendMessage } = useSSE();
  const {
    conversations,
    activeConversationId,
    messages,
    isStreaming,
    setConversations,
    setActiveConversation,
    addConversation,
    removeConversation,
    updateConversation,
    addMessage,
  } = useChatStore();

  // --- Sidebar state ---
  const [searchTerm, setSearchTerm] = useState('');
  const [menuConvId, setMenuConvId] = useState<number | null>(null);
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [renameConvId, setRenameConvId] = useState<number | null>(null);
  const [renameText, setRenameText] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteConvId, setDeleteConvId] = useState<number | null>(null);

  // --- Input area state ---
  const [inputContent, setInputContent] = useState('');
  const [chatAgents, setChatAgents] = useState<ChatAgentOption[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<number | ''>('');

  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string }>({ open: false, message: '' });

  const showSnackbar = useCallback((message: string) => {
    setSnackbar({ open: true, message });
  }, []);

  const resolvePayloadSource = useCallback(
    (conv: Conversation | undefined) => {
      const convHasDb = conv?.data_source_type === 'db' && conv.db_connection_id != null;
      const convHasFile =
        (conv?.data_source_type === 'excel' || conv?.data_source_type === 'csv') &&
        conv.file_upload_id != null;
      const convHasSource = convHasDb || convHasFile;
      const dataSourceType = convHasSource ? conv?.data_source_type : conv?.data_source_type;
      const dbConnectionId = convHasSource ? conv?.db_connection_id ?? null : null;
      const fileUploadId = convHasSource ? conv?.file_upload_id ?? null : null;
      return { dataSourceType, dbConnectionId, fileUploadId };
    },
    []
  );

  const isStreamPayloadValid = useCallback(
    (src: SourcePayload) => {
      const dst = src.dataSourceType;
      if (!dst || dst === 'chat') return false;
      if (dst === 'db') return src.dbConnectionId != null;
      if (dst === 'excel' || dst === 'csv') return src.fileUploadId != null;
      return false;
    },
    []
  );

  const selectedAgent = useMemo(
    () => chatAgents.find((a) => a.id === selectedAgentId),
    [chatAgents, selectedAgentId]
  );

  const resolvePayloadWithAgent = useCallback(
    (conv: Conversation | undefined, agent: ChatAgentOption | undefined): SourcePayload => {
      if (agent?.default_data_source_type === 'db' && agent.default_db_connection_id != null) {
        return {
          dataSourceType: 'db',
          dbConnectionId: agent.default_db_connection_id,
          fileUploadId: null,
        };
      }
      if (
        (agent?.default_data_source_type === 'excel' || agent?.default_data_source_type === 'csv') &&
        agent.default_file_upload_id != null
      ) {
        return {
          dataSourceType: agent.default_data_source_type,
          dbConnectionId: null,
          fileUploadId: agent.default_file_upload_id,
        };
      }

      const base = resolvePayloadSource(conv);
      if (isStreamPayloadValid(base)) {
        return {
          dataSourceType: base.dataSourceType,
          dbConnectionId: base.dbConnectionId ?? null,
          fileUploadId: base.fileUploadId ?? null,
        };
      }
      return {
        dataSourceType: 'chat',
        dbConnectionId: null,
        fileUploadId: null,
      };
    },
    [resolvePayloadSource, isStreamPayloadValid]
  );

  // --- Scroll ref ---
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Load conversations on mount（不自动选中任一会话，主区域保持空）
  useEffect(() => {
    chatService.getConversations().then((res) => {
      setConversations(res.data?.items || []);
    });
  }, [setConversations]);

  useEffect(() => {
    chatService
      .listChatAgents()
      .then((data) => {
        const items = data?.items ?? [];
        setChatAgents(items);
        if (data?.default_id != null) {
          setSelectedAgentId(data.default_id);
        } else if (items.length > 0) {
          setSelectedAgentId(items[0].id);
        }
      })
      .catch(() => {
        showSnackbar('加载智能体列表失败');
      });
  }, [showSnackbar]);

  useEffect(() => {
    if (!activeConversationId) return;
    const conv = conversations.find((c) => c.id === activeConversationId);
    if (conv?.agent_config_id != null) {
      setSelectedAgentId(conv.agent_config_id);
    }
  }, [activeConversationId, conversations]);

  // --- Conversation handlers ---
  const handleNewChat = useCallback(async () => {
    const hasEmpty = conversations.some((c) => (c as Conversation & { data_empty?: boolean }).data_empty);
    if (hasEmpty) return;

    const tempConv: Conversation & { data_empty?: boolean } = {
      id: Date.now(),
      title: '新对话',
      model: '',
      message_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      data_empty: true,
    };
    addConversation(tempConv);
  }, [addConversation, conversations]);

  /* ─── Context menu (inline popup) ─── */
  const [showMenu, setShowMenu] = useState(false);
  const [menuPos, setMenuPos] = useState({ top: 0, right: 0 });

  const handleOpenMenu = useCallback(
    (e: React.MouseEvent, convId: number) => {
      e.stopPropagation();
      const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
      setMenuPos({ top: rect.bottom + 4, right: window.innerWidth - rect.right });
      setMenuConvId(convId);
      setShowMenu(true);
    },
    []
  );

  const handleCloseMenu = useCallback(() => {
    setShowMenu(false);
    setMenuConvId(null);
  }, []);

  const handleOpenRename = useCallback(() => {
    const conv = conversations.find((c) => c.id === menuConvId);
    if (conv) setRenameText(conv.title || '');
    setRenameConvId(menuConvId);
    setRenameDialogOpen(true);
    handleCloseMenu();
  }, [conversations, menuConvId, handleCloseMenu]);

  const handleConfirmRename = useCallback(async () => {
    if (!renameConvId || !renameText.trim()) return;
    const safe = truncateConversationTitle(renameText.trim());
    try {
      await chatService.patchConversation(renameConvId, { title: safe });
      updateConversation(renameConvId, { title: safe });
    } catch { /* silent */ }
    setRenameDialogOpen(false);
    setRenameConvId(null);
  }, [renameConvId, renameText, updateConversation]);

  const handleOpenDelete = useCallback(() => {
    setDeleteConvId(menuConvId);
    setDeleteDialogOpen(true);
    handleCloseMenu();
  }, [menuConvId, handleCloseMenu]);

  const handleConfirmDelete = useCallback(async () => {
    if (!deleteConvId) return;
    try {
      await chatService.deleteConversation(deleteConvId);
      removeConversation(deleteConvId);
    } catch { /* silent */ }
    setDeleteDialogOpen(false);
    setDeleteConvId(null);
  }, [deleteConvId, removeConversation]);

  // --- Send handler ---
  const handleSend = useCallback(
    async (content: string) => {
      if (selectedAgentId === '') {
        showSnackbar('请先选择智能体');
        return;
      }

      let convId = activeConversationId;
      let conv: Conversation | undefined;

      const agentPayload = resolvePayloadWithAgent(undefined, selectedAgent);
      const hasAgentSource = isStreamPayloadValid(agentPayload);

      if (!convId) {
        const res = await chatService.createConversation({
          title: truncateConversationTitle(content),
          data_source_type: hasAgentSource ? agentPayload.dataSourceType : 'chat',
          db_connection_id: hasAgentSource ? agentPayload.dbConnectionId : null,
          file_upload_id: hasAgentSource ? agentPayload.fileUploadId : null,
          agent_config_id: Number(selectedAgentId),
        });
        addConversation(res.data);
        convId = res.data.id;
        conv = res.data;
      } else {
        conv = conversations.find((c) => c.id === convId);
      }

      const isPlaceholder = !!(conv && (conv as Conversation & { data_empty?: boolean }).data_empty);
      const serverConversationId = isPlaceholder ? null : convId;
      const streamSrc = resolvePayloadWithAgent(conv, selectedAgent);
      const hasStreamSource = isStreamPayloadValid(streamSrc);
      const normalizedStreamSrc = hasStreamSource
        ? streamSrc
        : {
            dataSourceType: 'chat' as const,
            dbConnectionId: null,
            fileUploadId: null,
          };

      const userMsg: Message = {
        id: Date.now(),
        conversation_id: convId,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      };

      const assistantMsg: Message = {
        id: Date.now() + 1,
        conversation_id: convId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
      };

      addMessage(convId, userMsg);
      addMessage(convId, assistantMsg);

      const titleFromFirst = truncateConversationTitle(content);

      sendMessage(
        {
          clientConversationId: convId,
          serverConversationId,
          content,
          dataSourceType: normalizedStreamSrc.dataSourceType,
          dbConnectionId: normalizedStreamSrc.dbConnectionId,
          fileUploadId: normalizedStreamSrc.fileUploadId,
          agentConfigId: Number(selectedAgentId),
        },
        {
          onError: (msg) => {
            showSnackbar(msg || '对话请求失败，请稍后重试');
          },
          onDone: (payload) => {
            if (!isPlaceholder || payload.conversation_id == null) return;
            updateConversation(payload.conversation_id, { title: titleFromFirst });
          },
        }
      );
    },
    [
      activeConversationId,
      addConversation,
      addMessage,
      sendMessage,
      resolvePayloadWithAgent,
      isStreamPayloadValid,
      showSnackbar,
      conversations,
      updateConversation,
      selectedAgentId,
      selectedAgent,
    ]
  );

  const handleInputSend = useCallback(() => {
    const trimmed = inputContent.trim();
    if (!trimmed || isStreaming) return;
    handleSend(trimmed);
    setInputContent('');
  }, [inputContent, isStreaming, handleSend]);

  const handleInputKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleInputSend();
      }
    },
    [handleInputSend]
  );

  // --- Filtered conversations ---
  const filteredConversations = conversations.filter((c) =>
    c.title?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const currentMessages = activeConversationId ? messages[activeConversationId] || [] : [];

  /* ════════════════ Render Helpers ════════════════ */

  const isPendingAssistantMessage = (msg: Message) =>
    msg.role === 'assistant' &&
    !msg.content &&
    !msg.sql &&
    !msg.table_data &&
    !msg.chart_data &&
    !msg.chart_view;

  const renderMessage = (msg: Message, idx: number) => {
    if (isStreaming && isPendingAssistantMessage(msg)) {
      return renderTyping(msg.id || idx);
    }
    const isUser = msg.role === 'user';
    const { markdown, sql: displaySql } = isUser
      ? { markdown: msg.content, sql: null as string | null }
      : resolveAssistantContent(msg);
	    return (
	      <Box
	        key={msg.id || idx}
	        className="msg"
	        sx={{
	          maxWidth: isUser ? '68%' : '82%',
	          display: 'flex',
	          gap: 1.5,
	          alignSelf: isUser ? 'flex-end' : 'flex-start',
	          flexDirection: isUser ? 'row-reverse' : 'row',
	        }}
      >
        {/* Avatar */}
        <Box
	          sx={{
	            width: 34,
	            height: 34,
	            borderRadius: '50%',
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 13,
            color: '#fff',
            fontWeight: 500,
	            bgcolor: isUser ? USER_AVATAR_BG : AI_AVATAR_BG,
	            boxShadow: '0 6px 16px rgba(15,23,42,0.12)',
	          }}
	        >
          {isUser ? '管' : 'AI'}
        </Box>

        {/* Bubble */}
        <Box
	          sx={{
	            px: 2,
	            py: 1.5,
	            borderRadius: 2,
	            fontSize: 14,
	            lineHeight: 1.6,
            ...(isUser
              ? {
	                  bgcolor: '#667eea',
	                  color: '#fff',
	                  borderBottomRightRadius: 0.75,
	                  boxShadow: '0 10px 24px rgba(102,126,234,0.18)',
	                }
	              : {
	                  bgcolor: '#fff',
	                  color: '#1a1a2e',
	                  border: '1px solid #e4e8f0',
	                  borderBottomLeftRadius: 0.75,
	                  boxShadow: '0 10px 28px rgba(15,23,42,0.07)',
	                }),
	          }}
	        >
          {isUser ? (
            <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
          ) : (
            <>
	              <Box
	                sx={{
	                  '& p': { m: 0, mb: 1 },
	                  '& p:last-child': { mb: 0 },
	                  '& pre': {
	                    borderRadius: 1.25,
	                    p: 1.5,
	                    overflow: 'auto',
	                    bgcolor: '#fff',
	                    border: '1px solid #e4e8f0',
	                    m: 0,
	                    mb: 1,
	                  },
	                  '& pre code.hljs': {
	                    bgcolor: 'transparent',
	                    p: 0,
	                    fontSize: 13,
	                    color: '#24292e',
	                  },
	                  '& :not(pre) > code': {
	                    bgcolor: '#f1f5f9',
	                    color: '#334155',
	                    px: 0.75,
	                    py: 0.25,
	                    borderRadius: 0.75,
	                    fontSize: '0.92em',
	                  },
	                  '& code': {
	                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
	                  },
	                }}
	              >
	                <ReactMarkdown rehypePlugins={[rehypeHighlight]}>{markdown || ''}</ReactMarkdown>
	              </Box>
              {displaySql && <SqlViewLink sql={displaySql} />}
              {msg.chart_view && (getVisualChartTypes(msg.chart_view.availableTypes).length > 0 || msg.chart_view.availableTypes.includes('table')) ? (
                <ChartContainer
                  chartView={msg.chart_view}
                  chartType={msg.chart_type}
                  tableData={msg.table_data}
                />
              ) : msg.table_data ? (
                <DataTable data={msg.table_data} />
              ) : null}
            </>
          )}
        </Box>
      </Box>
    );
  };

  const renderTyping = (key: React.Key = 'typing') => (
    <Box
      key={key}
      className="msg ai"
      sx={{
        maxWidth: '82%',
        display: 'flex',
        gap: 1.5,
        alignSelf: 'flex-start',
      }}
    >
      <Box
        sx={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 13,
          color: '#fff',
          fontWeight: 500,
          bgcolor: AI_AVATAR_BG,
          boxShadow: '0 6px 16px rgba(15,23,42,0.12)',
        }}
      >
        AI
      </Box>
      <Box
        sx={{
          px: 2,
          py: 1.5,
          borderRadius: 2,
          borderBottomLeftRadius: 0.75,
          bgcolor: '#fff',
          border: '1px solid #e4e8f0',
          boxShadow: '0 10px 28px rgba(15,23,42,0.07)',
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          color: '#7b8496',
          fontSize: 13,
        }}
      >
        <Box component="span">AI 正在思考</Box>
        <Box sx={{ display: 'flex', gap: 0.5 }}>
          {[0, 1, 2].map((i) => (
            <Box
              key={i}
              sx={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                bgcolor: '#9aaaf7',
                animation: `${pulse} 1.2s infinite`,
                animationDelay: `${i * 0.2}s`,
              }}
            />
          ))}
        </Box>
      </Box>
    </Box>
  );

  /* ════════════════ Main Render ════════════════ */

  return (
    <Box sx={{ display: 'flex', height: '100%', bgcolor: '#f6f8fb' }} onClick={() => showMenu && handleCloseMenu()}>
      {/* ====== Sidebar ====== */}
      <Box
        sx={{
          width: 272,
          borderRight: '1px solid #e4e8f0',
          bgcolor: '#f8fafc',
          display: 'flex',
          flexDirection: 'column',
          flexShrink: 0,
          boxShadow: '1px 0 0 rgba(15,23,42,0.02)',
        }}
      >
        {/* Header */}
        <Box sx={{ px: 1.5, pt: 1.5, pb: 1 }}>
          <Box
            component="button"
            onClick={handleNewChat}
            sx={{
              width: '100%',
              height: 40,
              bgcolor: '#667eea',
              color: '#fff',
              border: 'none',
              borderRadius: 1.25,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 0.75,
              fontSize: 14,
              fontWeight: 600,
              lineHeight: 1,
              fontFamily: 'inherit',
              boxShadow: '0 8px 18px rgba(102,126,234,0.22)',
              transition: 'all 0.18s',
              '&:hover': { bgcolor: '#7c93f5', transform: 'translateY(-1px)' },
            }}
          >
            <Box component="span" sx={{ fontSize: 18, lineHeight: 1 }}>+</Box>
            新建会话
          </Box>
        </Box>

        {/* Search */}
        <Box sx={{ px: 1.5, pb: 1.25 }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              px: 1.5,
              py: 0.75,
              border: '1px solid #dde3ee',
              borderRadius: 1.25,
              bgcolor: '#fff',
              boxShadow: '0 1px 2px rgba(15,23,42,0.04)',
              transition: 'all 0.2s',
              '&:focus-within': {
                borderColor: '#667eea',
                boxShadow: '0 0 0 3px rgba(102,126,234,0.12)',
              },
            }}
          >
            <SearchIcon sx={{ fontSize: 16, color: '#bbb', flexShrink: 0 }} />
            <Box
              component="input"
              placeholder="搜索对话..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              sx={{
                border: 'none',
                outline: 'none',
                fontSize: 12,
                fontFamily: 'inherit',
                width: '100%',
                bgcolor: 'transparent',
                '&::placeholder': { color: '#bbb' },
              }}
            />
          </Box>
        </Box>

        {/* Conversation list */}
        <Box sx={{ flex: 1, overflow: 'auto', px: 1.5, pb: 1.5 }}>
          {filteredConversations.map((conv) => {
            const isActive = activeConversationId === conv.id;
            return (
              <Box
                key={conv.id}
                onClick={() => setActiveConversation(conv.id)}
                sx={{
                  px: 1.5,
                  py: 1.25,
                  borderRadius: 1.25,
                  cursor: 'pointer',
                  fontSize: 13,
                  mb: 0.5,
                  display: 'flex',
                  alignItems: 'center',
                  position: 'relative',
                  bgcolor: isActive ? '#eef2ff' : '#fff',
                  color: isActive ? '#4f61d8' : '#1a1a2e',
                  fontWeight: isActive ? 500 : 400,
                  border: `1px solid ${isActive ? '#c7d2fe' : 'transparent'}`,
                  boxShadow: isActive ? '0 6px 16px rgba(102,126,234,0.12)' : 'none',
                  transition: 'all 0.16s',
                  '&:hover': {
                    bgcolor: isActive ? '#eef2ff' : '#fff',
                    borderColor: '#dbe2f0',
                    boxShadow: '0 6px 14px rgba(15,23,42,0.06)',
                  },
                }}
              >
                {/* Text content */}
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box
                    sx={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      fontSize: 13,
                      fontWeight: isActive ? 500 : 400,
                    }}
                  >
                    {conv.title || `对话 ${conv.id}`}
                  </Box>
                  <Box sx={{ fontSize: 11, color: '#bbb', mt: 0.25 }}>
                    {formatRelativeTime(conv.updated_at || conv.created_at)}
                  </Box>
                </Box>

                {/* More button — ⋯ shown on hover */}
                <Box
                  component="button"
                  onClick={(e) => handleOpenMenu(e, conv.id)}
                  sx={{
                    display: 'none',
                    width: 24,
                    height: 24,
                    border: 'none',
                    borderRadius: 1,
                    bgcolor: 'transparent',
                    cursor: 'pointer',
                    fontSize: 14,
                    color: '#999',
                    flexShrink: 0,
                    ml: 0.25,
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontFamily: 'inherit',
                    lineHeight: 1,
                    '&:hover': { bgcolor: '#dde0ff', color: '#667eea' },
                    ['.MuiBox-root:hover &']: { display: 'flex' },
                  }}
                >
                  ⋯
                </Box>
              </Box>
            );
          })}

          {filteredConversations.length === 0 && (
            <Box sx={{ p: 2.5, textAlign: 'center', fontSize: 12, color: '#bbb' }}>
              {searchTerm ? '无匹配的对话' : '暂无对话，点击“新建会话”开始'}
            </Box>
          )}
        </Box>
      </Box>

      {/* ====== Main Chat Area ====== */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Messages area */}
        {currentMessages.length === 0 && !isStreaming ? (
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 1,
              px: 3,
              bgcolor: '#f6f8fb',
            }}
          >
            <Typography variant="h4" sx={{ color: '#1a1a2e', fontWeight: 700, letterSpacing: 0 }}>
              ChatBI
            </Typography>
            <Typography variant="body1" sx={{ color: '#7b8496' }}>
              输入问题开始对话，系统会自动识别问数或普通问答
            </Typography>
          </Box>
        ) : (
          <Box
            className="chat-messages"
            sx={{
              flex: 1,
              overflowY: 'auto',
              px: { xs: 2.5, md: 3.5 },
              py: 4,
              display: 'flex',
              flexDirection: 'column',
              gap: 2.5,
              bgcolor: '#f6f8fb',
              width: '100%',
              maxWidth: CHAT_MESSAGE_RAIL_WIDTH,
              mx: 'auto',
              scrollbarWidth: 'none',
              msOverflowStyle: 'none',
              '&::-webkit-scrollbar': { display: 'none' },
            }}
          >
            {currentMessages.map((msg, idx) => renderMessage(msg, idx))}

            <div ref={messagesEndRef} />
          </Box>
        )}

        {/* ====== Input Area ====== */}
        <Box
          sx={{
            px: { xs: 2.5, md: 3.5 },
            pt: 1.5,
            pb: 2,
            bgcolor: '#f6f8fb',
            flexShrink: 0,
          }}
        >
          <Box sx={{ maxWidth: CHAT_MESSAGE_RAIL_WIDTH, width: '100%', mx: 'auto' }}>
            <Box
              sx={{
                display: 'flex',
                gap: 1,
                alignItems: 'center',
                ml: `${CHAT_AVATAR_OFFSET}px`,
                mr: `${CHAT_AVATAR_OFFSET}px`,
                p: 1,
                border: '1px solid #dde3ee',
                borderRadius: 2,
                bgcolor: '#fff',
                boxShadow: '0 12px 36px rgba(15,23,42,0.08)',
                transition: 'all 0.2s',
                '&:focus-within': {
                  borderColor: '#9aaaf7',
                  boxShadow: '0 16px 42px rgba(102,126,234,0.15)',
                },
              }}
            >
            <FormControl
              size="small"
              sx={{
                flexShrink: 0,
                minWidth: 148,
                maxWidth: 200,
                '& .MuiOutlinedInput-root': {
                  borderRadius: 1.5,
                  fontSize: 13,
                  height: 40,
                  bgcolor: '#f8faff',
                  '& fieldset': { borderColor: '#e8ecf4' },
                  '&:hover fieldset': { borderColor: '#c7d2fe' },
                  '&.Mui-focused fieldset': { borderColor: '#667eea' },
                },
                '& .MuiSelect-select': {
                  display: 'flex',
                  alignItems: 'center',
                  py: 0,
                },
              }}
            >
              <Select
                value={selectedAgentId === '' ? '' : selectedAgentId}
                displayEmpty
                disabled={isStreaming || chatAgents.length === 0}
                onChange={(e) => setSelectedAgentId(Number(e.target.value))}
                renderValue={(value) => {
                  const agent = chatAgents.find((a) => a.id === value);
                  if (!agent) return '选择智能体';
                  return (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, overflow: 'hidden' }}>
                      <SmartToyOutlinedIcon sx={{ fontSize: 16, color: '#667eea', flexShrink: 0 }} />
                      <Typography
                        component="span"
                        sx={{
                          fontSize: 13,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {agent.name}
                      </Typography>
                    </Box>
                  );
                }}
                MenuProps={{ PaperProps: { sx: { maxHeight: 280 } } }}
              >
                {chatAgents.map((agent) => (
                  <MenuItem key={agent.id} value={agent.id} sx={{ fontSize: 13 }}>
                    {agent.name}
                    {agent.is_default ? '（系统内置）' : ''}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Box
              component="textarea"
              placeholder="输入你的问题..."
              rows={1}
              value={inputContent}
              onChange={(e) => setInputContent(e.target.value)}
              onKeyDown={handleInputKeyDown}
              disabled={isStreaming}
              sx={{
                flex: 1,
                border: 'none',
                borderRadius: 1.5,
                px: '12px',
                py: 0,
                fontSize: 14,
                outline: 'none',
                resize: 'none',
                height: 40,
                minHeight: 40,
                maxHeight: 120,
                fontFamily: 'inherit',
                lineHeight: '40px',
                bgcolor: '#fff',
                transition: 'background 0.2s',
                boxSizing: 'border-box',
                '&::placeholder': {
                  lineHeight: '40px',
                  opacity: 0.55,
                },
                '&:focus': { bgcolor: '#fff' },
                '&:disabled': { bgcolor: '#f5f5f5', cursor: 'not-allowed' },
              }}
            />
            <Box
              component="button"
              onClick={handleInputSend}
              disabled={!inputContent.trim() || isStreaming}
              sx={{
                width: 40,
                height: 40,
                flexShrink: 0,
                bgcolor: !inputContent.trim() || isStreaming ? '#d9d9d9' : '#667eea',
                color: !inputContent.trim() || isStreaming ? 'rgba(0,0,0,0.26)' : '#fff',
                border: 'none',
                borderRadius: 1.5,
                cursor: !inputContent.trim() || isStreaming ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 18,
                fontFamily: 'inherit',
                lineHeight: 1,
                transition: 'background 0.15s',
                boxShadow: !inputContent.trim() || isStreaming ? 'none' : '0 8px 18px rgba(102,126,234,0.24)',
                '&:hover:not(:disabled)': { bgcolor: '#7c93f5', transform: 'translateY(-1px)' },
              }}
            >
              ➤
            </Box>
          </Box>
          </Box>
        </Box>
      </Box>

      {/* ====== Inline Context Menu ====== */}
      {showMenu && (
        <>
          <Box
            onClick={handleCloseMenu}
            sx={{ position: 'fixed', inset: 0, zIndex: 999 }}
          />
          <Box
            sx={{
              position: 'fixed',
              top: menuPos.top,
              right: menuPos.right,
              bgcolor: '#fff',
              borderRadius: 1,
              boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
              minWidth: 120,
              p: 0.5,
              zIndex: 1000,
            }}
          >
            <Box
              onClick={handleOpenRename}
              sx={{
                px: 1.5,
                py: 1,
                fontSize: 13,
                color: '#555',
                cursor: 'pointer',
                borderRadius: 0.5,
                display: 'flex',
                alignItems: 'center',
                gap: 0.75,
                '&:hover': { bgcolor: '#f0f2ff', color: '#667eea' },
              }}
            >
              ✏️ 重命名
            </Box>
            <Box
              onClick={handleOpenDelete}
              sx={{
                px: 1.5,
                py: 1,
                fontSize: 13,
                color: '#ff4d4f',
                cursor: 'pointer',
                borderRadius: 0.5,
                display: 'flex',
                alignItems: 'center',
                gap: 0.75,
                '&:hover': { bgcolor: '#fff2f0', color: '#ff4d4f' },
              }}
            >
              🗑️ 删除
            </Box>
          </Box>
        </>
      )}

      {/* ====== Rename Dialog ====== */}
      {renameDialogOpen && (
        <>
          <Box
            onClick={() => {
              setRenameDialogOpen(false);
              setRenameConvId(null);
            }}
            sx={{ position: 'fixed', inset: 0, bgcolor: 'rgba(0,0,0,0.35)', zIndex: 1100 }}
          />
          <Box
            sx={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              bgcolor: '#fff',
              borderRadius: 2,
              boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
              width: 420,
              zIndex: 1101,
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <Box sx={{ px: 2.5, py: 2, borderBottom: '1px solid #e8e8e8' }}>
              <Typography variant="subtitle1" sx={{ fontSize: 16, fontWeight: 600 }}>重命名对话</Typography>
            </Box>
            <Box sx={{ px: 2.5, py: 2 }}>
              <Box
                component="input"
                autoFocus
                value={renameText}
                onChange={(e) => setRenameText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') { e.preventDefault(); handleConfirmRename(); }
                }}
                sx={{
                  width: '100%',
                  p: '8px 12px',
                  border: '1px solid #d9d9d9',
                  borderRadius: 1,
                  fontSize: 13,
                  outline: 'none',
                  fontFamily: 'inherit',
                  '&:focus': { borderColor: '#667eea', boxShadow: '0 0 0 2px rgba(102,126,234,0.1)' },
                }}
              />
            </Box>
            <Box sx={{ px: 2.5, py: 1.5, borderTop: '1px solid #e8e8e8', display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
              <Box
                component="button"
                onClick={() => {
                  setRenameDialogOpen(false);
                  setRenameConvId(null);
                }}
                sx={{
                  px: 1.5,
                  py: 0.75,
                  border: '1px solid #d9d9d9',
                  borderRadius: 1,
                  bgcolor: '#fff',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontFamily: 'inherit',
                  color: '#555',
                  '&:hover': { borderColor: '#667eea', color: '#667eea' },
                }}
              >
                取消
              </Box>
              <Box
                component="button"
                onClick={handleConfirmRename}
                sx={{
                  px: 1.5,
                  py: 0.75,
                  border: 'none',
                  borderRadius: 1,
                  bgcolor: '#667eea',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontFamily: 'inherit',
                  color: '#fff',
                  '&:hover': { bgcolor: '#7c93f5' },
                }}
              >
                确认
              </Box>
            </Box>
          </Box>
        </>
      )}

      {/* ====== Delete Confirm Dialog ====== */}
      {deleteDialogOpen && (
        <>
          <Box
            onClick={() => setDeleteDialogOpen(false)}
            sx={{ position: 'fixed', inset: 0, bgcolor: 'rgba(0,0,0,0.35)', zIndex: 1100 }}
          />
          <Box
            sx={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              bgcolor: '#fff',
              borderRadius: 2,
              boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
              width: 420,
              zIndex: 1101,
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <Box sx={{ px: 2.5, py: 2, borderBottom: '1px solid #e8e8e8' }}>
              <Typography variant="subtitle1" sx={{ fontSize: 16, fontWeight: 600 }}>确认删除</Typography>
            </Box>
            <Box sx={{ px: 2.5, py: 2 }}>
              <Typography variant="body2" sx={{ color: '#555', fontSize: 14 }}>
                确认删除此对话？此操作不可恢复。
              </Typography>
            </Box>
            <Box sx={{ px: 2.5, py: 1.5, borderTop: '1px solid #e8e8e8', display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
              <Box
                component="button"
                onClick={() => setDeleteDialogOpen(false)}
                sx={{
                  px: 1.5,
                  py: 0.75,
                  border: '1px solid #d9d9d9',
                  borderRadius: 1,
                  bgcolor: '#fff',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontFamily: 'inherit',
                  color: '#555',
                  '&:hover': { borderColor: '#667eea', color: '#667eea' },
                }}
              >
                取消
              </Box>
              <Box
                component="button"
                onClick={handleConfirmDelete}
                sx={{
                  px: 1.5,
                  py: 0.75,
                  border: 'none',
                  borderRadius: 1,
                  bgcolor: '#ff4d4f',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontFamily: 'inherit',
                  color: '#fff',
                  '&:hover': { bgcolor: '#ff7875' },
                }}
              >
                删除
              </Box>
            </Box>
          </Box>
        </>
      )}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity="error"
          variant="filled"
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ChatPage;
