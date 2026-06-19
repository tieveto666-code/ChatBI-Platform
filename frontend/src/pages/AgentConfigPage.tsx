import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Drawer,
  TextField,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  OutlinedInput,
  Snackbar,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Paper,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import CloseIcon from '@mui/icons-material/Close';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import {
  agentService,
  type AgentConfigRow,
  type AgentConfigPayload,
  type DatasourceOptions,
  type RoleShareOption,
  type WorkflowTemplate,
  type WorkflowNodeConfig,
} from '../services/agents';
import AgentWorkflowEditor from '../components/agent/AgentWorkflowEditor';
import { emptyWorkflowFromTemplate, workflowPayload, PROVIDER_OPTIONS } from '../constants/agentWorkflow';

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

const badgeStyle: React.CSSProperties = {
  background: '#fff7e6',
  color: '#fa8c16',
  padding: '2px 8px',
  borderRadius: 4,
  fontSize: 12,
  fontWeight: 500,
};

const actionBtnSx = {
  fontSize: 12,
  borderColor: '#d9d9d9',
  color: '#555',
  textTransform: 'none' as const,
  py: 0.25,
  px: 1.25,
  minWidth: 0,
  '&:hover': { borderColor: '#667eea', color: '#667eea' },
};

const deleteBtnSx = {
  ...actionBtnSx,
  '&:hover': { borderColor: '#ff4d4f', color: '#ff4d4f' },
};

const emptyForm = {
  name: '',
  description: '',
  workflow_nodes: {} as Record<string, WorkflowNodeConfig>,
  model_provider: 'deepseek',
  model_name: 'deepseek-chat',
  temperature: 0.1,
  max_tokens: 4096,
  visibility: 'private',
  default_data_source_type: '' as string,
  default_db_connection_id: '' as string | number,
  default_file_upload_id: '' as string | number,
  shared_role_ids: [] as number[],
};

function sortAgents(list: AgentConfigRow[]): AgentConfigRow[] {
  return [...list].sort((a, b) => {
    if (a.is_default !== b.is_default) return a.is_default ? -1 : 1;
    return a.id - b.id;
  });
}

const AgentConfigPage: React.FC = () => {
  const [workflowTemplate, setWorkflowTemplate] = useState<WorkflowTemplate | null>(null);
  const [agents, setAgents] = useState<AgentConfigRow[]>([]);
  const [dsOptions, setDsOptions] = useState<DatasourceOptions | null>(null);
  const [roleOptions, setRoleOptions] = useState<RoleShareOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<AgentConfigRow | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<AgentConfigRow | null>(null);

  const [snack, setSnack] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [agentData, dsData, roles, wfTemplate] = await Promise.all([
        agentService.listAgents(),
        agentService.getDatasourceOptions(),
        agentService.getShareRoleOptions(),
        agentService.getWorkflowTemplate(),
      ]);
      setAgents(sortAgents(agentData?.items ?? []));
      setDsOptions(dsData ?? null);
      setRoleOptions(roles ?? []);
      setWorkflowTemplate(wfTemplate ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (!drawerOpen || !workflowTemplate) return;
    if (Object.keys(form.workflow_nodes).length === 0) {
      setForm((f) => ({
        ...f,
        workflow_nodes: emptyWorkflowFromTemplate(workflowTemplate),
      }));
    }
  }, [drawerOpen, workflowTemplate, form.workflow_nodes]);

  const canEdit = (agent: AgentConfigRow) =>
    agent.permission === 'admin' || agent.permission === 'edit';

  const canDelete = (agent: AgentConfigRow) =>
    !agent.is_default && agent.permission === 'admin';

  const openCreate = () => {
    setEditing(null);
    setForm({
      ...emptyForm,
      workflow_nodes: emptyWorkflowFromTemplate(workflowTemplate),
    });
    setDrawerOpen(true);
  };

  const openEdit = (agent: AgentConfigRow) => {
    if (!canEdit(agent)) {
      setSnack({ open: true, message: '您仅有使用权限，无法编辑此智能体', severity: 'error' });
      return;
    }
    setEditing(agent);
    setForm({
      name: agent.name,
      description: agent.description ?? '',
      workflow_nodes: agent.workflow_config ?? emptyWorkflowFromTemplate(workflowTemplate),
      model_provider: agent.model_provider,
      model_name: agent.model_name ?? '',
      temperature: agent.temperature,
      max_tokens: agent.max_tokens,
      visibility: agent.visibility || 'private',
      default_data_source_type: agent.default_data_source_type ?? '',
      default_db_connection_id: agent.default_db_connection_id ?? '',
      default_file_upload_id: agent.default_file_upload_id ?? '',
      shared_role_ids: agent.shared_role_ids ?? [],
    });
    setDrawerOpen(true);
  };

  const buildPayload = (): AgentConfigPayload => {
    const dst = form.default_data_source_type || null;
    const nl2sqlPrompt = form.workflow_nodes.nl2sql?.system_prompt ?? undefined;
    return {
      name: form.name.trim(),
      description: form.description.trim() || undefined,
      system_prompt: nl2sqlPrompt,
      workflow_config: workflowPayload(form.workflow_nodes),
      model_provider: form.model_provider,
      model_name: form.model_name.trim() || undefined,
      temperature: form.temperature,
      max_tokens: form.max_tokens,
      visibility: form.visibility,
      default_data_source_type: dst,
      default_db_connection_id:
        dst === 'db' && form.default_db_connection_id !== ''
          ? Number(form.default_db_connection_id)
          : null,
      default_file_upload_id:
        (dst === 'excel' || dst === 'csv') && form.default_file_upload_id !== ''
          ? Number(form.default_file_upload_id)
          : null,
      shared_role_ids: form.shared_role_ids,
    };
  };

  const handleSave = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const payload = buildPayload();
      if (editing) {
        const updated = await agentService.updateAgent(editing.id, payload);
        setAgents((prev) => sortAgents(prev.map((a) => (a.id === updated.id ? updated : a))));
        setSnack({ open: true, message: '智能体已更新', severity: 'success' });
      } else {
        const created = await agentService.createAgent(payload);
        setAgents((prev) => sortAgents([created, ...prev]));
        setSnack({ open: true, message: '智能体已创建', severity: 'success' });
      }
      setDrawerOpen(false);
    } catch (e) {
      setSnack({
        open: true,
        message: e instanceof Error ? e.message : '保存失败',
        severity: 'error',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setSaving(true);
    try {
      await agentService.deleteAgent(deleteTarget.id);
      setAgents((prev) => prev.filter((a) => a.id !== deleteTarget.id));
      setDeleteTarget(null);
      setDrawerOpen(false);
      setSnack({ open: true, message: '已删除', severity: 'success' });
    } catch (e) {
      setSnack({
        open: true,
        message: e instanceof Error ? e.message : '删除失败',
        severity: 'error',
      });
    } finally {
      setSaving(false);
    }
  };

  const filteredAgents = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return agents;
    return agents.filter(
      (a) =>
        a.name.toLowerCase().includes(q) ||
        (a.description ?? '').toLowerCase().includes(q) ||
        (a.created_by_name ?? '').toLowerCase().includes(q)
    );
  }, [agents, search]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box
        sx={{
          px: 3,
          py: 2,
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
          flexShrink: 0,
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
          智能体配置
        </Typography>
        <Typography variant="body2" color="text.secondary">
          管理问数智能体：工作流各节点 Prompt 与模型、默认数据源，以及可见性与角色共享
        </Typography>
      </Box>

      <Box sx={{ flex: 1, overflow: 'auto', px: 3, py: 2.5 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: 2,
            flexWrap: 'wrap',
            gap: 1,
          }}
        >
          <Box sx={searchBoxSx}>
            <SearchIcon sx={{ color: '#bbb', fontSize: 16 }} />
            <input
              type="text"
              placeholder="搜索名称、描述或归属用户..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={searchInputStyle}
            />
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={openCreate}
            disabled={loading}
            sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' }, textTransform: 'none' }}
          >
            新建智能体
          </Button>
        </Box>

        {loading && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <CircularProgress size={18} />
            <Typography variant="body2" color="text.secondary">
              加载中…
            </Typography>
          </Box>
        )}

        {!loading && filteredAgents.length === 0 && (
          <Paper
            variant="outlined"
            sx={{
              borderRadius: 1,
              border: '1px solid #e8e8e8',
              py: 5,
              textAlign: 'center',
            }}
          >
            <Typography variant="body2" color="text.secondary">
              {search ? '没有匹配的智能体' : '暂无智能体，点击「新建智能体」开始配置'}
            </Typography>
          </Paper>
        )}

        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: {
              xs: '1fr',
              md: 'repeat(2, minmax(0, 1fr))',
              lg: 'repeat(3, minmax(0, 1fr))',
            },
            gap: 2,
          }}
        >
          {filteredAgents.map((agent) => (
            <Paper
              key={agent.id}
              variant="outlined"
              sx={{
                borderRadius: 1,
                border: '1px solid #e8e8e8',
                overflow: 'hidden',
                transition: 'all .15s',
                display: 'flex',
                flexDirection: 'column',
                minHeight: 168,
                '&:hover': {
                  borderColor: '#667eea',
                  bgcolor: '#fafbff',
                },
              }}
            >
              <Box sx={{ px: 2, py: 2, flex: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.25 }}>
                  <Box
                    sx={{
                      width: 36,
                      height: 36,
                      borderRadius: 1,
                      bgcolor: '#f0f5ff',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <SmartToyOutlinedIcon sx={{ color: '#667eea', fontSize: 20 }} />
                  </Box>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flexWrap: 'wrap' }}>
                      <Typography variant="body2" sx={{ fontWeight: 500, fontSize: 15, color: '#333' }}>
                        {agent.name}
                      </Typography>
                      {agent.is_default && (
                        <Box component="span" sx={badgeStyle}>
                          系统内置
                        </Box>
                      )}
                    </Box>
                  </Box>
                </Box>

                <Typography
                  variant="body2"
                  sx={{
                    fontSize: 13,
                    color: '#888',
                    lineHeight: 1.5,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    flex: 1,
                  }}
                >
                  {agent.description || '暂无描述'}
                </Typography>

                <Typography variant="body2" sx={{ fontSize: 12, color: '#aaa' }}>
                  归属：{agent.created_by_name || '—'}
                </Typography>
              </Box>

              <Box
                sx={{
                  px: 2,
                  py: 1.25,
                  borderTop: '1px solid #f0f0f0',
                  display: 'flex',
                  justifyContent: 'flex-end',
                  gap: 0.75,
                  bgcolor: '#fafafa',
                }}
              >
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<EditOutlinedIcon sx={{ fontSize: 14 }} />}
                  onClick={() => openEdit(agent)}
                  sx={actionBtnSx}
                >
                  编辑
                </Button>
                {canDelete(agent) && (
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<DeleteOutlineIcon sx={{ fontSize: 14 }} />}
                    onClick={() => setDeleteTarget(agent)}
                    sx={deleteBtnSx}
                  >
                    删除
                  </Button>
                )}
              </Box>
            </Paper>
          ))}
        </Box>

        <Typography variant="caption" sx={{ mt: 1.5, display: 'block', color: '#888', fontSize: 12 }}>
          共 {agents.length} 个智能体
          {agents.some((a) => a.is_default) ? '（含 1 个系统内置，不可删除）' : ''}
        </Typography>
      </Box>

      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => !saving && setDrawerOpen(false)}
        PaperProps={{ sx: { width: { xs: '100%', sm: 600, md: 680 }, display: 'flex', flexDirection: 'column' } }}
      >
        <Box
          sx={{
            px: 2.5,
            py: 2,
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 600, fontSize: 16, flex: 1 }}>
            {editing ? (editing.is_default ? '编辑系统内置智能体' : '编辑智能体') : '新建智能体'}
          </Typography>
          <IconButton size="small" onClick={() => setDrawerOpen(false)} disabled={saving}>
            <CloseIcon />
          </IconButton>
        </Box>

        {editing?.is_default && (
          <Alert severity="info" sx={{ mx: 2.5, mt: 2, py: 0.5, fontSize: 13 }}>
            系统内置默认智能体，不可删除，可调整工作流 Prompt、模型与数据源绑定。
          </Alert>
        )}

        <Box sx={{ p: 2.5, overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="名称"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            fullWidth
            size="small"
            required
          />
          <TextField
            label="描述"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            fullWidth
            size="small"
            multiline
            minRows={2}
          />

          <Typography variant="subtitle2" sx={{ fontWeight: 500, color: '#555', fontSize: 13 }}>
            默认数据源
          </Typography>
          <Typography variant="caption" sx={{ color: '#888', fontSize: 12, display: 'block', mb: -1 }}>
            对话页未手动选数据源时，问数分支将使用此绑定。
          </Typography>
          <FormControl fullWidth size="small">
            <InputLabel>数据源类型</InputLabel>
            <Select
              label="数据源类型"
              value={form.default_data_source_type}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  default_data_source_type: e.target.value,
                  default_db_connection_id: '',
                  default_file_upload_id: '',
                }))
              }
            >
              <MenuItem value="">不绑定</MenuItem>
              <MenuItem value="db">SQLite 数据库</MenuItem>
              <MenuItem value="excel">Excel 文件</MenuItem>
              <MenuItem value="csv">CSV 文件</MenuItem>
            </Select>
          </FormControl>

          {form.default_data_source_type === 'db' && (
            <FormControl fullWidth size="small">
              <InputLabel>数据库连接</InputLabel>
              <Select
                label="数据库连接"
                value={form.default_db_connection_id}
                onChange={(e) => setForm((f) => ({ ...f, default_db_connection_id: e.target.value }))}
              >
                {(dsOptions?.db_connections ?? []).map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {(form.default_data_source_type === 'excel' || form.default_data_source_type === 'csv') && (
            <FormControl fullWidth size="small">
              <InputLabel>上传文件</InputLabel>
              <Select
                label="上传文件"
                value={form.default_file_upload_id}
                onChange={(e) => setForm((f) => ({ ...f, default_file_upload_id: e.target.value }))}
              >
                {(dsOptions?.file_uploads ?? []).map((f) => (
                  <MenuItem key={f.id} value={f.id}>
                    {f.original_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <Typography variant="subtitle2" sx={{ fontWeight: 500, color: '#555', fontSize: 13 }}>
            全局默认模型
          </Typography>
          <Typography variant="caption" sx={{ color: '#888', fontSize: 12, display: 'block', mb: -1 }}>
            各工作流节点未单独配置 Provider 时，继承以下模型参数。
          </Typography>
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Provider</InputLabel>
              <Select
                label="Provider"
                value={form.model_provider}
                onChange={(e) => setForm((f) => ({ ...f, model_provider: e.target.value }))}
              >
                {PROVIDER_OPTIONS.map((o) => (
                  <MenuItem key={o.value} value={o.value}>
                    {o.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="模型名称"
              value={form.model_name}
              onChange={(e) => setForm((f) => ({ ...f, model_name: e.target.value }))}
              fullWidth
              size="small"
            />
          </Box>
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <TextField
              label="温度"
              type="number"
              inputProps={{ min: 0, max: 1, step: 0.1 }}
              value={form.temperature}
              onChange={(e) => setForm((f) => ({ ...f, temperature: Number(e.target.value) }))}
              fullWidth
              size="small"
            />
            <TextField
              label="Max Tokens"
              type="number"
              value={form.max_tokens}
              onChange={(e) => setForm((f) => ({ ...f, max_tokens: Number(e.target.value) }))}
              fullWidth
              size="small"
            />
          </Box>

          <AgentWorkflowEditor
            template={workflowTemplate}
            nodes={form.workflow_nodes}
            globalDefaults={{
              model_provider: form.model_provider,
              model_name: form.model_name,
              temperature: form.temperature,
              max_tokens: form.max_tokens,
            }}
            onChange={(nodes) => setForm((f) => ({ ...f, workflow_nodes: nodes }))}
          />

          {!editing?.is_default && (
            <>
              <Typography variant="subtitle2" sx={{ fontWeight: 500, color: '#555', fontSize: 13 }}>
                可见性与共享
              </Typography>
              <FormControl fullWidth size="small">
                <InputLabel>可见性</InputLabel>
                <Select
                  label="可见性"
                  value={form.visibility}
                  onChange={(e) => setForm((f) => ({ ...f, visibility: e.target.value }))}
                >
                  <MenuItem value="private">私有（仅本人 + 授权角色）</MenuItem>
                  <MenuItem value="public">公共（有菜单权限的用户可见）</MenuItem>
                </Select>
              </FormControl>
              <FormControl fullWidth size="small">
                <InputLabel>共享给角色</InputLabel>
                <Select
                  multiple
                  label="共享给角色"
                  value={form.shared_role_ids}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      shared_role_ids: typeof e.target.value === 'string' ? [] : e.target.value,
                    }))
                  }
                  input={<OutlinedInput label="共享给角色" />}
                  renderValue={(selected) =>
                    roleOptions
                      .filter((r) => selected.includes(r.id))
                      .map((r) => r.name)
                      .join(', ')
                  }
                >
                  {roleOptions.map((r) => (
                    <MenuItem key={r.id} value={r.id}>
                      {r.name} ({r.code})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </>
          )}
        </Box>

        <Box
          sx={{
            px: 2.5,
            py: 2,
            borderTop: '1px solid #f0f0f0',
            display: 'flex',
            gap: 1.5,
            justifyContent: 'space-between',
          }}
        >
          <Box>
            {editing && editing.permission === 'admin' && !editing.is_default && (
              <Button
                color="error"
                startIcon={<DeleteOutlineIcon />}
                onClick={() => setDeleteTarget(editing)}
                disabled={saving}
                sx={{ textTransform: 'none' }}
              >
                删除
              </Button>
            )}
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button onClick={() => setDrawerOpen(false)} disabled={saving} sx={{ textTransform: 'none' }}>
              取消
            </Button>
            <Button
              variant="contained"
              onClick={() => void handleSave()}
              disabled={saving || !form.name.trim()}
              sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' }, textTransform: 'none' }}
            >
              {saving ? <CircularProgress size={20} color="inherit" /> : '保存'}
            </Button>
          </Box>
        </Box>
      </Drawer>

      <Dialog open={!!deleteTarget} onClose={() => !saving && setDeleteTarget(null)}>
        <DialogTitle sx={{ fontWeight: 600 }}>确认删除？</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            确定删除「{deleteTarget?.name}」吗？此操作不可撤销。
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteTarget(null)} disabled={saving}>
            取消
          </Button>
          <Button color="error" variant="contained" disabled={saving} onClick={() => void handleDelete()}>
            {saving ? '删除中…' : '确认删除'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snack.open}
        autoHideDuration={3000}
        onClose={() => setSnack((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snack.severity} onClose={() => setSnack((s) => ({ ...s, open: false }))}>
          {snack.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default AgentConfigPage;
