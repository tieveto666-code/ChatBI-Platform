from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.datasources import router as datasources_router
from routers.admin_users import router as admin_users_router
from routers.admin_roles import router as admin_roles_router
from routers.admin_menus import router as admin_menus_router
from routers.agents import router as agents_router

__all__ = [
    "auth_router",
    "chat_router",
    "datasources_router",
    "admin_users_router",
    "admin_roles_router",
    "admin_menus_router",
    "agents_router",
]
