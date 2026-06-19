import React, { useState } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Typography,
} from '@mui/material';
import CodeOutlinedIcon from '@mui/icons-material/CodeOutlined';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';

interface SqlViewLinkProps {
  sql: string;
}

const SqlViewLink: React.FC<SqlViewLinkProps> = ({ sql }) => {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(sql);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = sql;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      <Button
        size="small"
        startIcon={<CodeOutlinedIcon sx={{ fontSize: 14 }} />}
        onClick={() => setOpen(true)}
        sx={{
          mt: 1,
          fontSize: 12,
          color: '#667eea',
          textTransform: 'none',
          px: 0.75,
          py: 0.25,
          minWidth: 0,
          alignSelf: 'flex-start',
          '&:hover': { bgcolor: '#f0f2ff' },
        }}
      >
        查看 SQL
      </Button>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontWeight: 600,
            fontSize: 16,
            pb: 1,
          }}
        >
          SQL 查询语句
          <IconButton size="small" onClick={() => setOpen(false)} aria-label="关闭">
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ p: 0 }}>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 2,
              overflow: 'auto',
              maxHeight: 420,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
              fontSize: 13,
              lineHeight: 1.55,
              bgcolor: '#1e1e1e',
              color: '#d4d4d4',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {sql}
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 2, py: 1.5 }}>
          <Typography variant="caption" sx={{ flex: 1, color: '#999' }}>
            只读查看，不支持编辑重跑
          </Typography>
          <Button
            startIcon={copied ? <CheckIcon /> : <ContentCopyIcon />}
            onClick={() => void handleCopy()}
            sx={{ textTransform: 'none' }}
          >
            {copied ? '已复制' : '复制 SQL'}
          </Button>
          <Button onClick={() => setOpen(false)} sx={{ textTransform: 'none' }}>
            关闭
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default SqlViewLink;
