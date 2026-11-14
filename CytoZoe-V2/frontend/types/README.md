`react-shim.d.ts` is a minimal stand-in for `@types/react` / `@types/react-dom`, which could not be installed on the
build machine (no package downloads). It declares only the React APIs this app uses, so `npm run typecheck` still
checks all of the app's own code in strict mode. On a machine with internet, run `npm i -D @types/react @types/react-dom`,
delete `react-shim.d.ts`, remove `"types": []` and `"typeRoots"` from tsconfig.json, and re-run `npm run typecheck`.
