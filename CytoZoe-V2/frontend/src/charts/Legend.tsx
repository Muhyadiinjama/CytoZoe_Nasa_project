import { C } from './util';
export function Swatch({ kind }: { kind: 'dot' | 'diamond' | 'dash' | 'band' | 'excl' | 'line' }) {
  return (
    <svg width={22} height={14} viewBox="0 0 22 14" aria-hidden="true">
      {kind === 'dot' ? <circle cx={11} cy={7} r={5} fill={C.teal} /> : null}
      {kind === 'diamond' ? <path d="M11 1 L17 7 L11 13 L5 7 Z" fill={C.review} /> : null}
      {kind === 'dash' ? <line x1={1} x2={21} y1={7} y2={7} stroke={C.base} strokeWidth={2} strokeDasharray="5 4" /> : null}
      {kind === 'band' ? <rect x={1} y={2} width={20} height={10} fill={C.band} stroke={C.grid} /> : null}
      {kind === 'excl' ? <rect x={1} y={1} width={20} height={12} fill={C.reviewBg} stroke={C.review} /> : null}
      {kind === 'line' ? <line x1={1} x2={21} y1={7} y2={7} stroke={C.teal} strokeWidth={2} /> : null}
    </svg>
  );
}
