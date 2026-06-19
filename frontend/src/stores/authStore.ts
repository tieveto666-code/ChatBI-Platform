import { create } from 'zustand';
import type { User } from '../types/api';
import type { AdminMenuNode } from '../services/admin';
import { authService } from '../services/auth';
import { adminService } from '../services/admin';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  userMenus: AdminMenuNode[] | null;
  allowedMenuPaths: string[];
  menusLoaded: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User) => void;
  checkAuth: () => Promise<void>;
  initialize: () => void;
  refreshUserMenus: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: !!localStorage.getItem('token'),
  isLoading: true,
  userMenus: null,
  allowedMenuPaths: [],
  menusLoaded: false,

  refreshUserMenus: async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      set({ userMenus: null, allowedMenuPaths: [], menusLoaded: true });
      return;
    }
    try {
      const data = await adminService.getUserMenus();
      set({
        userMenus: data.items,
        allowedMenuPaths: data.allowed_paths ?? [],
        menusLoaded: true,
      });
    } catch {
      set({ userMenus: [], allowedMenuPaths: [], menusLoaded: true });
    }
  },

  initialize: () => {
    const token = localStorage.getItem('token');
    if (token) {
      authService
        .getMe()
        .then(async (res) => {
          set({ user: res.data, isAuthenticated: true });
          await get().refreshUserMenus();
          set({ isLoading: false });
        })
        .catch(() => {
          localStorage.removeItem('token');
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            userMenus: null,
            allowedMenuPaths: [],
            menusLoaded: true,
          });
        });
    } else {
      set({ isLoading: false, menusLoaded: true });
    }
  },

  login: async (username: string, password: string) => {
    const res = await authService.login({ username, password });
    const { access_token, user } = res.data;
    localStorage.setItem('token', access_token);
    set({ user, token: access_token, isAuthenticated: true, menusLoaded: false });
    await get().refreshUserMenus();
  },

  logout: () => {
    authService.logout().catch(() => {});
    localStorage.removeItem('token');
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      userMenus: null,
      allowedMenuPaths: [],
      menusLoaded: true,
    });
  },

  setUser: (user: User) => set({ user }),

  checkAuth: async () => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const res = await authService.getMe();
        set({ user: res.data, isAuthenticated: true });
        await get().refreshUserMenus();
        set({ isLoading: false });
      } catch {
        localStorage.removeItem('token');
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
          userMenus: null,
          allowedMenuPaths: [],
          menusLoaded: true,
        });
      }
    } else {
      set({ isLoading: false, menusLoaded: true });
    }
  },
}));
