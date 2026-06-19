import React, { useCallback, useEffect, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  TextField,
  MenuItem,
  Typography,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import CloseIcon from '@mui/icons-material/Close';
import api from '../../services/api';
import type { ApiResponse } from '../../types/api';

export interface FieldLexiconRow {
  id: number;
  table_name: string;
  target_column: string;
  standard_term: string;
  synonyms: string[];
}

interface TableSynonymDialogProps {
  open: boolean;
  onClose: () => void;
  resourceType: 'db_connection' | 'file_upload';
  resourceId: number;
  tableName: string;
  columns: string[];
}

function parseSynonymInput(text: string): string[] {
  return text
    .split(/[,，、\n]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function formatSynonymInput(synonyms: string[]): string {
  return synonyms.join('、');
}

const TableSynonymDialog: React.FC<TableSynonymDialogProps> = ({
  open,
  onClose,
  resourceType,
  resourceId,
  tableName,
  columns,
}) => {
  const [items, setItems] = useState<FieldLexiconRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [targetColumn, setTargetColumn] = useState('');
  const [standardTerm, setStandardTerm] = useState('');
  const [synonymInput, setSynonymInput] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const basePath =
    resourceType === 'db_connection'
      ? `/datasources/connections/${resourceId}`
      : `/datasources/files/${resourceId}`;

  const pickNextColumn = useCallback(
    (currentItems: FieldLexiconRow[], excludeId: number | null = null) => {
      const used = new Set(
        currentItems.filter((i) => i.id !== excludeId).map((i) => i.target_column)
      );
      return columns.find((c) => !used.has(c)) ?? '';
    },
    [columns]
  );

  const loadItems = useCallback(async (): Promise<FieldLexiconRow[]> => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<ApiResponse<{ items: FieldLexiconRow[] }>>(
        `${basePath}/tables/${encodeURIComponent(tableName)}/synonyms`
      );
      const list = res.data.data?.items ?? [];
      setItems(list);
      return list;
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载字段术语失败');
      setItems([]);
      return [];
    } finally {
      setLoading(false);
    }
  }, [basePath, tableName]);

  useEffect(() => {
    if (!open) return;
    setEditingId(null);
    setStandardTerm('');
    setSynonymInput('');
    void loadItems().then((list) => {
      setTargetColumn(pickNextColumn(list));
    });
  }, [open, loadItems, pickNextColumn]);

  const resetFormForAdd = (currentItems: FieldLexiconRow[]) => {
    setEditingId(null);
    setStandardTerm('');
    setSynonymInput('');
    setTargetColumn(pickNextColumn(currentItems));
  };

  const handleSubmit = async () => {
    if (!targetColumn || !standardTerm.trim()) return;
    setSubmitting(true);
    setError(null);
    const synonyms = parseSynonymInput(synonymInput);
    try {
      if (editingId != null) {
        await api.put(`${basePath}/synonyms/${editingId}`, {
          target_column: targetColumn,
          standard_term: standardTerm.trim(),
          synonyms,
        });
        const list = await loadItems();
        resetFormForAdd(list);
      } else {
        await api.post(`${basePath}/tables/${encodeURIComponent(tableName)}/synonyms`, {
          target_column: targetColumn,
          standard_term: standardTerm.trim(),
          synonyms,
        });
        const list = await loadItems();
        resetFormForAdd(list);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (row: FieldLexiconRow) => {
    setEditingId(row.id);
    setTargetColumn(row.target_column);
    setStandardTerm(row.standard_term);
    setSynonymInput(formatSynonymInput(row.synonyms ?? []));
  };

  const handleDelete = async (id: number) => {
    setSubmitting(true);
    setError(null);
    try {
      await api.delete(`${basePath}/synonyms/${id}`);
      const list = await loadItems();
      if (editingId === id) {
        resetFormForAdd(list);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除失败');
    } finally {
      setSubmitting(false);
    }
  };

  const usedColumns = new Set(items.filter((i) => i.id !== editingId).map((i) => i.target_column));
  const availableColumns = columns.filter((c) => !usedColumns.has(c));
  const allConfigured = editingId == null && availableColumns.length === 0 && items.length > 0;
  const configuredCount = items.length;
  const totalColumns = columns.length;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pb: 1 }}>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            字段术语 — {tableName}
          </Typography>
          <Typography variant="caption" sx={{ color: '#888' }}>
            同一张表可为多个字段分别配置标准词与同义词（已配置 {configuredCount}/{totalColumns} 个字段）
          </Typography>
        </Box>
        <IconButton size="small" onClick={onClose} aria-label="关闭">
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {allConfigured && (
          <Alert severity="info" sx={{ mb: 2 }}>
            本表全部字段均已配置术语。如需修改请编辑下方列表，或删除后重新添加。
          </Alert>
        )}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mb: 2 }}>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <TextField
              select
              label="数据字段"
              size="small"
              value={targetColumn}
              onChange={(e) => setTargetColumn(e.target.value)}
              disabled={editingId != null || allConfigured}
              sx={{ flex: 1, minWidth: 140 }}
              helperText={
                editingId != null
                  ? '编辑时不可更改字段'
                  : '选择尚未配置的字段，保存后可继续添加下一个'
              }
            >
              {(editingId != null ? columns : availableColumns.length > 0 ? availableColumns : columns).map((col) => (
                <MenuItem key={col} value={col}>
                  {col}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="标准词"
              size="small"
              value={standardTerm}
              onChange={(e) => setStandardTerm(e.target.value)}
              placeholder="如：销售额"
              sx={{ flex: 1, minWidth: 140 }}
            />
          </Box>
          <TextField
            label="同义词"
            size="small"
            value={synonymInput}
            onChange={(e) => setSynonymInput(e.target.value)}
            placeholder="多个同义词用逗号或顿号分隔，如：营收、销售收入"
            fullWidth
            helperText="一个标准词可对应多个同义词，用户提问中出现任一同义词均应映射到该字段"
          />
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="contained"
              disabled={submitting || allConfigured || !targetColumn || !standardTerm.trim()}
              onClick={() => void handleSubmit()}
              sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' }, textTransform: 'none' }}
            >
              {editingId != null ? '更新' : '添加并继续下一个字段'}
            </Button>
            {editingId != null && (
              <Button onClick={() => resetFormForAdd(items)} sx={{ textTransform: 'none' }}>
                取消编辑
              </Button>
            )}
          </Box>
        </Box>

        {loading ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 2 }}>
            <CircularProgress size={20} />
            <Typography variant="body2" color="text.secondary">加载中…</Typography>
          </Box>
        ) : items.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
            暂无字段术语，可在上方为各数据字段添加标准词与同义词
          </Typography>
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: '#fafafa' }}>
                  <TableCell sx={{ fontWeight: 500, fontSize: 13 }}>数据字段</TableCell>
                  <TableCell sx={{ fontWeight: 500, fontSize: 13 }}>标准词</TableCell>
                  <TableCell sx={{ fontWeight: 500, fontSize: 13 }}>同义词</TableCell>
                  <TableCell sx={{ fontWeight: 500, fontSize: 13, width: 88 }}>操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell sx={{ fontSize: 13, fontFamily: 'monospace' }}>{row.target_column}</TableCell>
                    <TableCell sx={{ fontSize: 13, fontWeight: 500 }}>{row.standard_term}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {(row.synonyms ?? []).length > 0 ? (
                          row.synonyms.map((s) => (
                            <Chip key={s} label={s} size="small" variant="outlined" sx={{ fontSize: 12 }} />
                          ))
                        ) : (
                          <Typography variant="caption" color="text.secondary">—</Typography>
                        )}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <IconButton size="small" onClick={() => handleEdit(row)} disabled={submitting}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => void handleDelete(row.id)} disabled={submitting}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 2, py: 1.5 }}>
        <Button onClick={onClose} sx={{ textTransform: 'none' }}>关闭</Button>
      </DialogActions>
    </Dialog>
  );
};

export default TableSynonymDialog;
