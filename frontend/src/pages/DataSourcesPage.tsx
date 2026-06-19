import React, { useCallback, useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  CircularProgress,
  Alert,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import VisibilityIcon from '@mui/icons-material/Visibility';
import SettingsIcon from '@mui/icons-material/Settings';
import api from '../services/api';
import type { ApiResponse, PaginatedData } from '../types/api';
import FileUploader from '../components/datasource/FileUploader';
import FilePreviewDialog, { SheetPreview } from '../components/datasource/FilePreviewDialog';
import TableRegistrationDialog, { RegisteredTable } from '../components/datasource/TableRegistrationDialog';

interface DbConnectionDto {
  id: number;
  name: string;
  db_type: string;
  db_path?: string | null;
  host?: string | null;
  port?: number | null;
  database_name?: string | null;
  is_active: boolean;
  created_at?: string | null;
}

interface FileUploadDto {
  id: number;
  original_name: string;
  file_size: number;
  query_db_ready: boolean;
  sheet_count: number;
  total_rows: number;
  status: string;
  created_at?: string | null;
}

interface SchemaApiTable {
  table_name: string;
  columns: { name: string; type: string; nullable?: boolean; pk?: boolean }[];
}

function connectionAddress(c: DbConnectionDto): string {
  if (c.db_type === 'sqlite') {
    return c.db_path || '—';
  }
  const host = c.host || '';
  const port = c.port != null ? `:${c.port}` : '';
  const dbn = c.database_name ? `/${c.database_name}` : '';
  return `${host}${port}${dbn}` || '—';
}

function mapSchemaToRegistered(tables: SchemaApiTable[]): RegisteredTable[] {
  return tables.map((t, ti) => ({
    id: ti + 1,
    table_name: t.table_name,
    table_comment: '',
    columns: (t.columns || []).map((c, ci) => ({
      id: ci + 1,
      column_name: c.name,
      column_type: c.type || 'TEXT',
      is_nullable: Boolean(c.nullable),
      is_primary_key: Boolean(c.pk),
      description: '',
    })),
  }));
}

const typeTagStyle = (type: string) => {
  const t = type.toLowerCase();
  const map: Record<string, React.CSSProperties> = {
    sqlite: { background: '#f0f5ff', color: '#667eea', padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 500 },
    mysql: { background: '#f6ffed', color: '#52c41a', padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 500 },
    postgresql: { background: '#e6f7ff', color: '#1890ff', padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 500 },
    xlsx: { background: '#fff7e6', color: '#fa8c16', padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 500 },
    csv: { background: '#f0f5ff', color: '#667eea', padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 500 },
  };
  return map[t] || { background: '#f0f0f0', color: '#555', padding: '2px 8px', borderRadius: 4, fontSize: 12 };
};

const DataSourcesPage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [dbSearch, setDbSearch] = useState('');
  const [fileSearch, setFileSearch] = useState('');

  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [datasources, setDatasources] = useState<DbConnectionDto[]>([]);
  const [excelFiles, setExcelFiles] = useState<FileUploadDto[]>([]);

  const [tableRegOpen, setTableRegOpen] = useState(false);
  const [currentDs, setCurrentDs] = useState<DbConnectionDto | null>(null);
  const [currentFile, setCurrentFile] = useState<FileUploadDto | null>(null);
  const [tableRegResourceType, setTableRegResourceType] = useState<'db_connection' | 'file_upload'>('db_connection');
  const [regTables, setRegTables] = useState<RegisteredTable[]>([]);
  const [schemaLoading, setSchemaLoading] = useState(false);

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState<FileUploadDto | null>(null);
  const [previewSheets, setPreviewSheets] = useState<SheetPreview[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);

  const [connDialogOpen, setConnDialogOpen] = useState(false);
  const [connForm, setConnForm] = useState({
    name: '',
    db_type: 'sqlite',
    db_path: '',
    host: '',
    port: '' as string,
    database_name: '',
    username: '',
    password: '',
  });
  const [connSubmitting, setConnSubmitting] = useState(false);
  const [connFormError, setConnFormError] = useState<string | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<
    | { kind: 'connection'; id: number; name: string }
    | { kind: 'file'; id: number; name: string }
    | null
  >(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  const loadLists = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const [connRes, filesRes] = await Promise.all([
        api.get<ApiResponse<PaginatedData<DbConnectionDto>>>('/datasources/connections', {
          params: { page: 1, page_size: 100 },
        }),
        api.get<ApiResponse<PaginatedData<FileUploadDto>>>('/datasources/files', {
          params: { page: 1, page_size: 100 },
        }),
      ]);
      setDatasources(connRes.data.data?.items ?? []);
      setExcelFiles(filesRes.data.data?.items ?? []);
    } catch (e) {
      setListError(e instanceof Error ? e.message : '加载失败');
    } finally {
      setListLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadLists();
  }, [loadLists]);

  const openAddConnection = () => {
    setConnForm({
      name: '',
      db_type: 'sqlite',
      db_path: '',
      host: '',
      port: '',
      database_name: '',
      username: '',
      password: '',
    });
    setConnFormError(null);
    setConnDialogOpen(true);
  };

  const submitConnection = async () => {
    setConnFormError(null);
    if (!connForm.name.trim()) {
      setConnFormError('请填写连接名称');
      return;
    }
    if (!connForm.db_path.trim()) {
      setConnFormError('SQLite 请填写数据库文件路径');
      return;
    }
    setConnSubmitting(true);
    try {
      await api.post('/datasources/connections', {
        name: connForm.name.trim(),
        db_type: 'sqlite',
        db_path: connForm.db_path.trim(),
        host: null,
        port: null,
        database_name: null,
        username: null,
        password: null,
      });
      setConnDialogOpen(false);
      await loadLists();
    } catch (e) {
      setConnFormError(e instanceof Error ? e.message : '创建失败');
    } finally {
      setConnSubmitting(false);
    }
  };

  const requestDeleteConnection = (c: DbConnectionDto) => {
    setDeleteTarget({ kind: 'connection', id: c.id, name: c.name });
  };

  const requestDeleteFile = (f: FileUploadDto) => {
    setDeleteTarget({ kind: 'file', id: f.id, name: f.original_name });
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleteSubmitting(true);
    try {
      if (deleteTarget.kind === 'connection') {
        await api.delete(`/datasources/connections/${deleteTarget.id}`);
      } else {
        await api.delete(`/datasources/files/${deleteTarget.id}`);
      }
      setDeleteTarget(null);
      await loadLists();
    } catch (e) {
      setListError(e instanceof Error ? e.message : '删除失败');
      setDeleteTarget(null);
    } finally {
      setDeleteSubmitting(false);
    }
  };

  const openManageTables = async (ds: DbConnectionDto) => {
    setCurrentDs(ds);
    setCurrentFile(null);
    setTableRegResourceType('db_connection');
    setTableRegOpen(true);
    setSchemaLoading(true);
    setRegTables([]);
    try {
      const res = await api.get<ApiResponse<{ tables: SchemaApiTable[] }>>(
        `/datasources/connections/${ds.id}/schema`
      );
      setRegTables(mapSchemaToRegistered(res.data.data?.tables ?? []));
    } catch {
      setRegTables([]);
    } finally {
      setSchemaLoading(false);
    }
  };

  const openManageFileTables = async (file: FileUploadDto) => {
    setCurrentFile(file);
    setCurrentDs(null);
    setTableRegResourceType('file_upload');
    setTableRegOpen(true);
    setSchemaLoading(true);
    setRegTables([]);
    try {
      const res = await api.get<ApiResponse<{ tables: SchemaApiTable[] }>>(
        `/datasources/files/${file.id}/schema`
      );
      setRegTables(mapSchemaToRegistered(res.data.data?.tables ?? []));
    } catch {
      setRegTables([]);
    } finally {
      setSchemaLoading(false);
    }
  };

  const handleTableRegSave = (tables: RegisteredTable[]) => {
    setRegTables(tables);
    setTableRegOpen(false);
  };

  const handleUpload = async (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    await api.post('/datasources/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    await loadLists();
  };

  const openPreview = async (f: FileUploadDto) => {
    setPreviewFile(f);
    setPreviewOpen(true);
    setPreviewSheets([]);
    setPreviewLoading(true);
    try {
      const res = await api.get<ApiResponse<{ sheets: SheetPreview[] }>>(
        `/datasources/files/${f.id}/preview`,
        { params: { limit: 200 } }
      );
      const sheets = res.data.data?.sheets ?? [];
      setPreviewSheets(
        sheets.map((s) => ({
          sheet_name: s.sheet_name,
          columns: s.columns || [],
          rows: s.rows || [],
        }))
      );
    } catch {
      setPreviewSheets([]);
    } finally {
      setPreviewLoading(false);
    }
  };

  const filteredDatasources = datasources.filter(
    (ds) =>
      !dbSearch ||
      ds.name.toLowerCase().includes(dbSearch.toLowerCase()) ||
      connectionAddress(ds).toLowerCase().includes(dbSearch.toLowerCase())
  );

  const filteredExcelFiles = excelFiles.filter(
    (f) =>
      !fileSearch ||
      f.original_name.toLowerCase().includes(fileSearch.toLowerCase())
  );

  const tabItemSx = (active: boolean) => ({
    py: 1.5,
    px: 3.5,
    cursor: 'pointer',
    fontSize: 14,
    color: active ? '#667eea' : '#555',
    borderBottom: '2px solid',
    borderColor: active ? '#667eea' : 'transparent',
    fontWeight: active ? 500 : 400,
    bgcolor: active ? '#fff' : '#fafafa',
    transition: 'all .15s',
    userSelect: 'none' as const,
    '&:hover': active ? {} : { color: '#667eea', bgcolor: '#f0f2ff' },
  });

  const searchBoxSx = {
    display: 'flex',
    alignItems: 'center',
    gap: 1,
    px: 1.5,
    py: 0.75,
    border: '1px solid #d9d9d9',
    borderRadius: 1,
    bgcolor: '#fff',
    '&:focus-within': { borderColor: '#667eea', boxShadow: '0 0 0 2px rgba(102,126,234,0.1)' },
  };

  const searchInputStyle: React.CSSProperties = {
    border: 'none',
    outline: 'none',
    fontSize: 13,
    fontFamily: 'inherit',
    width: 220,
    background: 'transparent',
  };

  const tableHoverSx = {
    '& .MuiTableRow-root:hover td': { bgcolor: '#f0f2ff' },
    '& .MuiTableRow-root:last-child td': { borderBottom: 'none' },
  };

  const sqliteReady = (c: DbConnectionDto) =>
    c.db_type === 'sqlite' && Boolean(c.db_path) && c.is_active;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ px: 3, py: 2, borderBottom: '1px solid', borderColor: 'divider', bgcolor: 'background.paper', flexShrink: 0 }}>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
          数据源管理
        </Typography>
        <Typography variant="body2" color="text.secondary">
          管理数据库连接和上传的 Excel/CSV 文件
        </Typography>
      </Box>

      <Box sx={{ display: 'flex', borderBottom: 1, borderColor: 'divider', bgcolor: '#fafafa' }}>
        <Box sx={tabItemSx(tabValue === 0)} onClick={() => setTabValue(0)}>
          数据库连接
        </Box>
        <Box sx={tabItemSx(tabValue === 1)} onClick={() => setTabValue(1)}>
          Excel/CSV 文件
        </Box>
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto', px: 3, py: 2.5 }}>
        {listError && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setListError(null)}>
            {listError}
          </Alert>
        )}

        {tabValue === 0 && (
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
              <Box sx={searchBoxSx}>
                <SearchIcon sx={{ color: '#bbb', fontSize: 16 }} />
                <input
                  type="text"
                  placeholder="搜索名称或路径..."
                  value={dbSearch}
                  onChange={(e) => setDbSearch(e.target.value)}
                  style={searchInputStyle}
                />
              </Box>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={openAddConnection}
                disabled={listLoading}
                sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' }, textTransform: 'none' }}
              >
                添加连接
              </Button>
            </Box>

            {listLoading && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <CircularProgress size={18} />
                <Typography variant="body2" color="text.secondary">加载中…</Typography>
              </Box>
            )}

            <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 1, border: '1px solid #e8e8e8' }}>
              <Table size="small" sx={tableHoverSx}>
                <TableHead>
                  <TableRow sx={{ bgcolor: '#fafafa' }}>
                    <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>名称</TableCell>
                    <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>类型</TableCell>
                    <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>路径 / 地址</TableCell>
                    <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>状态</TableCell>
                    <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredDatasources.map((ds) => (
                    <TableRow key={ds.id}>
                      <TableCell sx={{ fontSize: 13 }}>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>{ds.name}</Typography>
                      </TableCell>
                      <TableCell sx={{ fontSize: 13 }}>
                        <Box component="span" sx={typeTagStyle(ds.db_type)}>{ds.db_type}</Box>
                      </TableCell>
                      <TableCell sx={{ fontSize: 13, color: '#888', maxWidth: 280, wordBreak: 'break-all' }}>
                        {connectionAddress(ds)}
                      </TableCell>
                      <TableCell sx={{ fontSize: 13 }}>
                        <Typography
                          variant="body2"
                          sx={{
                            color: sqliteReady(ds) ? '#52c41a' : '#888',
                            fontWeight: 500,
                            fontSize: 13,
                          }}
                        >
                          {sqliteReady(ds) ? '就绪' : ds.is_active ? '待配置' : '未启用'}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ fontSize: 13 }}>
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<SettingsIcon />}
                          onClick={() => void openManageTables(ds)}
                          sx={{
                            fontSize: 12, mr: 0.5,
                            borderColor: '#d9d9d9', color: '#555',
                            '&:hover': { borderColor: '#667eea', color: '#667eea' },
                            textTransform: 'none', py: 0.25, px: 1, minWidth: 0,
                          }}
                        >
                          管理表
                        </Button>
                        <IconButton size="small" color="error" onClick={() => requestDeleteConnection(ds)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!listLoading && filteredDatasources.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} align="center" sx={{ py: 3 }}>
                        <Typography variant="body2" color="text.secondary">暂无数据库连接</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            <Typography variant="caption" sx={{ mt: 1.5, display: 'block', color: '#888', fontSize: 12 }}>
              共 {datasources.length} 个数据库连接
            </Typography>
          </Box>
        )}

        {tabValue === 1 && (
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
              <Box sx={searchBoxSx}>
                <SearchIcon sx={{ color: '#bbb', fontSize: 16 }} />
                <input
                  type="text"
                  placeholder="按文件名搜索..."
                  value={fileSearch}
                  onChange={(e) => setFileSearch(e.target.value)}
                  style={searchInputStyle}
                />
              </Box>
              <Button
                variant="contained"
                startIcon={<CloudUploadIcon />}
                disabled={listLoading}
                sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' }, textTransform: 'none' }}
                onClick={() => setUploadDialogOpen(true)}
              >
                上传新文件
              </Button>
            </Box>

            <Typography variant="subtitle2" sx={{ fontWeight: 500, mb: 1.5, color: '#888', fontSize: 13 }}>
              已上传文件
            </Typography>
            <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 1, border: '1px solid #e8e8e8' }}>
              <Table size="small" sx={tableHoverSx}>
                <TableHead>
                  <TableRow sx={{ bgcolor: '#fafafa' }}>
                    <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>文件名</TableCell>
                    <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>类型</TableCell>
                    <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>Sheet</TableCell>
                    <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>行数</TableCell>
                    <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>上传时间</TableCell>
                    <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredExcelFiles.map((file) => {
                    const ext = file.original_name.toLowerCase().endsWith('.csv') ? 'CSV' : 'XLSX';
                    return (
                      <TableRow key={file.id}>
                        <TableCell sx={{ fontSize: 13 }}>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>{file.original_name}</Typography>
                        </TableCell>
                        <TableCell sx={{ fontSize: 13 }}>
                          <Box component="span" sx={typeTagStyle(ext)}>{ext}</Box>
                        </TableCell>
                        <TableCell sx={{ fontSize: 13 }}>{file.sheet_count}</TableCell>
                        <TableCell sx={{ fontSize: 13 }}>{file.total_rows.toLocaleString()}</TableCell>
                        <TableCell sx={{ fontSize: 13, color: '#888' }}>
                          {file.created_at ? file.created_at.slice(0, 19).replace('T', ' ') : '—'}
                        </TableCell>
                        <TableCell sx={{ fontSize: 13 }}>
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<SettingsIcon />}
                            onClick={() => void openManageFileTables(file)}
                            sx={{
                              fontSize: 12, mr: 0.5,
                              borderColor: '#d9d9d9', color: '#555',
                              '&:hover': { borderColor: '#667eea', color: '#667eea' },
                              textTransform: 'none', py: 0.25, px: 1, minWidth: 0,
                            }}
                          >
                            管理表
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<VisibilityIcon />}
                            onClick={() => void openPreview(file)}
                            sx={{
                              fontSize: 12, mr: 0.5,
                              borderColor: '#d9d9d9', color: '#555',
                              '&:hover': { borderColor: '#667eea', color: '#667eea' },
                              textTransform: 'none', py: 0.25, px: 1, minWidth: 0,
                            }}
                          >
                            预览
                          </Button>
                          <IconButton size="small" color="error" onClick={() => requestDeleteFile(file)}>
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  {!listLoading && filteredExcelFiles.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                        <Typography variant="body2" color="text.secondary">暂无文件</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            <Typography variant="caption" sx={{ mt: 1.5, display: 'block', color: '#888', fontSize: 12 }}>
              共 {excelFiles.length} 个文件
            </Typography>
          </Box>
        )}
      </Box>

      {(currentDs || currentFile) && (
        <TableRegistrationDialog
          open={tableRegOpen}
          onClose={() => setTableRegOpen(false)}
          dsName={currentDs?.name ?? currentFile?.original_name ?? ''}
          tables={regTables}
          loading={schemaLoading}
          onSave={handleTableRegSave}
          resourceType={tableRegResourceType}
          resourceId={currentDs?.id ?? currentFile?.id}
        />
      )}

      {previewFile && (
        <FilePreviewDialog
          open={previewOpen}
          onClose={() => setPreviewOpen(false)}
          fileName={previewFile.original_name}
          loading={previewLoading}
          sheets={previewSheets}
        />
      )}

      <Dialog open={uploadDialogOpen} onClose={() => setUploadDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 600, fontSize: 16 }}>上传文件</DialogTitle>
        <DialogContent>
          <FileUploader
            onUpload={async (file) => {
              await handleUpload(file);
              setUploadDialogOpen(false);
            }}
            accept=".xlsx,.xls,.csv"
          />
        </DialogContent>
        <DialogActions sx={{ p: 2, pt: 0 }}>
          <Button variant="outlined" onClick={() => setUploadDialogOpen(false)} sx={{ borderColor: '#d9d9d9', color: '#555' }}>
            取消
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={connDialogOpen} onClose={() => !connSubmitting && setConnDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 600 }}>新建数据库连接</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          {connFormError && <Alert severity="error">{connFormError}</Alert>}
          <TextField
            label="连接名称"
            required
            fullWidth
            size="small"
            value={connForm.name}
            onChange={(e) => setConnForm((p) => ({ ...p, name: e.target.value }))}
          />
          <TextField
            label="数据库类型"
            fullWidth
            size="small"
            value="SQLite"
            disabled
            helperText="MVP 阶段仅支持 SQLite"
          />
          <TextField
            label="SQLite 文件路径（绝对路径）"
            required
            fullWidth
            size="small"
            value={connForm.db_path}
            onChange={(e) => setConnForm((p) => ({ ...p, db_path: e.target.value }))}
            helperText="请填写服务器上可访问的 .db / .sqlite / .sqlite3 文件绝对路径"
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button disabled={connSubmitting} onClick={() => setConnDialogOpen(false)}>取消</Button>
          <Button variant="contained" disabled={connSubmitting} onClick={() => void submitConnection()}>
            {connSubmitting ? '提交中…' : '创建'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(deleteTarget)} onClose={() => !deleteSubmitting && setDeleteTarget(null)}>
        <DialogTitle>确认删除？</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            确定删除「{deleteTarget?.name}」吗？此操作不可撤销。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleteSubmitting}>取消</Button>
          <Button color="error" variant="contained" disabled={deleteSubmitting} onClick={() => void confirmDelete()}>
            {deleteSubmitting ? '删除中…' : '确认删除'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DataSourcesPage;
