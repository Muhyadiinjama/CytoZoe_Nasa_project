/* Tiny history router: /overview, /health, /environment, /reviews with query-string state (PRD 15.4). */
import { useSyncExternalStore } from 'react';

export const ROUTES = [
  { path: '/overview', label: 'Health overview' },
  { path: '/health', label: 'Health trends' },
  { path: '/environment', label: 'Radiation review' },
  { path: '/reviews', label: 'Review log' },
] as const;
export type RoutePath = typeof ROUTES[number]['path'];

const listeners = new Set<() => void>();
function emit() { listeners.forEach((l) => l()); }
window.addEventListener('popstate', emit);

function subscribe(cb: () => void) { listeners.add(cb); return () => { listeners.delete(cb); }; }
function snapshot() { return window.location.pathname + window.location.search; }

export function useLocation(): { path: RoutePath; params: URLSearchParams; href: string } {
  const href = useSyncExternalStore(subscribe, snapshot);
  const u = new URL(href, window.location.origin);
  const path = (ROUTES.find((r) => r.path === u.pathname)?.path ?? '/overview') as RoutePath;
  return { path, params: u.searchParams, href };
}

export function navigate(path: string, params?: Record<string, string | undefined | null>, opts: { replace?: boolean } = {}) {
  const u = new URL(path, window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => { if (v) u.searchParams.set(k, v); });
  const next = u.pathname + u.search;
  if (next === snapshot()) return;
  if (opts.replace) window.history.replaceState(null, '', next); else window.history.pushState(null, '', next);
  emit();
}

/** Update some query params on the current route, keeping the rest. */
export function setParams(patch: Record<string, string | undefined | null>, opts: { replace?: boolean } = {}) {
  const u = new URL(window.location.href);
  Object.entries(patch).forEach(([k, v]) => { if (v) u.searchParams.set(k, v); else u.searchParams.delete(k); });
  navigate(u.pathname + u.search, undefined, opts);
}
