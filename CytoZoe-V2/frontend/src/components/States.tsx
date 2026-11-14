import type { ReactNode } from 'react';
import type { ApiError } from '../api/client';

export function Skeleton({ label, height = 160 }: { label: string; height?: number }) {
  return <div className="skeleton" style={{ minHeight: height }} role="status" aria-live="polite"><span className="sr-only">{label}</span></div>;
}

export function ErrorNotice({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  return (
    <div className="notice error" role="alert">
      <strong>{error.status === 0 ? 'Local service unavailable. ' : 'Could not load this. '}</strong>
      {error.message} {error.code && error.status !== 0 ? <span className="meta">({error.code})</span> : null}
      {onRetry ? <div style={{ marginTop: 8 }}><button className="btn small" type="button" onClick={onRetry}>Try again</button></div> : null}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="empty"><h2>{title}</h2>{children}</div>;
}

export function Notice({ kind, children }: { kind: 'info' | 'success' | 'error'; children: ReactNode }) {
  return <div className={`notice ${kind}`} role={kind === 'error' ? 'alert' : 'status'}>{children}</div>;
}
