import React, { useCallback, useEffect, useMemo, useState } from 'react';
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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Typography,
  CircularProgress,
  Alert,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { adminService, type AdminMenuNode } from '../../services/admin';

interface FlatRow {
  menu: AdminMenuNode;
  level: 0 | 1;
  sortLabel: string;
  isLast: boolean;
}

function flattenTwoLevels(roots: AdminMenuNode[]): FlatRow[] {
  const rows: FlatRow[] = [];
  roots.forEach((parent) => {
    const kids = parent.children ?? [];
    rows.push({ menu: parent, level: 0, sortLabel: String(parent.sort_order), isLast: kids.length === 0 });
    kids.forEach((child, idx) => {
      rows.push({
        menu: child,
        level: 1,
        sortLabel: `${parent.sort_order}.${idx + 1}`,
        isLast: idx === kids.length - 1,
      });
    });
  });
  return rows;
}

const MenuManagePage: React.FC = () => {
  const [searchText, setSearchText] = useState('');
  const [tree, setTree] = useState<AdminMenuNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingMenu, setEditingMenu] = useState<AdminMenuNode | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    icon: '',
    path: '',
    parent_id: 0,
    sort_order: 0,
  });
  const [saving, setSaving] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<AdminMenuNode | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  const loadMenus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminService.listMenusTree();
      setTree(data?.items ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败');
      setTree([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMenus();
  }, [loadMenus]);

  const flattened = useMemo(() => flattenTwoLevels(tree), [tree]);

  const filteredFlattened = useMemo(() => {
    if (!searchText.trim()) return flattened;
    const q = searchText.toLowerCase();
    return flattened.filter(
      (r) => r.menu.name.toLowerCase().includes(q) || (r.menu.path || '').toLowerCase().includes(q)
    );
  }, [flattened, searchText]);

  const topLevelMenus = useMemo(() => tree, [tree]);

  const handleOpenAdd = () => {
    setEditingMenu(null);
    setFormData({ name: '', icon: '', path: '', parent_id: 0, sort_order: 0 });
    setDialogOpen(true);
  };

  const handleOpenEdit = (menu: AdminMenuNode) => {
    setEditingMenu(menu);
    setFormData({
      name: menu.name,
      icon: menu.icon || '',
      path: menu.path || '',
      parent_id: menu.parent_id ?? 0,
      sort_order: menu.sort_order,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!formData.name.trim()) return;
    setSaving(true);
    try {
      const body = {
        parent_id: formData.parent_id ? formData.parent_id : null,
        name: formData.name.trim(),
        icon: formData.icon.trim() || null,
        path: formData.path.trim() || null,
        sort_order: formData.sort_order,
        is_visible: true,
      };
      if (editingMenu) {
        await adminService.updateMenu(editingMenu.id, body);
      } else {
        await adminService.createMenu(body);
      }
      setDialogOpen(false);
      await loadMenus();
    } catch {
      /* ignore */
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleteSubmitting(true);
    try {
      await adminService.deleteMenu(deleteTarget.id);
      setDeleteTarget(null);
      await loadMenus();
    } catch {
      /* ignore */
    } finally {
      setDeleteSubmitting(false);
    }
  };

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
            placeholder="搜索菜单名称或路径..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ border: 'none', outline: 'none', fontSize: 13, fontFamily: 'inherit', width: 220, background: 'transparent' }}
          />
        </Box>
        <Button variant="contained" onClick={handleOpenAdd} sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' }, textTransform: 'none' }}>
          + 添加菜单项
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
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555', width: 60 }}>排序</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>菜单名称</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>图标</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>路由路径</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>类型</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredFlattened.map(({ menu, level, isLast, sortLabel }) => (
                <TableRow
                  key={menu.id}
                  sx={{
                    '&:hover td': { bgcolor: '#f0f2ff' },
                    ...(level === 1 ? { '& td': { bgcolor: '#fafafa' } } : {}),
                  }}
                >
                  <TableCell sx={{ fontSize: 13 }}>{sortLabel}</TableCell>
                  <TableCell sx={{ fontSize: 13, pl: level === 1 ? 4 : 2 }}>
                    {level === 1 ? (
                      <Box component="span" sx={{ color: '#555' }}>
                        {'　　'}
                        {isLast ? '└ ' : '├ '}
                        {menu.name}
                      </Box>
                    ) : (
                      <strong>{menu.name}</strong>
                    )}
                  </TableCell>
                  <TableCell sx={{ fontSize: 13 }}>{menu.icon || '—'}</TableCell>
                  <TableCell sx={{ fontSize: 13, color: '#888' }}>{menu.path || '—'}</TableCell>
                  <TableCell>
                    {level === 0 ? (
                      <Box component="span" sx={badgeSx('#fff7e6', '#fa8c16', '#ffd591')}>
                        顶级菜单
                      </Box>
                    ) : (
                      <Box component="span" sx={badgeSx('#f0f2ff', '#667eea', '#b3c2ff')}>
                        子菜单
                      </Box>
                    )}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      <Button
                        size="small"
                        variant="outlined"
                        sx={{
                          fontSize: 12,
                          minWidth: 0,
                          px: 1,
                          py: 0.25,
                          borderColor: '#d9d9d9',
                          color: '#555',
                          '&:hover': { borderColor: '#667eea', color: '#667eea' },
                        }}
                        onClick={() => handleOpenEdit(menu)}
                      >
                        编辑
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        sx={{
                          fontSize: 12,
                          minWidth: 0,
                          px: 1,
                          py: 0.25,
                          borderColor: '#ffccc7',
                          color: '#ff4d4f',
                          '&:hover': { bgcolor: '#fff2f0', borderColor: '#ff4d4f' },
                        }}
                        onClick={() => setDeleteTarget(menu)}
                      >
                        删除
                      </Button>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      <Box sx={{ mt: 1.5, fontSize: 12, color: '#888' }}>共 {flattened.length} 个菜单项（含子菜单）</Box>

      <Dialog
        open={dialogOpen}
        onClose={() => !saving && setDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: { borderRadius: 2, boxShadow: '0 8px 24px rgba(0,0,0,.12)' } }}
      >
        <DialogTitle sx={{ fontSize: 16, fontWeight: 600, pb: 1.5, borderBottom: '1px solid #e8e8e8' }}>
          {editingMenu ? '编辑菜单' : '添加菜单项'}
        </DialogTitle>
        <DialogContent sx={{ pt: 2.5, pb: 2 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl size="small" fullWidth>
              <InputLabel>父菜单</InputLabel>
              <Select
                value={formData.parent_id}
                label="父菜单"
                onChange={(e) => setFormData({ ...formData, parent_id: e.target.value as number })}
                disabled={!!editingMenu}
              >
                <MenuItem value={0}>顶级菜单</MenuItem>
                {topLevelMenus.map((m) => (
                  <MenuItem key={m.id} value={m.id}>
                    {m.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="菜单名称"
              size="small"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="如：操作日志"
              fullWidth
            />
            <TextField
              label="图标"
              size="small"
              value={formData.icon}
              onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
              placeholder="如：HistoryIcon"
              fullWidth
            />
            <TextField
              label="路由路径"
              size="small"
              value={formData.path}
              onChange={(e) => setFormData({ ...formData, path: e.target.value })}
              placeholder="如：/admin/logs"
              fullWidth
            />
            <TextField
              label="排序序号"
              type="number"
              size="small"
              value={formData.sort_order}
              onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value, 10) || 0 })}
              placeholder="数字越小越靠前"
              fullWidth
            />
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
            {saving ? '保存中…' : editingMenu ? '保存' : '添加'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(deleteTarget)} onClose={() => !deleteSubmitting && setDeleteTarget(null)}>
        <DialogTitle>确认删除？</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            确定删除菜单「{deleteTarget?.name}」吗？子菜单与关联权限将一并删除，此操作不可撤销。
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

export default MenuManagePage;
