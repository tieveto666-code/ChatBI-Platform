import React, { useRef, useEffect } from 'react';
import { Box } from '@mui/material';
import type { Message } from '../../types/api';
import MessageBubble from './MessageBubble';

interface MessageListProps {
  messages: Message[];
  streamingContent?: string;
  isStreaming?: boolean;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  streamingContent,
  isStreaming = false,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  return (
    <Box
      sx={{
        flex: 1,
        overflow: 'auto',
        py: 2,
      }}
    >
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {isStreaming && streamingContent && (
        <MessageBubble
          message={{
            id: -1,
            conversation_id: messages[0]?.conversation_id || 0,
            role: 'assistant',
            content: streamingContent,
            created_at: new Date().toISOString(),
          }}
          isStreaming
        />
      )}

      <div ref={bottomRef} />
    </Box>
  );
};

export default MessageList;
