import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import Loading from '../common/Loading';
import { canVisitRoute, firstAccessiblePath } from '../../utils/menuAccess';

/**
 * 根据 GET /api/admin/menus/user 返回的 allowed_paths 校验当前 URL。
 */
const MenuPathGuard: React.FC = () => {
  const location = useLocation();
  const { isAuthenticated, menusLoaded, allowedMenuPaths } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!menusLoaded) {
    return <Loading fullScreen message="正在加载权限..." />;
  }

  if (!canVisitRoute(allowedMenuPaths, location.pathname)) {
    const next = firstAccessiblePath(allowedMenuPaths);
    return <Navigate to={next ?? '/no-access'} replace />;
  }

  return <Outlet />;
};

export default MenuPathGuard;
