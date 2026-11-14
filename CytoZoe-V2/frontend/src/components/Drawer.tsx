import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';

/** Modal side drawer: focus moves to the title, Tab stays inside, Escape closes, focus returns to the opener. */
export function Drawer({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const id = useId();
  const ref = useRef<HTMLElement | null>(null);
  const opener = useRef<Element | null>(document.activeElement);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const root = document.getElementById('root');
    root?.setAttribute('inert', '');
    root?.setAttribute('aria-hidden', 'true');
    (document.getElementById(id + 't') as HTMLElement | null)?.focus();
    const back = opener.current;
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.preventDefault(); closeRef.current(); } };
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('keydown', esc);
      root?.removeAttribute('inert');
      root?.removeAttribute('aria-hidden');
      if (back instanceof HTMLElement && document.contains(back)) back.focus();
    };
  }, [id]);
  const onKey = (e: { key: string; shiftKey: boolean; preventDefault(): void }) => {
    if (e.key !== 'Tab' || !ref.current) return;
    const f = Array.from(ref.current.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, iframe, [tabindex]:not([tabindex="-1"])'))
      .filter((x) => !(x as HTMLButtonElement).disabled && x.offsetParent !== null);
    if (!f.length) return;
    const first = f[0], last = f[f.length - 1], a = document.activeElement;
    if (e.shiftKey && (a === first || a === document.getElementById(id + 't'))) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && a === last) { e.preventDefault(); first.focus(); }
  };
  const host = document.getElementById('drawer-root');
  if (!host) return null;
  return createPortal(
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby={id + 't'} ref={ref} onKeyDown={onKey}>
        <div className="drawer-head">
          <h2 id={id + 't'} tabIndex={-1}>{title}</h2>
          <button className="btn" type="button" onClick={onClose} data-testid="drawer-close">Close</button>
        </div>
        <div className="drawer-body">{children}</div>
      </aside>
    </>, host);
}
