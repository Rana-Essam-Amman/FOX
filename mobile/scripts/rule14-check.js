#!/usr/bin/env node
/**
 * Rule 14 line-count guard.
 * Classifies source files by path and enforces maximum line counts.
 * Renaming an oversized screen into another directory still fails the relevant limit.
 */
/* eslint-disable no-undef */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const LIMITS = {
  screen: 150,
  component: 120,
  hook: 100,
  helper: 80,
  service: 150,
  style: 200,
};

function classify(rel) {
  const n = rel.replace(/\\/g, '/');
  if (n.startsWith('app/') && n.endsWith('.tsx') && !n.endsWith('/_layout.tsx')) return 'screen';
  if (n.includes('/components/') && n.endsWith('.tsx')) return 'component';
  if (n.includes('/hooks/') && (n.endsWith('.ts') || n.endsWith('.tsx'))) return 'hook';
  if (n.includes('/i18n/') || n.endsWith('/i18n.ts')) return null;
  if (n.includes('/styles/') && n.endsWith('.ts')) return 'style';
  if (n.includes('/services/') && n.endsWith('.ts')) return 'service';
  if (n.endsWith('.ts') && !n.endsWith('.test.ts') && !n.endsWith('.d.ts') && !n.includes('node_modules')) return 'helper';
  return null;
}

function walk(dir, acc = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name === 'dist' || entry.name.startsWith('.')) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, acc);
    else if (/\.(ts|tsx)$/.test(entry.name) && !entry.name.endsWith('.test.ts') && !entry.name.endsWith('.test.tsx')) acc.push(full);
  }
  return acc;
}

const files = walk(ROOT);
const violations = [];

for (const file of files) {
  const rel = path.relative(ROOT, file);
  const kind = classify(rel);
  if (!kind) continue;
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/).length;
  const limit = LIMITS[kind];
  if (lines > limit) {
    violations.push({ rel, kind, lines, limit });
  }
}

if (violations.length) {
  console.error('Rule 14 violations:');
  for (const v of violations) {
    console.error(`  ${v.rel}: ${v.lines} lines (${v.kind}, max ${v.limit})`);
  }
  process.exit(1);
}

console.log(`Rule 14: ${files.length} files checked, no violations.`);
