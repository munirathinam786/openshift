import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { build } from 'esbuild';

const outfile = resolve('docs/assets/javascripts/app-shell.js');

await mkdir(dirname(outfile), { recursive: true });

await build({
  entryPoints: [resolve('ui/src/app-shell.jsx')],
  bundle: true,
  outfile,
  format: 'iife',
  platform: 'browser',
  target: ['es2020'],
  jsx: 'automatic',
  define: {
    'process.env.NODE_ENV': '"production"',
  },
  minify: true,
  sourcemap: false,
  legalComments: 'none',
  logLevel: 'info',
});
