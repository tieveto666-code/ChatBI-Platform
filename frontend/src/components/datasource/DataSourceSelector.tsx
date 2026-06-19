import React, { useCallback, useEffect, useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Tabs, Tab, Box, Typography, Button, Radio, Checkbox,
  Alert, CircularProgress,
} from '@mui/material';
import api from '../../services/api';
import type { ApiResponse, PaginatedData } from '../../types/api';

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: (selection: {
    type: 'db' | 'excel';
    id?: number;
    tables?: string[];
    dataSourceType?: 'excel' | 'csv';
    displayName?: string;
  }) => void;
}

interface DbConnectionRow {
  id: number;
  name: string;
  db_type: string;
}

interface FileUploadRow {
  id: number;
  original_name: string;
  sheet_count: number;
  total_rows: number;
  created_at?: string | null;
}

interface SchemaTable {
  table_name?: string;
}

const PAGE_SIZE = 100;

const DataSourceSelector: React.FC<Props> = ({ open, onClose, onConfirm }) => {
  const [tabIndex, setTabIndex] = useState(0);

  const [dbConnections, setDbConnections] = useState<DbConnectionRow[]>([]);
  const [excelFiles, setExcelFiles] = useState<FileUploadRow[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  const [selectedDb, setSelectedDb] = useState<number | null>(null);
  const [schemaTables, setSchemaTables] = useState<string[]>([]);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [schemaError, setSchemaError] = useState<string | null>(null);
  const [selectedTables, setSelectedTables] = useState<string[]>([]);
  const [autoMode, setAutoMode] = useState(false);

  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);

  const loadLists = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const [connRes, filesRes] = await Promise.all([
        api.get<ApiResponse<PaginatedData<DbConnectionRow>>>('/datasources/connections', {
          params: { page: 1, page_size: PAGE_SIZE },
        }),
        api.get<ApiResponse<PaginatedData<FileUploadRow>>>('/datasources/files', {
          params: { page: 1, page_size: PAGE_SIZE },
        }),
      ]);
      const conns = connRes.data.data?.items ?? [];
      const files = filesRes.data.data?.items ?? [];
      setDbConnections(conns);
      setExcelFiles(files);
      setSelectedDb((prev) => {
        if (prev != null && conns.some((c) => c.id === prev)) return prev;
        return conns[0]?.id ?? null;
      });
      setSelectedFileId((prev) => {
        if (prev != null && files.some((f) => f.id === prev)) return prev;
        return files[0]?.id ?? null;
      });
    } catch (e) {
      setListError(e instanceof Error ? e.message : '加载数据源列表失败');
      setDbConnections([]);
      setExcelFiles([]);
    } finally {
      setListLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      void loadLists();
    }
  }, [open, loadLists]);

  useEffect(() => {
    if (!open || selectedDb == null) {
      setSchemaTables([]);
      setSchemaError(null);
      return;
    }
    let cancelled = false;
    setSchemaLoading(true);
    setSchemaError(null);
    api
      .get<ApiResponse<{ tables: SchemaTable[] }>>(`/datasources/connections/${selectedDb}/schema`)
      .then((res) => {
        if (cancelled) return;
        const names = (res.data.data?.tables ?? [])
          .map((t) => t.table_name)
          .filter((n): n is string => Boolean(n));
        setSchemaTables(names);
        setSelectedTables(names);
      })
      .catch((e) => {
        if (cancelled) return;
        setSchemaTables([]);
        setSelectedTables([]);
        setSchemaError(e instanceof Error ? e.message : '加载表结构失败');
      })
      .finally(() => {
        if (!cancelled) setSchemaLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, selectedDb]);

  const toggleTable = (table: string) => {
    setSelectedTables((prev) =>
      prev.includes(table) ? prev.filter((t) => t !== table) : [...prev, table]
    );
  };

  const handleConfirm = () => {
    if (tabIndex === 0) {
      if (selectedDb == null) return;
      onConfirm({
        type: 'db',
        id: selectedDb,
        tables: autoMode ? undefined : selectedTables,
        displayName: dbConnections.find((c) => c.id === selectedDb)?.name,
      });
    } else {
      if (selectedFileId == null) return;
      const file = excelFiles.find((f) => f.id === selectedFileId);
      const isCsv = file?.original_name?.toLowerCase().endsWith('.csv') ?? false;
      onConfirm({
        type: 'excel',
        id: selectedFileId,
        dataSourceType: isCsv ? 'csv' : 'excel',
        displayName: file?.original_name,
      });
    }
    onClose();
  };

  const confirmDisabled =
    listLoading ||
    (tabIndex === 0 && (selectedDb == null || schemaLoading)) ||
    (tabIndex === 1 && selectedFileId == null);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>选择数据源</DialogTitle>
      <Tabs value={tabIndex} onChange={(_, i) => setTabIndex(i)} sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
        <Tab label="数据库" />
        <Tab label="Excel" />
      </Tabs>
      <DialogContent>
        {(listError || schemaError) && (
          <Alert severity="error" sx={{ mb: 1 }}>
            {listError || schemaError}
          </Alert>
        )}
        {listLoading && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 1 }}>
            <CircularProgress size={18} />
            <Typography variant="body2" color="text.secondary">加载中…</Typography>
          </Box>
        )}
        {tabIndex === 0 && (
          <Box sx={{ opacity: listLoading ? 0.5 : 1, pointerEvents: listLoading ? 'none' : 'auto' }}>
            <Box
              sx={{
                p: 1.5, mb: 1, bgcolor: '#fff8e1', border: '1px solid #ffe082', borderRadius: 1,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 1,
              }}
              onClick={() => setAutoMode(true)}
            >
              <Typography variant="body2" color="textSecondary">
                <strong>让模型自行判断</strong> — 将所有表注入 LLM（仍需选择上方数据库连接）
              </Typography>
            </Box>
            {dbConnections.length === 0 && !listLoading && !listError && (
              <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>
                暂无数据库连接，请先在「数据源管理」中创建。
              </Typography>
            )}
            {dbConnections.map((db) => (
              <Box
                key={db.id}
                sx={{
                  mb: 1, p: 1.5,
                  border: selectedDb === db.id ? '1px solid #667eea' : '1px solid transparent',
                  borderRadius: 1, cursor: 'pointer',
                  bgcolor: selectedDb === db.id ? '#f0f2ff' : 'transparent',
                }}
                onClick={() => { setSelectedDb(db.id); setAutoMode(false); }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" fontWeight={500}>{db.name}</Typography>
                  <Typography variant="caption" color="textDisabled">{db.db_type}</Typography>
                  {selectedDb === db.id && !autoMode && (
                    <Typography variant="caption" color="primary" sx={{ ml: 'auto' }}>
                      已选 {selectedTables.length} 张表
                    </Typography>
                  )}
                </Box>
                {selectedDb === db.id && schemaLoading && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, pl: 3, mt: 1 }}>
                    <CircularProgress size={14} />
                    <Typography variant="caption" color="text.secondary">同步表结构…</Typography>
                  </Box>
                )}
                {selectedDb === db.id && !autoMode && !schemaLoading && schemaTables.length > 0 && (
                  <Box sx={{ pl: 3, mt: 1 }}>
                    {schemaTables.map((t) => (
                      <Box key={t} sx={{ display: 'flex', alignItems: 'center', gap: 0.5, py: 0.25 }}>
                        <Checkbox
                          size="small"
                          checked={selectedTables.includes(t)}
                          onChange={() => toggleTable(t)}
                          sx={{ '& .MuiSvgIcon-root': { fontSize: 18 } }}
                        />
                        <Typography variant="body2">{t}</Typography>
                      </Box>
                    ))}
                  </Box>
                )}
                {selectedDb === db.id && autoMode && !schemaLoading && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', pl: 3, mt: 0.5 }}>
                    将使用全部 {schemaTables.length} 张表
                  </Typography>
                )}
              </Box>
            ))}
          </Box>
        )}
        {tabIndex === 1 && (
          <Box sx={{ opacity: listLoading ? 0.5 : 1, pointerEvents: listLoading ? 'none' : 'auto' }}>
            <Box
              sx={{
                border: '2px dashed #d9d9d9', borderRadius: 2, p: 3, textAlign: 'center',
                mb: 2,
              }}
            >
              <Typography variant="h5" sx={{ mb: 0.5 }}>+</Typography>
              <Typography variant="body2">上传新文件</Typography>
              <Typography variant="caption" color="textDisabled">请在「数据源管理」页上传；此处可选择已上传文件</Typography>
            </Box>
            <Typography variant="caption" fontWeight={500} color="textSecondary">历史上传文件</Typography>
            {excelFiles.length === 0 && !listLoading && !listError && (
              <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>
                暂无文件记录。
              </Typography>
            )}
            {excelFiles.map((f) => (
              <Box
                key={f.id}
                sx={{
                  display: 'flex', alignItems: 'center', gap: 1.5, p: 1, mt: 0.5,
                  border: selectedFileId === f.id ? '1px solid #667eea' : '1px solid transparent',
                  borderRadius: 1, cursor: 'pointer',
                  bgcolor: selectedFileId === f.id ? '#f0f2ff' : 'transparent',
                }}
                onClick={() => setSelectedFileId(f.id)}
              >
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" fontWeight={500}>{f.original_name}</Typography>
                  <Typography variant="caption" color="textDisabled">
                    {f.sheet_count} Sheets · {f.total_rows.toLocaleString()} 行
                    {f.created_at ? ` · ${f.created_at.slice(0, 10)}` : ''}
                  </Typography>
                </Box>
                <Radio checked={selectedFileId === f.id} size="small" />
              </Box>
            ))}
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose}>取消</Button>
        <Button
          variant="contained"
          disabled={confirmDisabled}
          onClick={handleConfirm}
          sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' } }}
        >
          确认选择
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DataSourceSelector;
