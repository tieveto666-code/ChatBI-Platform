import React from 'react';
import { Box, Typography, IconButton, Button } from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';

interface SQLBlockProps {
  sql: string;
  onExecute?: (sql: string) => Promise<void> | void;
}

const SQLBlock: React.FC<SQLBlockProps> = ({ sql, onExecute }) => {
  const [copied, setCopied] = React.useState(false);
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState(sql);
  const [running, setRunning] = React.useState(false);

  React.useEffect(() => setDraft(sql), [sql]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = sql;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleExecute = async () => {
    if (!onExecute) return;
    setRunning(true);
    try {
      await onExecute(draft);
      setEditing(false);
    } finally {
      setRunning(false);
    }
  };

  return (
    <Box
      sx={{
        position: 'relative',
        bgcolor: '#1e1e1e',
        borderRadius: 1,
        overflow: 'hidden',
        my: 1,
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          py: 0.5,
          bgcolor: '#2d2d2d',
        }}
      >
        <Typography variant="caption" sx={{ color: '#999' }}>
          SQL
        </Typography>
        <IconButton size="small" onClick={handleCopy} sx={{ color: '#999' }}>
          {copied ? <CheckIcon fontSize="small" /> : <ContentCopyIcon fontSize="small" />}
        </IconButton>
      </Box>
      {editing ? (
        <Box sx={{ p: 1.5 }}>
          <Box
            component="textarea"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            sx={{
              width: '100%',
              minHeight: 120,
              boxSizing: 'border-box',
              bgcolor: '#111',
              color: '#d4d4d4',
              border: '1px solid #444',
              borderRadius: 1,
              p: 1,
              fontFamily: '"Fira Code", "Consolas", monospace',
              fontSize: 13,
              lineHeight: 1.5,
            }}
          />
          <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', mt: 1 }}>
            <Button size="small" onClick={() => { setDraft(sql); setEditing(false); }}>取消</Button>
            <Button size="small" variant="contained" disabled={running || !draft.trim()} onClick={() => void handleExecute()}>
              {running ? '执行中' : '执行'}
            </Button>
          </Box>
        </Box>
      ) : (
        <>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 2,
              overflow: 'auto',
              fontFamily: '"Fira Code", "Consolas", monospace',
              fontSize: 13,
              lineHeight: 1.5,
              color: '#d4d4d4',
            }}
          >
            {sql}
          </Box>
          {onExecute && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', px: 1.5, pb: 1 }}>
              <Button size="small" variant="outlined" onClick={() => setEditing(true)}>编辑并重跑</Button>
            </Box>
          )}
        </>
      )}
    </Box>
  );
};

export default SQLBlock;
