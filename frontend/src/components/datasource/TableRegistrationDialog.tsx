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
  IconButton,
  CircularProgress,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import FieldEditDialog, { EditableField } from './FieldEditDialog';
import TableSynonymDialog from './TableSynonymDialog';
import FilePreviewDialog, { SheetPreview } from './FilePreviewDialog';
import api from '../../services/api';
import type { ApiResponse } from '../../types/api';

export interface RegisteredTable {
  id: number;
  table_name: string;
  table_comment: string;
  columns: EditableField[];
}

interface TableRegistrationDialogProps {
  open: boolean;
  onClose: () => void;
  dsName: string;
  tables: RegisteredTable[];
  onSave: (tables: RegisteredTable[]) => void;
  loading?: boolean;
  resourceType?: 'db_connection' | 'file_upload';
  resourceId?: number;
}

const TableRegistrationDialog: React.FC<TableRegistrationDialogProps> = ({
  open,
  onClose,
  dsName,
  tables,
  onSave,
  loading = false,
  resourceType,
  resourceId,
}) => {
  const [localTables, setLocalTables] = useState<RegisteredTable[]>(tables);
  const [editTable, setEditTable] = useState<RegisteredTable | null>(null);
  const [fieldEditOpen, setFieldEditOpen] = useState(false);
  const [pendingRemoveId, setPendingRemoveId] = useState<number | null>(null);
  const [synonymTable, setSynonymTable] = useState<RegisteredTable | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewTitle, setPreviewTitle] = useState('');
  const [previewSheets, setPreviewSheets] = useState<SheetPreview[]>([]);

  React.useEffect(() => {
    if (open) setLocalTables(tables);
  }, [open, tables]);

  const pendingRemoveTable =
    pendingRemoveId != null ? localTables.find((t) => t.id === pendingRemoveId) : null;

  const handleRemoveTable = (tableId: number) => {
    setLocalTables((prev) => prev.filter((t) => t.id !== tableId));
    setPendingRemoveId(null);
  };

  const handleFieldSave = (updatedFields: EditableField[]) => {
    if (!editTable) return;
    setLocalTables((prev) =>
      prev.map((t) =>
        t.id === editTable.id ? { ...t, columns: updatedFields } : t
      )
    );
  };

  const handleOpenFieldEdit = (table: RegisteredTable) => {
    setEditTable(table);
    setFieldEditOpen(true);
  };

  const openTablePreview = async (table: RegisteredTable) => {
    if (resourceType !== 'db_connection' || resourceId == null) return;
    setPreviewTitle(`${dsName} / ${table.table_name}`);
    setPreviewOpen(true);
    setPreviewSheets([]);
    setPreviewLoading(true);
    try {
      const res = await api.get<ApiResponse<{
        table_name: string;
        columns: { name: string; type?: string }[];
        rows: Record<string, string>[];
      }>>(
        `/datasources/connections/${resourceId}/tables/${encodeURIComponent(table.table_name)}/preview`,
        { params: { limit: 200 } },
      );
      const data = res.data.data;
      if (!data) {
        setPreviewSheets([]);
        return;
      }
      setPreviewSheets([{
        sheet_name: data.table_name,
        columns: data.columns || [],
        rows: data.rows || [],
      }]);
    } catch {
      setPreviewSheets([]);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleReadNewTables = () => {
    const nextId = localTables.length > 0
      ? Math.max(...localTables.map((t) => t.id)) + 1
      : 1;
    const newTable: RegisteredTable = {
      id: nextId,
      table_name: `new_table_${nextId}`,
      table_comment: '新读取的表',
      columns: [
        { id: 1, column_name: 'id', column_type: 'INTEGER', is_nullable: false, is_primary_key: true, description: 'ID' },
        { id: 2, column_name: 'name', column_type: 'TEXT', is_nullable: false, is_primary_key: false, description: '名称' },
      ],
    };
    setLocalTables((prev) => [...prev, newTable]);
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>
          {dsName} — 注册/编辑表
        </DialogTitle>
        <DialogContent sx={{ maxHeight: '60vh', overflow: 'auto' }}>
          {loading ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 3 }}>
              <CircularProgress size={22} />
              <Typography variant="body2" color="text.secondary">正在同步表结构…</Typography>
            </Box>
          ) : (
            <>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            自动从数据源读取以下表结构，可编辑字段信息并为各数据字段配置标准词与同义词
          </Typography>

          {localTables.map((table) => (
            <Box
              key={table.id}
              sx={{
                bgcolor: '#fafafa',
                borderRadius: 1,
                p: 1.5,
                mb: 1.5,
                border: '1px solid',
                borderColor: 'divider',
              }}
            >
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  mb: 1,
                }}
              >
                <Typography variant="body1" sx={{ fontWeight: 500, fontSize: 14 }}>
                  📄 {table.table_name}{' '}
                  <Typography
                    component="span"
                    variant="body2"
                    sx={{ fontWeight: 400, color: 'text.secondary', fontSize: 12 }}
                  >
                    — {table.table_comment}
                  </Typography>
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5 }}>
                  {resourceType === 'db_connection' && resourceId != null && (
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<VisibilityIcon sx={{ fontSize: 16 }} />}
                      onClick={() => void openTablePreview(table)}
                      sx={{
                        fontSize: 12,
                        borderColor: '#d9d9d9',
                        color: '#555',
                        '&:hover': { borderColor: '#667eea', color: '#667eea' },
                      }}
                    >
                      预览
                    </Button>
                  )}
                  {resourceType && resourceId != null && (
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() => setSynonymTable(table)}
                      sx={{ fontSize: 12, borderColor: '#667eea', color: '#667eea' }}
                    >
                      字段术语
                    </Button>
                  )}
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => handleOpenFieldEdit(table)}
                    sx={{ fontSize: 12, borderColor: '#d9d9d9', color: 'text.secondary' }}
                  >
                    编辑字段
                  </Button>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => setPendingRemoveId(table.id)}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
              </Box>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small" sx={{ '& th, & td': { fontSize: 12 } }}>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 500 }}>字段名</TableCell>
                      <TableCell sx={{ fontWeight: 500 }}>类型</TableCell>
                      <TableCell sx={{ fontWeight: 500 }}>可空</TableCell>
                      <TableCell sx={{ fontWeight: 500 }}>主键</TableCell>
                      <TableCell sx={{ fontWeight: 500 }}>描述</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {table.columns.map((col) => (
                      <TableRow key={col.id}>
                        <TableCell>{col.column_name}</TableCell>
                        <TableCell>{col.column_type}</TableCell>
                        <TableCell>{col.is_nullable ? '✅' : '❌'}</TableCell>
                        <TableCell>{col.is_primary_key ? '✅' : '❌'}</TableCell>
                        <TableCell sx={{ color: 'text.secondary' }}>
                          {col.description || '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          ))}

          <Button
            variant="outlined"
            onClick={handleReadNewTables}
            sx={{
              width: '100%',
              py: 1,
              justifyContent: 'center',
              borderColor: '#d9d9d9',
              color: 'text.secondary',
              mt: 1,
            }}
          >
            + 从数据库读取新表
          </Button>
            </>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 1.5 }}>
          <Button onClick={onClose} color="inherit">
            取消
          </Button>
          <Button
            variant="contained"
            disabled={loading}
            onClick={() => {
              onSave(localTables);
              onClose();
            }}
            sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' } }}
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={pendingRemoveId != null} onClose={() => setPendingRemoveId(null)}>
        <DialogTitle>确认删除？</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            确定从列表中移除表「{pendingRemoveTable?.table_name ?? ''}」吗？
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendingRemoveId(null)}>取消</Button>
          <Button
            color="error"
            variant="contained"
            onClick={() => pendingRemoveId != null && handleRemoveTable(pendingRemoveId)}
          >
            确认删除
          </Button>
        </DialogActions>
      </Dialog>

      {editTable && (
        <FieldEditDialog
          open={fieldEditOpen}
          onClose={() => setFieldEditOpen(false)}
          tableName={editTable.table_name}
          fields={editTable.columns}
          onSave={handleFieldSave}
        />
      )}

      {synonymTable && resourceType && resourceId != null && (
        <TableSynonymDialog
          open={Boolean(synonymTable)}
          onClose={() => setSynonymTable(null)}
          resourceType={resourceType}
          resourceId={resourceId}
          tableName={synonymTable.table_name}
          columns={synonymTable.columns.map((c) => c.column_name)}
        />
      )}

      <FilePreviewDialog
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        fileName={previewTitle}
        loading={previewLoading}
        sheets={previewSheets}
      />
    </>
  );
};

export default TableRegistrationDialog;
