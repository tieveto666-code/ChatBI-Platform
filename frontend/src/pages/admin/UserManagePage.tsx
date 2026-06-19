import React, { useCallback, useEffect, useState } from 'react';
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Alert,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { adminService, type AdminRoleOption, type AdminUserRow } from '../../services/admin';

const roleBadgeColors: Record<string, { bg: string; color: string; border: string }> = {
  admin: { bg: '#fff7e6', color: '#fa8c16', border: '#ffd591' },
  analyst: { bg: '#f0f2ff', color: '#667eea', border: '#b3c2ff' },
  user: { bg: '#f6ffed', color: '#52c41a', border: '#b7eb8f' },
};

const statusBadgeColors = {
  on: { bg: '#f6ffed', color: '#52c41a', border: '#b7eb8f' },
  off: { bg: '#fff2f0', color: '#ff4d4f', border: '#ffccc7' },
};

const UserManagePage: React.FC = () => {
  const [searchText, setSearchText] = useState('');
  const [keyword, setKeyword] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [total, setTotal] = useState(0);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [roles, setRoles] = useState<AdminRoleOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<AdminUserRow | null>(null);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    role_id: 3,
  });
  const [saving, setSaving] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<AdminUserRow | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  const loadRoles = useCallback(async () => {
    const list = await adminService.listRoleOptions();
    setRoles(list);
  }, []);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminService.listUsers(page, pageSize, keyword.trim());
      setUsers(data?.items ?? []);
      setTotal(data?.total ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败');
      setUsers([]);
    } finally {
      setLoading(false);
    }
  }, [page, keyword]);

  useEffect(() => {
    void loadRoles();
  }, [loadRoles]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setKeyword(searchText);
      setPage(1);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchText]);

  const badgeSx = (bg: string, color: string, border: string) => ({
    display: 'inline-block',
    px: 1.25,
    py: 0.25,
    borderRadius: '10px',
    fontSize: 12,
    fontWeight: 500,
    bgcolor: bg,
    color: color,
    border: `1px solid ${border}`,
  });

  const btnDefaultSx = {
    fontSize: 12,
    minWidth: 0,
    px: 1,
    py: 0.25,
    borderColor: '#d9d9d9',
    color: '#555',
    '&:hover': { borderColor: '#667eea', color: '#667eea' },
  };

  const btnDangerSx = {
    fontSize: 12,
    minWidth: 0,
    px: 1,
    py: 0.25,
    bgcolor: '#fff',
    color: '#ff4d4f',
    borderColor: '#ffccc7',
    '&:hover': { bgcolor: '#fff2f0', borderColor: '#ff4d4f' },
  };

  const btnPrimarySx = {
    fontSize: 12,
    minWidth: 0,
    px: 1,
    py: 0.25,
    bgcolor: '#667eea',
    color: '#fff',
    borderColor: '#667eea',
    '&:hover': { bgcolor: '#7c93f5', borderColor: '#7c93f5' },
  };

  const roleStyleFor = (code: string | undefined) =>
    roleBadgeColors[code || ''] ?? { bg: '#f5f5f5', color: '#555', border: '#d9d9d9' };

  const handleOpenCreate = () => {
    setEditingUser(null);
    setFormData({ username: '', email: '', password: '', role_id: roles[0]?.id ?? 3 });
    setDialogOpen(true);
  };

  const handleOpenEdit = (user: AdminUserRow) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      email: user.email || '',
      password: '',
      role_id: user.role_id,
    });
    setDialogOpen(true);
  };

  const handleToggleStatus = async (user: AdminUserRow) => {
    try {
      const next = !user.is_active;
      await adminService.updateUserStatus(user.id, next);
      await loadUsers();
    } catch {
      /* 错误由拦截器处理或静默 */
    }
  };

  const handleSave = async () => {
    if (!formData.username.trim()) return;
    if (!editingUser && formData.password.length < 6) return;
    setSaving(true);
    try {
      if (editingUser) {
        await adminService.updateUser(editingUser.id, {
          email: formData.email || null,
          role_id: formData.role_id,
          ...(formData.password.trim() ? { password: formData.password } : {}),
        });
      } else {
        await adminService.createUser({
          username: formData.username.trim(),
          password: formData.password,
          email: formData.email || null,
          role_id: formData.role_id,
        });
      }
      setDialogOpen(false);
      await loadUsers();
    } catch {
      /* axios 已提示 */
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleteSubmitting(true);
    try {
      await adminService.deleteUser(deleteTarget.id);
      setDeleteTarget(null);
      await loadUsers();
    } catch {
      /* ignore */
    } finally {
      setDeleteSubmitting(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            px: 1.5,
            py: 0.75,
            border: '1px solid #d9d9d9',
            borderRadius: 1,
            bgcolor: '#fff',
            '&:focus-within': { borderColor: '#667eea', boxShadow: '0 0 0 2px rgba(102,126,234,0.1)' },
          }}
        >
          <SearchIcon sx={{ color: '#bbb', fontSize: 16 }} />
          <input
            type="text"
            placeholder="搜索用户名或邮箱..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{
              border: 'none',
              outline: 'none',
              fontSize: 13,
              fontFamily: 'inherit',
              width: 220,
              background: 'transparent',
            }}
          />
        </Box>
        <Button
          variant="contained"
          onClick={handleOpenCreate}
          sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' }, textTransform: 'none' }}
        >
          + 新建用户
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 1, border: '1px solid #e8e8e8' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress size={28} />
          </Box>
        ) : (
          <Table sx={{ minWidth: 650 }}>
            <TableHead>
              <TableRow sx={{ bgcolor: '#fafafa' }}>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>用户名</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>邮箱</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>角色</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>状态</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>创建时间</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => {
                const roleMeta = roles.find((r) => r.id === user.role_id);
                const rs = roleStyleFor(roleMeta?.code);
                const st = user.is_active ? statusBadgeColors.on : statusBadgeColors.off;
                return (
                  <TableRow key={user.id} sx={{ '&:hover td': { bgcolor: '#f0f2ff' } }}>
                    <TableCell sx={{ fontSize: 13 }}>
                      <strong>{user.username}</strong>
                    </TableCell>
                    <TableCell sx={{ fontSize: 13, color: '#888' }}>{user.email || '—'}</TableCell>
                    <TableCell>
                      <Box component="span" sx={badgeSx(rs.bg, rs.color, rs.border)}>
                        {user.role_name || roleMeta?.name || `角色 #${user.role_id}`}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Box component="span" sx={badgeSx(st.bg, st.color, st.border)}>
                        {user.is_active ? '启用' : '已禁用'}
                      </Box>
                    </TableCell>
                    <TableCell sx={{ fontSize: 13, color: '#888' }}>
                      {user.created_at ? user.created_at.slice(0, 10) : '—'}
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        <Button size="small" variant="outlined" sx={btnDefaultSx} onClick={() => handleOpenEdit(user)}>
                          编辑
                        </Button>
                        <Button
                          size="small"
                          variant={user.is_active ? 'outlined' : 'contained'}
                          sx={user.is_active ? btnDangerSx : btnPrimarySx}
                          onClick={() => void handleToggleStatus(user)}
                        >
                          {user.is_active ? '禁用' : '启用'}
                        </Button>
                        <Button size="small" variant="outlined" sx={btnDangerSx} onClick={() => setDeleteTarget(user)}>
                          删除
                        </Button>
                      </Box>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1.5, fontSize: 12, color: '#888' }}>
        <span>共 {total} 个用户</span>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Button
            size="small"
            variant="outlined"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            sx={{ fontSize: 12, minWidth: 0, px: 1, borderColor: '#d9d9d9', color: '#555' }}
          >
            ‹ 上一页
          </Button>
          <Typography variant="body2" sx={{ lineHeight: '28px', fontSize: 12 }}>
            {page}/{totalPages}
          </Typography>
          <Button
            size="small"
            variant="outlined"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            sx={{ fontSize: 12, minWidth: 0, px: 1, borderColor: '#d9d9d9', color: '#555' }}
          >
            下一页 ›
          </Button>
        </Box>
      </Box>

      <Dialog
        open={dialogOpen}
        onClose={() => !saving && setDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: { borderRadius: 2, boxShadow: '0 8px 24px rgba(0,0,0,.12)' } }}
      >
        <DialogTitle sx={{ fontSize: 16, fontWeight: 600, pb: 1.5, borderBottom: '1px solid #e8e8e8' }}>
          {editingUser ? '编辑用户' : '新建用户'}
        </DialogTitle>
        <DialogContent sx={{ pt: 2.5, pb: 2 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="用户名"
              size="small"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              disabled={!!editingUser}
              placeholder="请输入用户名"
              fullWidth
            />
            <TextField
              label="邮箱"
              size="small"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="请输入邮箱"
              fullWidth
            />
            <TextField
              label={editingUser ? '新密码（留空不改）' : '密码'}
              type="password"
              size="small"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              placeholder={editingUser ? '不修改请留空' : '至少 6 位'}
              fullWidth
            />
            <FormControl size="small" fullWidth>
              <InputLabel>角色</InputLabel>
              <Select
                value={formData.role_id}
                label="角色"
                onChange={(e) => setFormData({ ...formData, role_id: Number(e.target.value) })}
              >
                {roles.map((r) => (
                  <MenuItem key={r.id} value={r.id}>
                    {r.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 1.5, borderTop: '1px solid #e8e8e8' }}>
          <Button
            onClick={() => setDialogOpen(false)}
            disabled={saving}
            variant="outlined"
            sx={{ color: '#555', borderColor: '#d9d9d9', '&:hover': { borderColor: '#667eea', color: '#667eea' }, textTransform: 'none' }}
          >
            取消
          </Button>
          <Button
            variant="contained"
            disabled={saving}
            onClick={() => void handleSave()}
            sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' }, textTransform: 'none' }}
          >
            {saving ? '保存中…' : '保存'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(deleteTarget)} onClose={() => !deleteSubmitting && setDeleteTarget(null)}>
        <DialogTitle>确认删除？</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            确定删除用户「{deleteTarget?.username}」吗？此操作不可撤销。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleteSubmitting}>
            取消
          </Button>
          <Button color="error" variant="contained" disabled={deleteSubmitting} onClick={() => void confirmDelete()}>
            {deleteSubmitting ? '删除中…' : '确认删除'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default UserManagePage;
