import { readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

const repoRoot = resolve(import.meta.dirname, '..');
const scriptsDir = join(repoRoot, 'docs', 'assets', 'javascripts');
const excludedFiles = new Set(['app-shell.js']);

const scriptFiles = readdirSync(scriptsDir)
  .filter((entry) => entry.endsWith('.js'))
  .filter((entry) => !excludedFiles.has(entry))
  .sort();

if (!scriptFiles.length) {
  console.log('No authored docs JavaScript files found to validate.');
  process.exit(0);
}

const failures = [];

for (const fileName of scriptFiles) {
  const filePath = join(scriptsDir, fileName);
  const result = spawnSync(process.execPath, ['--check', filePath], {
    cwd: repoRoot,
    encoding: 'utf8',
  });

  if (result.status !== 0) {
    failures.push({
      fileName,
      output: [result.stdout, result.stderr].filter(Boolean).join('\n').trim(),
    });
    continue;
  }

  console.log(`✓ Syntax OK: docs/assets/javascripts/${fileName}`);
}

if (failures.length) {
  console.error('\nDocs JavaScript syntax validation failed.');
  for (const failure of failures) {
    console.error(`\n--- ${failure.fileName} ---`);
    console.error(failure.output || 'Unknown syntax validation error.');
  }
  process.exit(1);
}

console.log(`\nValidated ${scriptFiles.length} authored docs JavaScript file(s).`);
