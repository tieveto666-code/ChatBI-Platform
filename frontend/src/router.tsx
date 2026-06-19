import { createBrowserRouter, Navigate } from 'react-router-dom';
import App from './App';
import LoginPage from './pages/LoginPage';
import ChatPage from './pages/ChatPage';
import DataSourcesPage from './pages/DataSourcesPage';
import AgentConfigPage from './pages/AgentConfigPage';
import AdminLayout from './pages/admin/AdminLayout';
import UserManagePage from './pages/admin/UserManagePage';
import RoleManagePage from './pages/admin/RoleManagePage';
import MenuManagePage from './pages/admin/MenuManagePage';
import ProtectedLayout from './components/layout/ProtectedLayout';
import MenuPathGuard from './components/layout/MenuPathGuard';
import AdminDefaultRedirect from './components/layout/AdminDefaultRedirect';
import NoAccessPage from './pages/NoAccessPage';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <Navigate to="/chat" replace />,
      },
      {
        path: 'login',
        element: <LoginPage />,
      },
      {
        path: 'no-access',
        element: <ProtectedLayout />,
        children: [{ index: true, element: <NoAccessPage /> }],
      },
      {
        path: '',
        element: <ProtectedLayout />,
        children: [
          {
            path: 'chat',
            element: <MenuPathGuard />,
            children: [{ index: true, element: <ChatPage /> }],
          },
          {
            path: 'datasources',
            element: <MenuPathGuard />,
            children: [{ index: true, element: <DataSourcesPage /> }],
          },
          {
            path: 'agents',
            element: <MenuPathGuard />,
            children: [{ index: true, element: <AgentConfigPage /> }],
          },
          {
            path: 'admin',
            element: <MenuPathGuard />,
            children: [
              { index: true, element: <AdminDefaultRedirect /> },
              {
                path: '',
                element: <AdminLayout />,
                children: [
                  { path: 'users', element: <UserManagePage /> },
                  { path: 'roles', element: <RoleManagePage /> },
                  { path: 'menus', element: <MenuManagePage /> },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
]);

export default router;
