import React from 'react';
import { Box, Typography, Avatar } from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import type { Message } from '../../types/api';
import TypingEffect from './TypingEffect';
import SQLBlock from './SQLBlock';
import ChartContainer from '../chart/ChartContainer';
import DataTable from '../chart/DataTable';

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isStreaming }) => {
  const isUser = message.role === 'user';

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: isUser ? 'row-reverse' : 'row',
        gap: 1.5,
        mb: 2,
        px: 2,
      }}
    >
      <Avatar
        sx={{
          width: 36,
          height: 36,
          bgcolor: isUser ? 'primary.main' : 'secondary.main',
        }}
      >
        {isUser ? <PersonIcon fontSize="small" /> : <SmartToyIcon fontSize="small" />}
      </Avatar>
      <Box sx={{ maxWidth: '70%' }}>
        <Box
          sx={{
            p: 2,
            borderRadius: 2,
            bgcolor: isUser ? 'primary.main' : 'grey.100',
            color: isUser ? 'white' : 'text.primary',
            borderTopRightRadius: isUser ? 4 : 2,
            borderTopLeftRadius: isUser ? 2 : 4,
          }}
        >
          {isUser ? (
            <Typography variant="body1">{message.content}</Typography>
          ) : (
            <>
              <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                {isStreaming ? (
                  <TypingEffect text={message.content} />
                ) : (
                  message.content
                )}
              </Typography>

              {message.sql && <SQLBlock sql={message.sql} />}

              {message.chart_view ? (
                <ChartContainer
                  chartView={message.chart_view}
                  chartType={message.chart_type}
                  tableData={message.table_data}
                />
              ) : message.table_data ? (
                <DataTable data={message.table_data} />
              ) : null}
            </>
          )}
        </Box>
        <Typography
          variant="caption"
          sx={{
            display: 'block',
            mt: 0.5,
            color: 'text.disabled',
            textAlign: isUser ? 'right' : 'left',
          }}
        >
          {new Date(message.created_at).toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </Typography>
      </Box>
    </Box>
  );
};

export default MessageBubble;
