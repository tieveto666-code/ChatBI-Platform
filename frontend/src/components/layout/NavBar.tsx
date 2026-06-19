import React, { useMemo, useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Box } from '@mui/material';
import { COLORS, RADIUS } from '../../theme';
import { useAuth } from '../../hooks/useAuth';
import { canVisitRoute } from '../../utils/menuAccess';

const NavBar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, allowedMenuPaths } = useAuth();

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const isActive = (path: string) => location.pathname.startsWith(path);

  const navItems = useMemo(
    () =>
      [
        { path: '/chat', label: '智能问答', icon: '🏠' },
        { path: '/datasources', label: '数据源', icon: '🗄️' },
        { path: '/agents', label: '智能体配置', icon: '🧠' },
      ].filter((item) => canVisitRoute(allowedMenuPaths, item.path)),
    [allowedMenuPaths]
  );

  const adminItems = useMemo(
    () =>
      [
        { path: '/admin/users', label: '用户管理' },
        { path: '/admin/roles', label: '角色管理' },
        { path: '/admin/menus', label: '菜单管理' },
      ].filter((item) => canVisitRoute(allowedMenuPaths, item.path)),
    [allowedMenuPaths]
  );

  const showAdminDropdown = adminItems.length > 0;

  const handleLogout = () => {
    setUserMenuOpen(false);
    logout();
    navigate('/login');
  };

  useEffect(() => {
    if (!userMenuOpen) return;
    const onDocClick = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [userMenuOpen]);

  return (
    <Box
      sx={{
        height: 56,
        bgcolor: COLORS.cardBg,
        borderBottom: `1px solid ${COLORS.border}`,
        display: 'flex',
        alignItems: 'center',
        px: 3,
        flexShrink: 0,
        zIndex: 100,
      }}
    >
      {/* Logo */}
      <Box
        sx={{
          fontSize: 18,
          fontWeight: 700,
          background: COLORS.gradient,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          mr: 4,
          cursor: 'pointer',
          whiteSpace: 'nowrap',
        }}
        onClick={() => {
          const first = navItems[0]?.path ?? adminItems[0]?.path ?? '/no-access';
          navigate(first);
        }}
      >
        ⬡ ChatBI
      </Box>

      {/* Nav items group */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25 }}>
        {navItems.map((item) => (
          <Box
            key={item.path}
            onClick={() => navigate(item.path)}
            sx={{
              position: 'relative',
              px: 2,
              height: 56,
              display: 'flex',
              alignItems: 'center',
              gap: 0.75,
              fontSize: 14,
              color: isActive(item.path) ? COLORS.primary : COLORS.textSecondary,
              cursor: 'pointer',
              transition: 'all 0.2s',
              borderBottom: isActive(item.path)
                ? `2px solid ${COLORS.primary}`
                : '2px solid transparent',
              fontWeight: isActive(item.path) ? 500 : 400,
              whiteSpace: 'nowrap',
              userSelect: 'none',
              '&:hover': {
                color: COLORS.primary,
                bgcolor: COLORS.primaryBg,
              },
            }}
          >
            <span>{item.icon}</span>
            {item.label}
          </Box>
        ))}

        {showAdminDropdown && (
          <Box
            sx={{ position: 'relative' }}
            onMouseEnter={() => setDropdownOpen(true)}
            onMouseLeave={() => setDropdownOpen(false)}
          >
            <Box
              sx={{
                position: 'relative',
                px: 2,
                pr: '22px !important',
                height: 56,
                display: 'flex',
                alignItems: 'center',
                gap: 0.75,
                fontSize: 14,
                color: isActive('/admin') ? COLORS.primary : COLORS.textSecondary,
                cursor: 'pointer',
                transition: 'all 0.2s',
                borderBottom: isActive('/admin')
                  ? `2px solid ${COLORS.primary}`
                  : '2px solid transparent',
                fontWeight: isActive('/admin') ? 500 : 400,
                whiteSpace: 'nowrap',
                userSelect: 'none',
                '&:hover': {
                  color: COLORS.primary,
                  bgcolor: COLORS.primaryBg,
                },
                '&::after': {
                  content: '"▾"',
                  position: 'absolute',
                  right: 4,
                  fontSize: 10,
                  color: '#bbb',
                },
              }}
            >
              <span>⚙️</span>
              系统管理
            </Box>

            {dropdownOpen && (
              <Box
                sx={{
                  display: 'block',
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  bgcolor: COLORS.cardBg,
                  borderRadius: `${RADIUS.md}px`,
                  boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                  minWidth: 160,
                  p: 0.5,
                  zIndex: 200,
                }}
              >
                {adminItems.map((item) => (
                  <Box
                    key={item.path}
                    onClick={() => {
                      navigate(item.path);
                      setDropdownOpen(false);
                    }}
                    sx={{
                      px: 2,
                      py: 1.25,
                      fontSize: 13,
                      color: COLORS.textSecondary,
                      cursor: 'pointer',
                      borderRadius: `${RADIUS.sm}px`,
                      transition: 'all 0.15s',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                      '&:hover': {
                        bgcolor: COLORS.primaryBg,
                        color: COLORS.primary,
                      },
                    }}
                  >
                    {item.label}
                  </Box>
                ))}
              </Box>
            )}
          </Box>
        )}
      </Box>

      {/* User menu */}
      <Box sx={{ ml: 'auto', position: 'relative' }} ref={userMenuRef}>
        <Box
          onClick={() => setUserMenuOpen((open) => !open)}
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            fontSize: 13,
            color: COLORS.textMuted,
            cursor: 'pointer',
            py: 0.5,
            px: 1,
            borderRadius: `${RADIUS.sm}px`,
            userSelect: 'none',
            transition: 'background 0.15s',
            '&:hover': { bgcolor: COLORS.primaryBg },
            '&::after': {
              content: '"▾"',
              fontSize: 10,
              color: '#bbb',
              ml: 0.25,
            },
          }}
        >
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: COLORS.gradient,
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 13,
              fontWeight: 500,
              flexShrink: 0,
            }}
          >
            {user?.username?.[0] || 'U'}
          </Box>
          <span>{user?.username || '用户'}</span>
        </Box>

        {userMenuOpen && (
          <Box
            sx={{
              position: 'absolute',
              top: 'calc(100% + 6px)',
              right: 0,
              bgcolor: COLORS.cardBg,
              borderRadius: `${RADIUS.md}px`,
              boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
              minWidth: 140,
              p: 0.5,
              zIndex: 300,
              border: `1px solid ${COLORS.border}`,
            }}
          >
            <Box
              onClick={handleLogout}
              sx={{
                px: 2,
                py: 1.25,
                fontSize: 13,
                color: COLORS.textSecondary,
                cursor: 'pointer',
                borderRadius: `${RADIUS.sm}px`,
                transition: 'all 0.15s',
                '&:hover': {
                  bgcolor: '#fff1f0',
                  color: COLORS.danger,
                },
              }}
            >
              退出
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default NavBar;
