/** 与后端 AdminService.menu_route_allowed 对称：用于前端路由 / 导航显隐 */

function normPath(s: string): string {
  const t = (s || '').trim();
  if (!t || t === '/') return '/';
  const x = t.replace(/\/+$/, '');
  return x || '/';
}

/**
 * 当前 location 是否可访问：存在某条已授权 path，与路由互为前缀关系即允许
 *（含仅授权子菜单时也可进入 /admin 再由子页承接）
 */
export function canVisitRoute(allowedPaths: string[], routePath: string): boolean {
  const r = normPath(routePath);
  if (!allowedPaths.length) return false;
  for (const raw of allowedPaths) {
    const p = normPath(raw);
    if (!p) continue;
    if (r === p || r.startsWith(`${p}/`) || p.startsWith(`${r}/`)) return true;
  }
  return false;
}

const FALLBACK_PRIORITY = ['/chat', '/datasources', '/agents', '/admin/users', '/admin/roles', '/admin/menus'];

/** 无权限进入当前页时，跳转到第一个可访问的默认页 */
export function firstAccessiblePath(allowedPaths: string[]): string | null {
  for (const p of FALLBACK_PRIORITY) {
    if (canVisitRoute(allowedPaths, p)) return p;
  }
  for (const p of allowedPaths) {
    const n = normPath(p);
    if (n && n !== '/') return n;
  }
  return null;
}
