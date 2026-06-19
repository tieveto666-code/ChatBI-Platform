import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Chip,
  CircularProgress,
} from '@mui/material';

export interface PreviewColumn {
  name: string;
  type?: string;
}

export interface SheetPreview {
  sheet_name: string;
  columns: PreviewColumn[];
  rows: Record<string, string>[];
}

interface FilePreviewDialogProps {
  open: boolean;
  onClose: () => void;
  fileName: string;
  loading?: boolean;
  sheets: SheetPreview[];
}

const FilePreviewDialog: React.FC<FilePreviewDialogProps> = ({
  open,
  onClose,
  fileName,
  loading = false,
  sheets,
}) => {
  const [activeSheet, setActiveSheet] = useState(0);

  React.useEffect(() => {
    if (open) setActiveSheet(0);
  }, [open, sheets.length]);

  const current = sheets[activeSheet];
  const colKeys = current?.columns.map((c) => c.name) ?? [];

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle sx={{ fontWeight: 600 }}>
        {fileName}
        {sheets.length > 1 && (
          <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
            （{sheets.length} 个工作表）
          </Typography>
        )}
      </DialogTitle>
      <DialogContent sx={{ maxHeight: '72vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {loading && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 2 }}>
            <CircularProgress size={20} />
            <Typography variant="body2" color="text.secondary">加载预览…</Typography>
          </Box>
        )}

        {!loading && sheets.length > 0 && (
          <>
            {sheets.length > 1 && (
            <Box sx={{ display: 'flex', gap: 1, mb: 1.5, flexWrap: 'wrap', borderBottom: '1px solid', borderColor: 'divider', pb: 1 }}>
              {sheets.map((s, i) => (
                <Chip
                  key={`${s.sheet_name}-${i}`}
                  label={s.sheet_name}
                  onClick={() => setActiveSheet(i)}
                  variant={activeSheet === i ? 'filled' : 'outlined'}
                  color={activeSheet === i ? 'primary' : 'default'}
                  sx={{ borderRadius: '14px', cursor: 'pointer' }}
                />
              ))}
            </Box>
            )}

            <TableContainer
              component={Paper}
              variant="outlined"
              sx={{
                flex: 1,
                maxHeight: 480,
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
              }}
            >
              <Table size="small" stickyHeader sx={{ '& .MuiTableCell-root': { fontSize: 12, borderColor: '#e8e8e8' } }}>
                <TableHead>
                  <TableRow>
                    {colKeys.map((key) => {
                      const meta = current.columns.find((c) => c.name === key);
                      return (
                        <TableCell
                          key={key}
                          sx={{
                            fontWeight: 600,
                            bgcolor: '#f5f5f5',
                            borderRight: '1px solid #e0e0e0',
                            whiteSpace: 'nowrap',
                            minWidth: 96,
                          }}
                        >
                          <Box component="span" sx={{ display: 'block' }}>{key}</Box>
                          {meta?.type && (
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 400 }}>
                              {meta.type}
                            </Typography>
                          )}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(current.rows || []).map((row, ri) => (
                    <TableRow key={ri} hover sx={{ '&:nth-of-type(even)': { bgcolor: '#fafafa' } }}>
                      {colKeys.map((key) => (
                        <TableCell
                          key={key}
                          sx={{
                            borderRight: '1px solid #eee',
                            maxWidth: 220,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {row[key] ?? ''}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}

        {!loading && sheets.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
            暂无预览数据
          </Typography>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 1.5 }}>
        <Button variant="contained" onClick={onClose} sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' } }}>
          关闭
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default FilePreviewDialog;
