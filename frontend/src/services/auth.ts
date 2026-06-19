import api from './api';
import type { ApiResponse, User } from '../types/api';

interface LoginParams {
  username: string;
  password: string;
}

interface RegisterParams {
  username: string;
  password: string;
  email: string;
  nickname: string;
}

interface AuthData {
  access_token: string;
  token_type: string;
  user: User;
}

export const authService = {
  login: (params: LoginParams) =>
    api.post<ApiResponse<AuthData>>('/auth/login', params).then((res) => res.data),

  register: (params: RegisterParams) =>
    api.post<ApiResponse<AuthData>>('/auth/register', params).then((res) => res.data),

  refresh: () =>
    api.post<ApiResponse<AuthData>>('/auth/refresh').then((res) => res.data),

  logout: () =>
    api.post<ApiResponse<null>>('/auth/logout').then((res) => res.data),

  getMe: () =>
    api.get<ApiResponse<User>>('/auth/me').then((res) => res.data),
};
