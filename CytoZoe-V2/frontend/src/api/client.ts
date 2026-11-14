/* The only place that talks to the local service. Same origin; no other hosts are ever contacted. */
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details: Record<string, unknown> = {}) { super(message); }
}

export async function api<T>(method: 'GET' | 'POST' | 'PATCH', path: string, body?: unknown, opts: { raw?: Blob; timeoutMs?: number } = {}): Promise<T> {
  const ctl = new AbortController();
  const timer = window.setTimeout(() => ctl.abort(), opts.timeoutMs ?? 30000);
  let res: Response;
  try {
    res = await fetch(path, {
      method, signal: ctl.signal, credentials: 'same-origin',
      headers: opts.raw ? { 'Content-Type': 'text/csv' } : body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: opts.raw ?? (body !== undefined ? JSON.stringify(body) : undefined),
    });
  } catch {
    throw new ApiError(0, 'SERVICE_UNAVAILABLE', 'The local CytoZoe service is not responding. Check that it is still running, then try again.');
  } finally {
    window.clearTimeout(timer);
  }
  const text = await res.text();
  let data: unknown = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }
  if (!res.ok) {
    const d = (data ?? {}) as { code?: string; message?: string; details?: Record<string, unknown> };
    throw new ApiError(res.status, d.code ?? 'HTTP_' + res.status, d.message ?? 'The local service returned an error.', d.details ?? {});
  }
  return data as T;
}

export const get = <T,>(p: string) => api<T>('GET', p);
export const qs = (o: Record<string, string | number | undefined | null>) =>
  Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== '').map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join('&');
