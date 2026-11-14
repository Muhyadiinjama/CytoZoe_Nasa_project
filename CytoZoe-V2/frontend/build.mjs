// Production build: bundles src/main.tsx (+ CSS) into dist/assets and copies index.html and fonts.
// esbuild is used in place of Vite (Vite could not be installed on the build machine); output is equivalent static files.
import * as esbuild from 'esbuild';
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';

const watch = process.argv.includes('--watch');
rmSync('dist', { recursive: true, force: true });
mkdirSync('dist/assets', { recursive: true });
const opts = {
  entryPoints: ['src/main.tsx'], bundle: true, outdir: 'dist/assets', format: 'esm', target: ['es2020'],
  jsx: 'automatic', minify: !watch, sourcemap: watch ? 'inline' : false, metafile: true, logLevel: 'info',
  define: { 'process.env.NODE_ENV': watch ? '"development"' : '"production"' },
  loader: { '.otf': 'file' }, external: ['/fonts/*'],
};
const finish = () => {
  const js = readFileSync('dist/assets/main.js'); const css = readFileSync('dist/assets/main.css');
  const v = createHash('sha256').update(js).update(css).digest('hex').slice(0, 10);
  const html = readFileSync('index.html', 'utf8').replaceAll('%V%', v);
  writeFileSync('dist/index.html', html);
  cpSync('public/fonts', 'dist/fonts', { recursive: true });
  console.log('dist ready', v);
};
if (watch) { const ctx = await esbuild.context({ ...opts, plugins: [{ name: 'done', setup(b) { b.onEnd(finish); } }] }); await ctx.watch(); }
else { await esbuild.build(opts); finish(); }
