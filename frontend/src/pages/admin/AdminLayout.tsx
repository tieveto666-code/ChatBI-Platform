import React, { useMemo } from 'react';
import { Box, List, ListItemButton, ListItemIcon, ListItemText, Typography } from '@mui/material';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import PeopleIcon from '@mui/icons-material/People';
import SecurityIcon from '@mui/icons-material/Security';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import { useAuthStore } from '../../stores/authStore';
import { canVisitRoute } from '../../utils/menuAccess';

const AdminLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const allowedMenuPaths = useAuthStore((s) => s.allowedMenuPaths);

  const navItems = useMemo(() => {
    const all = [
      { path: '/admin/users', label: '用户管理', icon: <PeopleIcon /> },
      { path: '/admin/roles', label: '角色管理', icon: <SecurityIcon /> },
      { path: '/admin/menus', label: '菜单管理', icon: <MenuBookIcon /> },
    ];
    return all.filter((item) => canVisitRoute(allowedMenuPaths, item.path));
  }, [allowedMenuPaths]);

  return (
    <Box sx={{ display: 'flex', height: '100%' }}>
      <Box
        sx={{
          width: 220,
          borderRight: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper',
          p: 2,
        }}
      >
        <Typography variant="subtitle2" color="text.secondary" sx={{ px: 1, mb: 1 }}>
          系统管理
        </Typography>
        <List dense>
          {navItems.map((item) => (
            <ListItemButton
              key={item.path}
              selected={location.pathname === item.path}
              onClick={() => navigate(item.path)}
              sx={{ borderRadius: 1, mb: 0.5 }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
      </Box>

      <Box sx={{ flex: 1, p: 3, overflow: 'auto' }}>
        <Outlet />
      </Box>
    </Box>
  );
};

export default AdminLayout;
