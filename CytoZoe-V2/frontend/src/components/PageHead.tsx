import type { ReactNode } from 'react';
export function PageHead({ title, purpose, chips }: { title: string; purpose: string; chips?: ReactNode }) {
  return (
    <div className="topbar">
      <div className="lead"><h1 id="page-title" tabIndex={-1}>{title}</h1><p>{purpose}</p></div>
      <div className="chips">{chips}</div>
    </div>
  );
}
