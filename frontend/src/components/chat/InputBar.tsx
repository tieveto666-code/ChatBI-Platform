import React, { useState, useCallback } from 'react';
import { Box, IconButton, TextareaAutosize } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import StorageIcon from '@mui/icons-material/Storage';
import PsychologyIcon from '@mui/icons-material/Psychology';
import { useChatStore } from '../../stores/chatStore';

interface InputBarProps {
  onSend: (content: string) => void;
  onOpenDataSource?: () => void;
}

const InputBar: React.FC<InputBarProps> = ({ onSend, onOpenDataSource }) => {
  const [content, setContent] = useState('');
  const isStreaming = useChatStore((s) => s.isStreaming);

  const handleSend = useCallback(() => {
    const trimmed = content.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setContent('');
  }, [content, isStreaming, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Box
      sx={{
        borderTop: '1px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        px: 2.5,
        py: 1.5,
      }}
    >
      {/* Input row */}
      <Box sx={{ display: 'flex', gap: 1.25, alignItems: 'flex-end' }}>
        <TextareaAutosize
          minRows={1}
          maxRows={4}
          placeholder="输入你的数据问题..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
          style={{
            flex: 1,
            minHeight: 44,
            maxHeight: 120,
            padding: '10px 14px',
            fontSize: 14,
            fontFamily: 'inherit',
            border: '1px solid #d9d9d9',
            borderRadius: 8,
            outline: 'none',
            resize: 'none',
            backgroundColor: '#fff',
            lineHeight: 1.5,
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = '#667eea';
            e.currentTarget.style.boxShadow = '0 0 0 3px rgba(102,126,234,0.1)';
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = '#d9d9d9';
            e.currentTarget.style.boxShadow = 'none';
          }}
        />
        <IconButton
          onClick={handleSend}
          disabled={!content.trim() || isStreaming}
          sx={{
            width: 44,
            height: 44,
            bgcolor: !content.trim() || isStreaming ? 'action.disabledBackground' : '#667eea',
            color: 'white',
            borderRadius: 1.5,
            '&:hover': {
              bgcolor: '#7c93f5',
            },
            '&.Mui-disabled': {
              bgcolor: 'action.disabledBackground',
              color: 'rgba(0,0,0,0.26)',
            },
          }}
        >
          <SendIcon sx={{ fontSize: 20 }} />
        </IconButton>
      </Box>

      {/* Bottom row: data source + model selectors */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          mt: 1,
        }}
      >
        <Box
          component="span"
          onClick={onOpenDataSource}
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 0.5,
            px: 1.25,
            py: 0.5,
            borderRadius: 1,
            fontSize: 12,
            color: 'text.secondary',
            cursor: 'pointer',
            transition: 'all 0.15s',
            border: '1px solid transparent',
            '&:hover': {
              bgcolor: '#f0f2ff',
              borderColor: '#b3c2ff',
              color: '#667eea',
            },
          }}
        >
          <StorageIcon sx={{ fontSize: 14 }} />
          选择数据源
        </Box>
        <Box
          component="span"
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 0.5,
            px: 1.25,
            py: 0.5,
            borderRadius: 1,
            fontSize: 12,
            color: 'text.secondary',
            cursor: 'pointer',
            transition: 'all 0.15s',
            border: '1px solid transparent',
            '&:hover': {
              bgcolor: '#f0f2ff',
              borderColor: '#b3c2ff',
              color: '#667eea',
            },
          }}
        >
          <PsychologyIcon sx={{ fontSize: 14 }} />
          默认模型
        </Box>
      </Box>
    </Box>
  );
};

export default InputBar;
