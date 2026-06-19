import { create } from 'zustand';

interface UIState {
  sidebarCollapsed: boolean;
  themeMode: 'light' | 'dark';
  toggleSidebar: () => void;
  setThemeMode: (mode: 'light' | 'dark') => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  themeMode: 'light',
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setThemeMode: (mode) => set({ themeMode: mode }),
}));
