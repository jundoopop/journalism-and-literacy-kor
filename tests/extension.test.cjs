const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function loadScript(name, storage = {}) {
  const context = {
    console: {log() {}, warn() {}, error() {}},
    setTimeout() {}, clearTimeout() {},
    chrome: {
      runtime: {onMessage: {addListener() {}}},
      storage: {local: {
        async get(key) { return key === null ? {...storage} : {[key]: storage[key]}; },
        async remove(keys) { for (const key of keys) delete storage[key]; },
        async clear() { for (const key of Object.keys(storage)) delete storage[key]; },
      }},
    },
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../chrome-ex', name), 'utf8'), context);
  return context;
}

test('clearing analysis cache preserves saved settings', async () => {
  const storage = {highlighterSettings: {mode: 'consensus'}, cache_old: {timestamp: 0}};
  const ctx = loadScript('background.js', storage);
  await vm.runInContext('clearAllCache()', ctx);
  assert.deepEqual(storage, {highlighterSettings: {mode: 'consensus'}});
});

test('single and consensus reasons cannot inject HTML', () => {
  const ctx = loadScript('content.js');
  ctx.attack = '<img src=x onerror="alert(1)">';
  for (const metadata of [
    {reason: ctx.attack},
    {consensus_score: 1, consensus_level: 'insufficient',
     selected_by: ['gemini'], reasons: {gemini: ctx.attack}},
  ]) {
    ctx.metadata = metadata;
    const html = vm.runInContext('tooltipManager.buildTooltipContent(metadata)', ctx);
    assert.ok(!html.includes('<img'));
    assert.ok(html.includes('&lt;img'));
  }
});
