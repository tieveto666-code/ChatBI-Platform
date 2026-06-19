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
  Typography,
  Checkbox,
  FormControlLabel,
  CircularProgress,
  Alert,
  MenuItem,
  Select,
  FormControl,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import {
  adminService,
  type AdminMenuNode,
  type AdminRoleRow,
  type RoleAgentGrant,
  type RoleDatasourceGrant,
} from '../../services/admin';
import { useAuthStore } from '../../stores/authStore';

function collectDescendantIds(node: AdminMenuNode): number[] {
  const ids = [node.id];
  (node.children ?? []).forEach((c) => ids.push(...collectDescendantIds(c)));
  return ids;
}

function flattenRoleSearch(nodes: AdminMenuNode[], q: string): AdminMenuNode[] {
  if (!q.trim()) return nodes;
  const lower = q.toLowerCase();
  const out: AdminMenuNode[] = [];
  for (const n of nodes) {
    const match = n.name.toLowerCase().includes(lower);
    const filteredChildren = flattenRoleSearch(n.children ?? [], q);
    if (match || filteredChildren.length) {
      out.push({ ...n, children: match ? n.children : filteredChildren });
    }
  }
  return out;
}

const RoleManagePage: React.FC = () => {
  const [searchText, setSearchText] = useState('');
  const [roles, setRoles] = useState<AdminRoleRow[]>([]);
  const [menuTree, setMenuTree] = useState<AdminMenuNode[]>([]);
  const [userCountByRole, setUserCountByRole] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [permOpen, setPermOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<AdminRoleRow | null>(null);
  const [selectedMenuIds, setSelectedMenuIds] = useState<number[]>([]);
  const [createForm, setCreateForm] = useState({ name: '', code: '', description: '' });
  const [createMenuIds, setCreateMenuIds] = useState<number[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<AdminRoleRow | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  const [resourceOpen, setResourceOpen] = useState(false);
  const [resourceRole, setResourceRole] = useState<AdminRoleRow | null>(null);
  const [resourceCatalog, setResourceCatalog] = useState<{
    agents: { id: number; name: string; visibility: string }[];
    db_connections: { id: number; name: string; visibility: string }[];
    file_uploads: { id: number; name: string; visibility: string }[];
  } | null>(null);
  const [agentGrants, setAgentGrants] = useState<RoleAgentGrant[]>([]);
  const [datasourceGrants, setDatasourceGrants] = useState<RoleDatasourceGrant[]>([]);
  const [resourceSubmitting, setResourceSubmitting] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [roleData, menuData, userPage] = await Promise.all([
        adminService.listRoles(),
        adminService.listMenusTree(),
        adminService.listUsers(1, 100, ''),
      ]);
      setRoles(roleData?.items ?? []);
      setMenuTree(menuData?.items ?? []);
      const counts: Record<number, number> = {};
      (userPage?.items ?? []).forEach((u) => {
        counts[u.role_id] = (counts[u.role_id] ?? 0) + 1;
      });
      setUserCountByRole(counts);
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const filteredRoles = useMemo(() => {
    if (!searchText.trim()) return roles;
    const q = searchText.toLowerCase();
    return roles.filter((r) => r.name.toLowerCase().includes(q) || r.code.toLowerCase().includes(q));
  }, [roles, searchText]);

  const displayMenuTree = useMemo(() => flattenRoleSearch(menuTree, ''), [menuTree]);

  const handleOpenPerm = (role: AdminRoleRow) => {
    setEditingRole(role);
    setSelectedMenuIds([...(role.menu_ids ?? [])]);
    setPermOpen(true);
  };

  const handleOpenResource = async (role: AdminRoleRow) => {
    setResourceRole(role);
    setResourceOpen(true);
    setResourceSubmitting(true);
    try {
      const [catalog, grants] = await Promise.all([
        adminService.getResourceCatalog(),
        adminService.getRoleResources(role.id),
      ]);
      setResourceCatalog(catalog ?? null);
      setAgentGrants(grants?.agents ?? []);
      setDatasourceGrants(grants?.datasources ?? []);
    } catch {
      setResourceCatalog(null);
      setAgentGrants([]);
      setDatasourceGrants([]);
    } finally {
      setResourceSubmitting(false);
    }
  };

  const toggleAgentGrant = (agentId: number) => {
    setAgentGrants((prev) => {
      const exists = prev.find((g) => g.agent_id === agentId);
      if (exists) return prev.filter((g) => g.agent_id !== agentId);
      return [...prev, { agent_id: agentId, permission: 'use' }];
    });
  };

  const setAgentPermission = (agentId: number, permission: string) => {
    setAgentGrants((prev) =>
      prev.map((g) => (g.agent_id === agentId ? { ...g, permission } : g))
    );
  };

  const toggleDatasourceGrant = (resourceType: 'db_connection' | 'file_upload', resourceId: number) => {
    setDatasourceGrants((prev) => {
      const exists = prev.find(
        (g) => g.resource_type === resourceType && g.resource_id === resourceId
      );
      if (exists) {
        return prev.filter(
          (g) => !(g.resource_type === resourceType && g.resource_id === resourceId)
        );
      }
      return [...prev, { resource_type: resourceType, resource_id: resourceId, permission: 'use' }];
    });
  };

  const setDatasourcePermission = (
    resourceType: 'db_connection' | 'file_upload',
    resourceId: number,
    permission: string
  ) => {
    setDatasourceGrants((prev) =>
      prev.map((g) =>
        g.resource_type === resourceType && g.resource_id === resourceId
          ? { ...g, permission }
          : g
      )
    );
  };

  const saveRoleResources = async () => {
    if (!resourceRole) return;
    setResourceSubmitting(true);
    try {
      await adminService.updateRoleResources(resourceRole.id, {
        agents: agentGrants,
        datasources: datasourceGrants,
      });
      setResourceOpen(false);
    } finally {
      setResourceSubmitting(false);
    }
  };

  const handleToggleMenu = (node: AdminMenuNode) => {
    const ids = collectDescendantIds(node);
    const allSelected = ids.every((id) => selectedMenuIds.includes(id));
    setSelectedMenuIds((prev) => {
      const next = allSelected ? prev.filter((id) => !ids.includes(id)) : [...new Set([...prev, ...ids])];
      return next;
    });
  };

  const getParentNode = useCallback(
    (menuId: number): AdminMenuNode | undefined => {
      const walk = (nodes: AdminMenuNode[], parent: AdminMenuNode | undefined): AdminMenuNode | undefined => {
        for (const n of nodes) {
          if (n.id === menuId) return parent;
          const hit = walk(n.children ?? [], n);
          if (hit !== undefined) return hit;
        }
        return undefined;
      };
      return walk(menuTree, undefined);
    },
    [menuTree]
  );

  const handleToggleLeaf = (menuId: number) => {
    const parentNode = getParentNode(menuId);
    setSelectedMenuIds((prev) => {
      let next = prev.includes(menuId) ? prev.filter((id) => id !== menuId) : [...prev, menuId];
      if (parentNode?.children?.length) {
        const childIds = parentNode.children.map((c) => c.id);
        const allChildrenSelected = childIds.every((cid) => next.includes(cid));
        if (allChildrenSelected && !next.includes(parentNode.id)) {
          next = [...next, parentNode.id];
        }
      }
      return next;
    });
  };

  const isChecked = (menuId: number): boolean => selectedMenuIds.includes(menuId);

  const renderMenuCheckbox = (node: AdminMenuNode, level: number = 0) => {
    const hasChildren = !!(node.children && node.children.length > 0);
    const childIds = hasChildren ? node.children!.flatMap((c) => collectDescendantIds(c)) : [];
    const allSelected = hasChildren && childIds.every((id) => selectedMenuIds.includes(id));
    const someSelected =
      hasChildren && childIds.some((id) => selectedMenuIds.includes(id)) && !allSelected;

    return (
      <Box key={node.id} sx={{ ml: level * 3 }}>
        <FormControlLabel
          control={
            <Checkbox
              checked={hasChildren ? allSelected : isChecked(node.id)}
              indeterminate={someSelected}
              onChange={() => {
                if (hasChildren) {
                  handleToggleMenu(node);
                } else {
                  handleToggleLeaf(node.id);
                }
              }}
              size="small"
              sx={{ '& .MuiSvgIcon-root': { fontSize: 18 }, color: '#667eea', '&.Mui-checked': { color: '#667eea' } }}
            />
          }
          label={
            <Typography variant="body2" sx={{ fontSize: node.children?.length ? 14 : 13, fontWeight: node.children?.length ? 500 : 400 }}>
              {node.name}
            </Typography>
          }
          sx={{ my: 0.25 }}
        />
        {hasChildren && node.children!.map((child) => renderMenuCheckbox(child, level + 1))}
      </Box>
    );
  };

  const renderCreateMenuCheckbox = (node: AdminMenuNode, level: number = 0) => {
    const hasChildren = !!(node.children && node.children.length > 0);
    const childIds = hasChildren ? node.children!.flatMap((c) => collectDescendantIds(c)) : [];
    const allSelected = hasChildren && childIds.every((id) => createMenuIds.includes(id));
    const someSelected =
      hasChildren && childIds.some((id) => createMenuIds.includes(id)) && !allSelected;

    return (
      <Box key={node.id} sx={{ ml: level * 3 }}>
        <FormControlLabel
          control={
            <Checkbox
              checked={hasChildren ? allSelected : createMenuIds.includes(node.id)}
              indeterminate={someSelected}
              onChange={() => {
                const ids = collectDescendantIds(node);
                const allSel = ids.every((id) => createMenuIds.includes(id));
                setCreateMenuIds((prev) => (allSel ? prev.filter((id) => !ids.includes(id)) : [...new Set([...prev, ...ids])]));
              }}
              size="small"
              sx={{ '& .MuiSvgIcon-root': { fontSize: 18 }, color: '#667eea', '&.Mui-checked': { color: '#667eea' } }}
            />
          }
          label={
            <Typography variant="body2" sx={{ fontSize: node.children?.length ? 14 : 13, fontWeight: node.children?.length ? 500 : 400 }}>
              {node.name}
            </Typography>
          }
          sx={{ my: 0.25 }}
        />
        {hasChildren && node.children!.map((child) => renderCreateMenuCheckbox(child, level + 1))}
      </Box>
    );
  };

  const savePermissions = async () => {
    if (!editingRole) return;
    setSubmitting(true);
    try {
      await adminService.updateRoleMenus(editingRole.id, selectedMenuIds);
      setPermOpen(false);
      await loadAll();
      const me = useAuthStore.getState().user;
      if (me && editingRole.id === me.role_id) {
        await useAuthStore.getState().refreshUserMenus();
      }
    } catch {
      /* ignore */
    } finally {
      setSubmitting(false);
    }
  };

  const createRole = async () => {
    if (!createForm.name.trim() || !createForm.code.trim()) return;
    setSubmitting(true);
    try {
      await adminService.createRole({
        name: createForm.name.trim(),
        code: createForm.code.trim(),
        description: createForm.description || null,
        menu_ids: createMenuIds,
      });
      setCreateOpen(false);
      setCreateForm({ name: '', code: '', description: '' });
      setCreateMenuIds([]);
      await loadAll();
    } catch {
      /* ignore */
    } finally {
      setSubmitting(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleteSubmitting(true);
    try {
      await adminService.deleteRole(deleteTarget.id);
      setDeleteTarget(null);
      await loadAll();
    } catch {
      /* ignore */
    } finally {
      setDeleteSubmitting(false);
    }
  };

  const dialogPaperSx = { borderRadius: 2, boxShadow: '0 8px 24px rgba(0,0,0,.12)' };

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
            placeholder="搜索角色名称..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ border: 'none', outline: 'none', fontSize: 13, fontFamily: 'inherit', width: 220, background: 'transparent' }}
          />
        </Box>
        <Button
          variant="contained"
          onClick={() => {
            setCreateForm({ name: '', code: '', description: '' });
            setCreateMenuIds([]);
            setCreateOpen(true);
          }}
          sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' }, textTransform: 'none' }}
        >
          + 新建角色
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
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>角色名称</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>编码</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>描述</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>用户数</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>系统内置</TableCell>
                <TableCell sx={{ fontWeight: 500, fontSize: 13, color: '#555' }}>操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredRoles.map((role) => (
                <TableRow key={role.id} sx={{ '&:hover td': { bgcolor: '#f0f2ff' } }}>
                  <TableCell sx={{ fontSize: 13 }}>
                    <strong>{role.name}</strong>
                  </TableCell>
                  <TableCell>
                    <Box component="code" sx={{ bgcolor: '#f5f5f5', px: 1, py: 0.25, borderRadius: 1, fontSize: 12 }}>
                      {role.code}
                    </Box>
                  </TableCell>
                  <TableCell sx={{ fontSize: 13, color: '#888' }}>{role.description || '—'}</TableCell>
                  <TableCell sx={{ fontSize: 13 }}>{userCountByRole[role.id] ?? 0}</TableCell>
                  <TableCell>
                    {role.is_system ? (
                      <Box
                        component="span"
                        sx={{
                          display: 'inline-block',
                          px: 1.25,
                          py: 0.25,
                          borderRadius: '10px',
                          fontSize: 12,
                          fontWeight: 500,
                          bgcolor: '#f0f2ff',
                          color: '#667eea',
                          border: '1px solid #b3c2ff',
                        }}
                      >
                        是
                      </Box>
                    ) : (
                      <Box
                        component="span"
                        sx={{
                          display: 'inline-block',
                          px: 1.25,
                          py: 0.25,
                          borderRadius: '10px',
                          fontSize: 12,
                          fontWeight: 500,
                          bgcolor: '#f6ffed',
                          color: '#52c41a',
                          border: '1px solid #b7eb8f',
                        }}
                      >
                        否
                      </Box>
                    )}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
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
                        onClick={() => handleOpenPerm(role)}
                      >
                        菜单权限
                      </Button>
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
                        onClick={() => void handleOpenResource(role)}
                      >
                        资源授权
                      </Button>
                      {!role.is_system && (
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
                          onClick={() => setDeleteTarget(role)}
                        >
                          删除
                        </Button>
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      <Box sx={{ mt: 1.5, fontSize: 12, color: '#888' }}>共 {roles.length} 个角色</Box>

      <Dialog open={createOpen} onClose={() => !submitting && setCreateOpen(false)} maxWidth="sm" fullWidth PaperProps={{ sx: dialogPaperSx }}>
        <DialogTitle sx={{ fontSize: 16, fontWeight: 600, pb: 1.5, borderBottom: '1px solid #e8e8e8' }}>新建角色</DialogTitle>
        <DialogContent sx={{ pt: 2.5, pb: 2 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="角色名称"
              size="small"
              value={createForm.name}
              onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              placeholder="请输入角色名称"
              fullWidth
            />
            <TextField
              label="角色编码"
              size="small"
              value={createForm.code}
              onChange={(e) => setCreateForm({ ...createForm, code: e.target.value })}
              placeholder="英文编码，如 viewer"
              fullWidth
            />
            <TextField
              label="描述"
              size="small"
              value={createForm.description}
              onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
              placeholder="角色描述"
              fullWidth
            />
            <Typography variant="body2" sx={{ fontWeight: 500, color: '#555', mt: 1 }}>
              初始菜单权限
            </Typography>
            <Box sx={{ p: 1.5, bgcolor: '#fafafa', borderRadius: 1, border: '1px solid #e8e8e8' }}>
              {displayMenuTree.map((node) => renderCreateMenuCheckbox(node))}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 1.5, borderTop: '1px solid #e8e8e8' }}>
          <Button
            onClick={() => setCreateOpen(false)}
            disabled={submitting}
            variant="outlined"
            sx={{ color: '#555', borderColor: '#d9d9d9', '&:hover': { borderColor: '#667eea', color: '#667eea' }, textTransform: 'none' }}
          >
            取消
          </Button>
          <Button
            variant="contained"
            disabled={submitting}
            onClick={() => void createRole()}
            sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' }, textTransform: 'none' }}
          >
            {submitting ? '提交中…' : '创建'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={permOpen} onClose={() => !submitting && setPermOpen(false)} maxWidth="sm" fullWidth PaperProps={{ sx: dialogPaperSx }}>
        <DialogTitle sx={{ fontSize: 16, fontWeight: 600, pb: 1.5, borderBottom: '1px solid #e8e8e8' }}>
          编辑权限 - {editingRole?.name}
        </DialogTitle>
        <DialogContent sx={{ pt: 2.5, pb: 2 }}>
          <Typography variant="body2" sx={{ fontSize: 13, color: '#888', mb: 1.5 }}>
            勾选该角色可以访问的菜单，子菜单将跟随父菜单自动联动
          </Typography>
          <Box sx={{ p: 1.5, bgcolor: '#fafafa', borderRadius: 1, border: '1px solid #e8e8e8' }}>
            {displayMenuTree.map((node) => renderMenuCheckbox(node))}
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 1.5, borderTop: '1px solid #e8e8e8' }}>
          <Button
            onClick={() => setPermOpen(false)}
            disabled={submitting}
            variant="outlined"
            sx={{ color: '#555', borderColor: '#d9d9d9', '&:hover': { borderColor: '#667eea', color: '#667eea' }, textTransform: 'none' }}
          >
            取消
          </Button>
          <Button
            variant="contained"
            disabled={submitting}
            onClick={() => void savePermissions()}
            sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' }, textTransform: 'none' }}
          >
            {submitting ? '保存中…' : '保存'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={resourceOpen}
        onClose={() => !resourceSubmitting && setResourceOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: dialogPaperSx }}
      >
        <DialogTitle sx={{ fontSize: 16, fontWeight: 600 }}>
          资源授权 — {resourceRole?.name}
        </DialogTitle>
        <DialogContent dividers>
          {resourceSubmitting && !resourceCatalog ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress size={28} />
            </Box>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  智能体
                </Typography>
                {(resourceCatalog?.agents ?? []).map((agent) => {
                  const grant = agentGrants.find((g) => g.agent_id === agent.id);
                  return (
                    <Box
                      key={agent.id}
                      sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, pl: 1 }}
                    >
                      <Checkbox
                        checked={!!grant}
                        onChange={() => toggleAgentGrant(agent.id)}
                        size="small"
                      />
                      <Typography variant="body2" sx={{ flex: 1 }}>
                        {agent.name}
                        <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                          ({agent.visibility})
                        </Typography>
                      </Typography>
                      {grant && (
                        <FormControl size="small" sx={{ minWidth: 100 }}>
                          <Select
                            value={grant.permission}
                            onChange={(e) => setAgentPermission(agent.id, e.target.value)}
                          >
                            <MenuItem value="use">use</MenuItem>
                            <MenuItem value="edit">edit</MenuItem>
                            <MenuItem value="admin">admin</MenuItem>
                          </Select>
                        </FormControl>
                      )}
                    </Box>
                  );
                })}
              </Box>
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  数据库连接
                </Typography>
                {(resourceCatalog?.db_connections ?? []).map((conn) => {
                  const grant = datasourceGrants.find(
                    (g) => g.resource_type === 'db_connection' && g.resource_id === conn.id
                  );
                  return (
                    <Box
                      key={conn.id}
                      sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, pl: 1 }}
                    >
                      <Checkbox
                        checked={!!grant}
                        onChange={() => toggleDatasourceGrant('db_connection', conn.id)}
                        size="small"
                      />
                      <Typography variant="body2" sx={{ flex: 1 }}>
                        {conn.name}
                      </Typography>
                      {grant && (
                        <FormControl size="small" sx={{ minWidth: 100 }}>
                          <Select
                            value={grant.permission}
                            onChange={(e) =>
                              setDatasourcePermission('db_connection', conn.id, e.target.value)
                            }
                          >
                            <MenuItem value="use">use</MenuItem>
                            <MenuItem value="edit">edit</MenuItem>
                            <MenuItem value="admin">admin</MenuItem>
                          </Select>
                        </FormControl>
                      )}
                    </Box>
                  );
                })}
              </Box>
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  上传文件
                </Typography>
                {(resourceCatalog?.file_uploads ?? []).map((file) => {
                  const grant = datasourceGrants.find(
                    (g) => g.resource_type === 'file_upload' && g.resource_id === file.id
                  );
                  return (
                    <Box
                      key={file.id}
                      sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, pl: 1 }}
                    >
                      <Checkbox
                        checked={!!grant}
                        onChange={() => toggleDatasourceGrant('file_upload', file.id)}
                        size="small"
                      />
                      <Typography variant="body2" sx={{ flex: 1 }}>
                        {file.name}
                      </Typography>
                      {grant && (
                        <FormControl size="small" sx={{ minWidth: 100 }}>
                          <Select
                            value={grant.permission}
                            onChange={(e) =>
                              setDatasourcePermission('file_upload', file.id, e.target.value)
                            }
                          >
                            <MenuItem value="use">use</MenuItem>
                            <MenuItem value="edit">edit</MenuItem>
                            <MenuItem value="admin">admin</MenuItem>
                          </Select>
                        </FormControl>
                      )}
                    </Box>
                  );
                })}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResourceOpen(false)} disabled={resourceSubmitting}>
            取消
          </Button>
          <Button
            variant="contained"
            onClick={() => void saveRoleResources()}
            disabled={resourceSubmitting}
            sx={{ bgcolor: '#667eea' }}
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(deleteTarget)} onClose={() => !deleteSubmitting && setDeleteTarget(null)}>
        <DialogTitle>确认删除？</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            确定删除角色「{deleteTarget?.name}」吗？使用中的用户将被迁移到默认角色。此操作不可撤销。
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

export default RoleManagePage;
