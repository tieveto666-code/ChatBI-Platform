import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { firstAccessiblePath } from '../utils/menuAccess';

const NoAccessPage: React.FC = () => {
  const navigate = useNavigate();
  const { allowedMenuPaths, logout } = useAuthStore();

  const goSomewhere = () => {
    const p = firstAccessiblePath(allowedMenuPaths);
    if (p) navigate(p, { replace: true });
    else {
      logout();
      navigate('/login', { replace: true });
    }
  };

  return (
    <Box sx={{ p: 4, maxWidth: 520, mx: 'auto', mt: 8 }}>
      <Typography variant="h5" gutterBottom>
        暂无可访问功能
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        当前账号未分配任何菜单权限，或您尝试访问的页面不在授权范围内。请联系管理员在「角色管理」中为您分配菜单。
      </Typography>
      <Button variant="contained" onClick={goSomewhere}>
        {firstAccessiblePath(allowedMenuPaths) ? '返回可用页面' : '退出并重新登录'}
      </Button>
    </Box>
  );
};

export default NoAccessPage;
