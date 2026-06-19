import { createTheme } from '@mui/material/styles';

// ChatBI Design Tokens — matching HTML prototype exactly
export const COLORS = {
  primary: '#667eea',
  primaryLight: '#7c93f5',
  primaryBg: '#f0f2ff',
  primaryBorder: '#b3c2ff',
  success: '#52c41a',
  danger: '#ff4d4f',
  warning: '#fa8c16',
  text: '#1a1a2e',
  textSecondary: '#555',
  textMuted: '#888',
  border: '#e8e8e8',
  bg: '#f0f2f5',
  cardBg: '#fff',
  gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
};

export const RADIUS = {
  sm: 6,
  md: 8,
  lg: 12,
};

const theme = createTheme({
  palette: {
    primary: { main: COLORS.primary, light: COLORS.primaryLight, contrastText: '#fff' },
    secondary: { main: '#764ba2' },
    success: { main: COLORS.success },
    error: { main: COLORS.danger },
    warning: { main: COLORS.warning },
    background: { default: COLORS.bg, paper: COLORS.cardBg },
    text: { primary: COLORS.text, secondary: COLORS.textSecondary },
    divider: COLORS.border,
  },
  shape: { borderRadius: RADIUS.md },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", sans-serif',
    fontSize: 14,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none' as const,
          fontWeight: 500,
          borderRadius: RADIUS.sm,
          padding: '7px 16px',
          fontSize: 13,
          fontFamily: 'inherit',
          minWidth: 'auto',
        },
        containedPrimary: {
          background: COLORS.primary,
          '&:hover': { background: COLORS.primaryLight },
        },
        outlined: {
          borderColor: '#d9d9d9',
          color: COLORS.textSecondary,
          '&:hover': { borderColor: COLORS.primary, color: COLORS.primary, background: 'transparent' },
        },
        sizeSmall: { padding: '4px 10px', fontSize: 12 },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-head': {
            fontWeight: 500,
            fontSize: 13,
            color: COLORS.textSecondary,
            backgroundColor: '#fafafa',
            borderBottom: `1px solid ${COLORS.border}`,
          },
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover td': { backgroundColor: COLORS.primaryBg },
          '& td': { fontSize: 13, borderBottom: '1px solid #f5f5f5', padding: '10px 14px' },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        outlined: { border: `1px solid ${COLORS.border}` },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: { borderRadius: RADIUS.lg },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 10, fontSize: 12, fontWeight: 500 },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none' as const,
          fontSize: 14,
          minHeight: 44,
          '&.Mui-selected': { fontWeight: 500 },
        },
      },
    },
  },
});

export default theme;
