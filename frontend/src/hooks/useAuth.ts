import { useAuthStore } from '../stores/authStore';

export function useAuth() {
  const { user, token, isAuthenticated, isLoading, login, logout, allowedMenuPaths } = useAuthStore();

  return {
    user,
    token,
    isAuthenticated,
    isLoading,
    login,
    logout,
    allowedMenuPaths,
    /** 角色编码为 admin（仅展示/语义；权限以菜单为准） */
    isAdminRole: user?.role_code === 'admin',
  };
}
