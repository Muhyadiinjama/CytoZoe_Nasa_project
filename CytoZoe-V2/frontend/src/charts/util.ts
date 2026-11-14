export function niceTicks(lo: number, hi: number, n: number): number[] {
  const span = hi - lo || 1, raw = span / n, p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p;
  const step = (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
  const out: number[] = [];
  for (let t = Math.ceil(lo / step - 1e-9) * step; ; t += step) { out.push(+t.toFixed(10)); if (t >= hi - step * 1e-6 || out.length > 50) break; }
  return out;
}
export const C = { grid: '#DCE4EB', teal: '#087F8C', review: '#9A4B08', reviewBg: '#FFF3DF', band: '#E8F5F5', base: '#64748B', ink: '#14283F', ctrl: '#728297', focus: '#2458D3' };
export function hourTicks(t0: number, t1: number): number[] {
  const hrs = (t1 - t0) / 3.6e6, step = (hrs > 12 ? 3 : hrs > 6 ? 2 : 1) * 3.6e6;
  const start = Math.ceil(t0 / 3.6e6) * 3.6e6, out: number[] = [];
  for (let t = start; t <= t1; t += step) out.push(t);
  return out;
}
export const hh = (t: number) => String(new Date(t).getUTCHours()).padStart(2, '0') + ':00'; // source clock, no timezone conversion
