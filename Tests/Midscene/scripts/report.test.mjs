import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, rm, access } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { assemble } from './report.mjs';
import { collect } from './collect.mjs';
async function fixture(fn) {
  const root = await mkdtemp(path.join(tmpdir(), 'search-report-'));
  try {
    const dir = path.join(root, 'shard'); await mkdir(dir);
    const cases = await collect();
    for (const c of cases) {
      await writeFile(path.join(dir, `${c.id}.html`), 'native placeholder');
      await writeFile(path.join(dir, `${c.id}.png`), 'png placeholder');
    }
    await writeFile(path.join(dir, 'results.json'), JSON.stringify(cases.map(c => ({ id: c.id, status: 'passed', report: `${c.id}.html`, screenshot: `${c.id}.png` }))));
    await fn(root, dir);
  } finally { await rm(root, { recursive: true, force: true }); }
}
const opts = root => ({ directory: root, baseUrl: 'https://example.test/runs/123/2', summary: path.join(root, 'summary.md') });
const merge = async ({ outputDir }) => {
  const mergedReportPath = path.join(outputDir, 'native.html');
  await mkdir(path.dirname(mergedReportPath), { recursive: true }); await writeFile(mergedReportPath, 'merged');
  return { mergedReportPath };
};
test('complete table links to exact reports and screenshots', () => fixture(async root => {
  assert.equal(await assemble({ ...opts(root), merge }), true);
  const summary = await readFile(opts(root).summary, 'utf8');
  assert.match(summary, /https:\/\/example.test\/runs\/123\/2\/shard\/bookmarks-import.html/);
  assert.match(summary, /!\[screenshot\]/);
}));
test('failed merge keeps per-case files and deletes partial output', () => fixture(async (root, dir) => {
  assert.equal(await assemble({ ...opts(root), merge: async args => { await merge(args); throw new Error('merge failed'); } }), false);
  await access(path.join(dir, 'bookmarks-import.html'));
  await assert.rejects(access(path.join(root, 'native.html')));
  assert.match(await readFile(opts(root).summary, 'utf8'), /Individual reports remain/);
}));
test('incomplete rerun removes old merge and reports missing cases', () => fixture(async (root, dir) => {
  await assemble({ ...opts(root), merge });
  await writeFile(path.join(dir, 'results.json'), '[]');
  assert.equal(await assemble({ ...opts(root), merge }), false);
  await assert.rejects(access(path.join(root, 'native.html')));
  assert.match(await readFile(opts(root).summary, 'utf8'), /missing/);
}));
test('unknown shards fail rather than silently running nothing', async () => {
  await assert.rejects(collect('typo'), /No cases/);
});
test('SDK native standalone HTML merges without a model or desktop', () => fixture(async (root, dir) => {
  const { Agent, mergeReportFiles } = await import('@midscene/core');
  const agent = new Agent({ interfaceType: 'static', actionSpace: () => [], destroy: async () => {} }, { generateReport: false });
  try {
    // Record a synthetic log using the SDK rather than inventing its HTML schema.
    await agent.recordToReport('Synthetic harness entry', { content: 'No model call', screenshots: [{ base64: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aC9sAAAAASUVORK5CYII=' }] });
    const html = agent.reportHTMLString({ inlineScreenshots: true });
    for (const c of await collect()) await writeFile(path.join(dir, `${c.id}.html`), html);
    assert.equal(await assemble({ ...opts(root), merge: mergeReportFiles }), true);
    const merged = await readFile(path.join(root, 'native.html'), 'utf8');
    assert.match(merged, /Synthetic harness entry/);
  } finally { await agent.destroy(); }
}));
