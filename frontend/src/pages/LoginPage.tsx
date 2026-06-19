import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box } from '@mui/material';
import { COLORS, RADIUS } from '../theme';
import { useAuthStore } from '../stores/authStore';
import { firstAccessiblePath } from '../utils/menuAccess';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const storeLogin = useAuthStore((s) => s.login);
  const token = useAuthStore((s) => s.token);
  const menusLoaded = useAuthStore((s) => s.menusLoaded);
  const allowedMenuPaths = useAuthStore((s) => s.allowedMenuPaths);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (token && menusLoaded) {
      const dest = firstAccessiblePath(allowedMenuPaths) ?? '/no-access';
      navigate(dest, { replace: true });
    }
  }, [token, menusLoaded, allowedMenuPaths, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await storeLogin(username, password);
      const paths = useAuthStore.getState().allowedMenuPaths;
      const dest = firstAccessiblePath(paths) ?? '/no-access';
      navigate(dest, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        zIndex: 9999,
      }}
    >
      <Box
        sx={{
          width: 420,
          bgcolor: COLORS.cardBg,
          borderRadius: `${RADIUS.lg}px`,
          padding: '48px 40px 40px',
          boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
          animation: 'fadeUp 0.5s ease',
          '@keyframes fadeUp': {
            from: { opacity: 0, transform: 'translateY(20px)' },
            to: { opacity: 1, transform: 'translateY(0)' },
          },
        }}
      >
        {/* Logo */}
        <Box sx={{ textAlign: 'center', mb: 1 }}>
          <Box
            component="h1"
            sx={{
              fontSize: 28,
              fontWeight: 700,
              background: 'linear-gradient(135deg, #667eea, #764ba2)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              m: 0,
              mb: 0.5,
            }}
          >
            ⬡ ChatBI
          </Box>
          <Box sx={{ fontSize: 14, color: COLORS.textMuted }}>
            对话式数据分析平台
          </Box>
        </Box>

        {/* Error message */}
        {error && (
          <Box
            sx={{
              color: COLORS.danger,
              fontSize: 13,
              mt: 2,
              mb: 1,
            }}
          >
            {error}
          </Box>
        )}

        {/* Form */}
        <Box component="form" onSubmit={handleSubmit}>
          <Box sx={{ mb: 2.5 }}>
            <Box
              component="label"
              sx={{
                display: 'block',
                fontSize: 13,
                fontWeight: 500,
                color: COLORS.textSecondary,
                mb: 0.75,
              }}
            >
              用户名
            </Box>
            <Box
              component="input"
              placeholder="请输入用户名"
              value={username}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setUsername(e.target.value)
              }
              required
              sx={{
                width: '100%',
                p: '12px 14px',
                border: '1px solid #d9d9d9',
                borderRadius: `${RADIUS.md}px`,
                fontSize: 14,
                outline: 'none',
                transition: 'all 0.2s',
                fontFamily: 'inherit',
                boxSizing: 'border-box',
                '&:focus': {
                  borderColor: COLORS.primary,
                  boxShadow: '0 0 0 3px rgba(102,126,234,0.15)',
                },
              }}
            />
          </Box>

          <Box sx={{ mb: 2.5 }}>
            <Box
              component="label"
              sx={{
                display: 'block',
                fontSize: 13,
                fontWeight: 500,
                color: COLORS.textSecondary,
                mb: 0.75,
              }}
            >
              密码
            </Box>
            <Box
              component="input"
              type="password"
              placeholder="请输入密码"
              value={password}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setPassword(e.target.value)
              }
              required
              sx={{
                width: '100%',
                p: '12px 14px',
                border: '1px solid #d9d9d9',
                borderRadius: `${RADIUS.md}px`,
                fontSize: 14,
                outline: 'none',
                transition: 'all 0.2s',
                fontFamily: 'inherit',
                boxSizing: 'border-box',
                '&:focus': {
                  borderColor: COLORS.primary,
                  boxShadow: '0 0 0 3px rgba(102,126,234,0.15)',
                },
              }}
            />
          </Box>

          <Box
            component="button"
            type="submit"
            disabled={loading}
            sx={{
              width: '100%',
              py: 1.5,
              background: 'linear-gradient(135deg, #667eea, #764ba2)',
              color: '#fff',
              border: 'none',
              borderRadius: `${RADIUS.md}px`,
              fontSize: 15,
              fontWeight: 500,
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              fontFamily: 'inherit',
              opacity: loading ? 0.65 : 1,
              '&:hover': loading
                ? {}
                : {
                    transform: 'translateY(-1px)',
                    boxShadow: '0 4px 12px rgba(102,126,234,0.4)',
                  },
            }}
          >
            {loading ? '登录中...' : '登 录'}
          </Box>
        </Box>

        <Box
          sx={{
            textAlign: 'center',
            mt: 2,
            fontSize: 12,
            color: '#bbb',
          }}
        >
          默认账号 admin / admin123
        </Box>
      </Box>
    </Box>
  );
};

export default LoginPage;
