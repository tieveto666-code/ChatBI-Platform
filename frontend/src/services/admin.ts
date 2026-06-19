import api from './api';
import type { ApiResponse } from '../types/api';

export interface AdminUserRow {
  id: number;
  username: string;
  email: string | null;
  role_id: number;
  role_name: string | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface AdminRoleRow {
  id: number;
  name: string;
  code: string;
  description: string | null;
  is_system: boolean;
  sort_order: number;
  menu_ids: number[];
  created_at: string | null;
  updated_at: string | null;
}

export interface AdminRoleOption {
  id: number;
  name: string;
  code: string;
  description: string | null;
  is_system: boolean;
  sort_order: number;
}

export interface AdminMenuNode {
  id: number;
  parent_id: number | null;
  name: string;
  icon: string | null;
  path: string | null;
  component: string | null;
  sort_order: number;
  is_visible: boolean;
  permission: string | null;
  children?: AdminMenuNode[];
}

export interface RoleAgentGrant {
  agent_id: number;
  permission: string;
}

export interface RoleDatasourceGrant {
  resource_type: 'db_connection' | 'file_upload';
  resource_id: number;
  permission: string;
}

export const adminService = {
  getUserMenus: () =>
    api
      .get<ApiResponse<{ items: AdminMenuNode[]; total: number; allowed_paths?: string[] }>>(
        '/admin/menus/user'
      )
      .then((r) => ({
        items: r.data.data.items ?? [],
        total: r.data.data.total ?? 0,
        allowed_paths: r.data.data.allowed_paths ?? [],
      })),

  listUsers: (page = 1, page_size = 20, keyword = '') =>
    api
      .get<ApiResponse<{ items: AdminUserRow[]; total: number; page: number; page_size: number }>>(
        '/admin/users',
        { params: { page, page_size, keyword } }
      )
      .then((r) => r.data.data),

  createUser: (body: { username: string; password: string; email?: string | null; role_id: number }) =>
    api.post<ApiResponse<AdminUserRow>>('/admin/users', body).then((r) => r.data.data),

  updateUser: (id: number, body: { email?: string | null; role_id?: number; password?: string }) =>
    api.put<ApiResponse<AdminUserRow>>(`/admin/users/${id}`, body).then((r) => r.data.data),

  updateUserStatus: (id: number, is_active: boolean) =>
    api
      .put<ApiResponse<AdminUserRow>>(`/admin/users/${id}/status`, { is_active })
      .then((r) => r.data.data),

  deleteUser: (id: number) => api.delete<ApiResponse<{ message: string }>>(`/admin/users/${id}`).then((r) => r.data.data),

  listRoles: () =>
    api.get<ApiResponse<{ items: AdminRoleRow[]; total: number }>>('/admin/roles').then((r) => r.data.data),

  listRoleOptions: () =>
    api.get<ApiResponse<AdminRoleOption[]>>('/admin/roles/all').then((r) => r.data.data),

  createRole: (body: {
    name: string;
    code: string;
    description?: string | null;
    sort_order?: number;
    menu_ids?: number[];
  }) => api.post<ApiResponse<AdminRoleRow>>('/admin/roles', body).then((r) => r.data.data),

  updateRoleMenus: (id: number, menu_ids: number[]) =>
    api.put<ApiResponse<AdminRoleRow>>(`/admin/roles/${id}/menus`, { menu_ids }).then((r) => r.data.data),

  deleteRole: (id: number) =>
    api.delete<ApiResponse<{ message: string }>>(`/admin/roles/${id}`).then((r) => r.data.data),

  getRoleResources: (roleId: number) =>
    api
      .get<ApiResponse<{ agents: RoleAgentGrant[]; datasources: RoleDatasourceGrant[] }>>(
        `/admin/roles/${roleId}/resources`
      )
      .then((r) => r.data.data),

  updateRoleResources: (
    roleId: number,
    body: { agents: RoleAgentGrant[]; datasources: RoleDatasourceGrant[] }
  ) =>
    api.put<ApiResponse<{ agents: RoleAgentGrant[]; datasources: RoleDatasourceGrant[] }>>(
      `/admin/roles/${roleId}/resources`,
      body
    ).then((r) => r.data.data),

  getResourceCatalog: () =>
    api
      .get<
        ApiResponse<{
          agents: { id: number; name: string; visibility: string }[];
          db_connections: { id: number; name: string; visibility: string }[];
          file_uploads: { id: number; name: string; visibility: string }[];
        }>
      >('/admin/resources/catalog')
      .then((r) => r.data.data),

  listMenusTree: () =>
    api.get<ApiResponse<{ items: AdminMenuNode[]; total: number }>>('/admin/menus').then((r) => r.data.data),

  createMenu: (body: Record<string, unknown>) =>
    api.post<ApiResponse<AdminMenuNode>>('/admin/menus', body).then((r) => r.data.data),

  updateMenu: (id: number, body: Record<string, unknown>) =>
    api.put<ApiResponse<AdminMenuNode>>(`/admin/menus/${id}`, body).then((r) => r.data.data),

  deleteMenu: (id: number) =>
    api.delete<ApiResponse<{ message: string }>>(`/admin/menus/${id}`).then((r) => r.data.data),
};
