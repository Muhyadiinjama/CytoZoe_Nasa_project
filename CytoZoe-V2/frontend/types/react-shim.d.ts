/* Minimal React 19 declarations for the APIs used by CytoZoe (see types/README.md). */
declare module 'react' {
  export type ReactNode = ReactElement | string | number | bigint | boolean | null | undefined | Iterable<ReactNode>;
  export interface ReactElement { type: unknown; props: unknown; key: string | null }
  export type Key = string | number;
  export type SetStateAction<S> = S | ((prev: S) => S);
  export type Dispatch<A> = (value: A) => void;
  export interface RefObject<T> { current: T }
  export type DependencyList = readonly unknown[];
  export type FC<P = Record<string, never>> = (props: P) => ReactNode;
  export interface SyntheticEvent<T = Element> { currentTarget: T; target: EventTarget; preventDefault(): void; stopPropagation(): void }
  export interface KeyboardEvent<T = Element> extends SyntheticEvent<T> { key: string; shiftKey: boolean; ctrlKey: boolean; metaKey: boolean; altKey: boolean }
  export interface MouseEvent<T = Element> extends SyntheticEvent<T> { clientX: number; clientY: number; button: number; ctrlKey: boolean; metaKey: boolean; shiftKey: boolean; altKey: boolean }
  export interface PointerEvent<T = Element> extends MouseEvent<T> { pointerType: string }
  export interface ChangeEvent<T = Element> extends SyntheticEvent<T> { target: EventTarget & T }
  export interface FormEvent<T = Element> extends SyntheticEvent<T> {}
  export function useState<S>(initial: S | (() => S)): [S, Dispatch<SetStateAction<S>>];
  export function useState<S = undefined>(): [S | undefined, Dispatch<SetStateAction<S | undefined>>];
  export function useEffect(effect: () => void | (() => void), deps?: DependencyList): void;
  export function useLayoutEffect(effect: () => void | (() => void), deps?: DependencyList): void;
  export function useMemo<T>(factory: () => T, deps: DependencyList): T;
  export function useCallback<T extends (...args: never[]) => unknown>(cb: T, deps: DependencyList): T;
  export function useRef<T>(initial: T): RefObject<T>;
  export function useRef<T>(initial: T | null): RefObject<T | null>;
  export function useId(): string;
  export function useSyncExternalStore<T>(subscribe: (cb: () => void) => () => void, get: () => T, getServer?: () => T): T;
  export function createContext<T>(value: T): Context<T>;
  export function useContext<T>(ctx: Context<T>): T;
  export interface Context<T> { Provider: (p: { value: T; children?: ReactNode }) => ReactNode; _t?: T }
  export const Fragment: (p: { children?: ReactNode }) => ReactNode;
  export const StrictMode: (p: { children?: ReactNode }) => ReactNode;
  const React: { StrictMode: typeof StrictMode };
  export default React;
}
declare module 'react/jsx-runtime' {
  export const jsx: unknown; export const jsxs: unknown; export const Fragment: unknown;
}
declare module 'react-dom/client' {
  import type { ReactNode } from 'react';
  export interface Root { render(node: ReactNode): void; unmount(): void }
  export function createRoot(el: Element): Root;
}
declare module 'react-dom' {
  import type { ReactNode } from 'react';
  export function createPortal(node: ReactNode, container: Element): ReactNode;
}
declare namespace JSX {
  type Element = import('react').ReactElement;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  type ElementType = string | ((props: any) => import('react').ReactNode);
  interface ElementChildrenAttribute { children: unknown }
  interface IntrinsicAttributes { key?: import('react').Key }
  // Attributes are checked loosely here; real @types/react gives full checking.
  interface IntrinsicElements { [el: string]: Record<string, unknown> }
}

declare module '*.css';
