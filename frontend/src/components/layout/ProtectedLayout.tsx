import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import { useAuthStore } from '../../stores/authStore';
import NavBar from './NavBar';
import Loading from '../common/Loading';

const ProtectedLayout: React.FC = () => {
  const { isAuthenticated, isLoading, menusLoaded } = useAuthStore();

  if (isLoading) return <Loading fullScreen message="正在验证身份..." />;

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  if (!menusLoaded) return <Loading fullScreen message="正在加载权限..." />;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <NavBar />
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        <Outlet />
      </Box>
    </Box>
  );
};

export default ProtectedLayout;
