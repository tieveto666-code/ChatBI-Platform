import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { canVisitRoute } from '../../utils/menuAccess';

/** /admin 访问时跳到第一个有权限的子页 */
const AdminDefaultRedirect: React.FC = () => {
  const { allowedMenuPaths } = useAuthStore();
  const order = ['/admin/users', '/admin/roles', '/admin/menus'];
  for (const p of order) {
    if (canVisitRoute(allowedMenuPaths, p)) {
      return <Navigate to={p} replace />;
    }
  }
  return <Navigate to="/no-access" replace />;
};

export default AdminDefaultRedirect;
