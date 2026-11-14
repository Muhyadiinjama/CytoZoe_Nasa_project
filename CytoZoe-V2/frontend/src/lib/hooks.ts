import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/client';

export interface Async<T> { data: T | null; error: ApiError | null; loading: boolean; reload: () => void }

/** Load data for the current inputs; stale responses are ignored. */
export function useAsync<T>(fn: () => Promise<T>, deps: readonly unknown[]): Async<T> {
  const [state, setState] = useState<{ data: T | null; error: ApiError | null; loading: boolean }>({ data: null, error: null, loading: true });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    fn().then((data) => { if (live) setState({ data, error: null, loading: false }); })
      .catch((e: unknown) => { if (live) setState({ data: null, error: e instanceof ApiError ? e : new ApiError(0, 'UNEXPECTED', String(e)), loading: false }); });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}

/** Width of an element, updated on resize (charts redraw to fit). */
export function useWidth<T extends HTMLElement>(): [{ current: T | null }, number] {
  const ref = useRef<T | null>(null);
  const [w, setW] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const update = () => setW(Math.round(el.getBoundingClientRect().width));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

/** Small app-wide event bus so a save in a drawer refreshes the page behind it. */
const bus = new Set<() => void>();
export const reviewsChanged = () => bus.forEach((f) => f());
export function useReviewsChanged(cb: () => void) {
  useEffect(() => { bus.add(cb); return () => { bus.delete(cb); }; }, [cb]);
}
