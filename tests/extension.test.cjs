const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function loadScript(name, storage = {}, overrides = {}) {
  const timers = new Map();
  let timerId = 0;
  const context = {
    console: {log() {}, warn() {}, error() {}},
    setTimeout(callback, delay) { timers.set(++timerId, {callback, delay}); return timerId; },
    clearTimeout(id) { timers.delete(id); },
    AbortController, AbortSignal,
    fetch() { throw new Error('Unexpected network request'); },
    chrome: {
      runtime: {onMessage: {addListener() {}}},
      storage: {local: {
        async get(key) { return structuredClone(key === null ? storage : {[key]: storage[key]}); },
        async set(values) { Object.assign(storage, structuredClone(values)); },
        async remove(keys) { for (const key of keys) delete storage[key]; },
        async clear() { for (const key of Object.keys(storage)) delete storage[key]; },
      }},
    },
    ...overrides,
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../chrome-ex', name), 'utf8'), context);
  context.testTimers = timers;
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

const articleURL = 'https://www.hani.co.kr/article';

function backgroundFixture(settings, results) {
  const storage = {highlighterSettings: settings};
  const calls = [];
  const ctx = loadScript('background.js', storage, {
    async fetch(url, options) {
      if (url.endsWith('/models')) {
        return {ok: true, async json() { return {configuration_id: 'fixture-config'}; }};
      }
      assert.equal(url, `http://localhost:5001/${settings.mode === 'consensus' ? 'analyze_consensus' : 'analyze'}`);
      calls.push(JSON.parse(options.body));
      assert.ok(results.length, 'Unexpected analysis request');
      return {ok: true, async json() { return results.shift(); }};
    },
  });
  return {ctx, storage, calls};
}

async function analyze(ctx) {
  let reply;
  await ctx.handleGetHighlightSentences(articleURL, result => { reply = result; });
  assert.ok(reply, 'The message handler must respond');
  return reply;
}

test('partial consensus is retried and only the recovered complete result is cached', async () => {
  const partial = {success: true, count: 0, sentences: [], successful_providers: ['gemini'], failed_providers: ['mistral']};
  const complete = {...partial, successful_providers: ['gemini', 'mistral'], failed_providers: []};
  const {ctx, calls, storage} = backgroundFixture(
    {mode: 'consensus', providers: ['gemini', 'mistral']}, [partial, complete]);
  assert.deepEqual((await analyze(ctx)).failed_providers, ['mistral']);
  assert.equal(Object.keys(storage).filter(k => k.startsWith('cache_')).length, 0);
  assert.deepEqual((await analyze(ctx)).failed_providers, []);
  assert.deepEqual((await analyze(ctx)).failed_providers, []);
  assert.equal(calls.length, 2);
});

test('an existing partial browser cache entry is discarded', async () => {
  const settings = {mode: 'consensus', providers: ['gemini', 'mistral']};
  const {ctx, calls, storage} = backgroundFixture(settings, [
    {success: true, sentences: [], count: 0, failed_providers: []},
  ]);
  const key = ctx.getCacheKey(articleURL, {...settings, configurationId: 'fixture-config'});
  storage[key] = {timestamp: Date.now(), data: {success: true, failed_providers: ['mistral']}};
  assert.deepEqual((await analyze(ctx)).failed_providers, []);
  assert.equal(calls.length, 1);
});

test('single-provider results remain cacheable', async () => {
  const {ctx, calls} = backgroundFixture({mode: 'single', providers: ['mistral']}, [
    {success: true, count: 0, sentences: []},
  ]);
  assert.equal((await analyze(ctx)).success, true);
  assert.equal((await analyze(ctx)).success, true);
  assert.deepEqual(calls, [{url: articleURL, provider: 'mistral'}]);
});

test('failed analysis requests release their timeout', async () => {
  const ctx = loadScript('background.js', {}, {async fetch() { throw new Error('Offline'); }});
  const result = await ctx.fetchHighlightSentences(articleURL, {mode: 'single', providers: ['gemini']});
  assert.equal(result.success, false);
  assert.equal(result.error, 'Offline');
  assert.ok([...ctx.testTimers.values()].every(timer => timer.delay !== 90000));
});

for (const text of [
  '  앞부분. 첫   문장입니다. 뒷부분.',
  '앞부분. 첫\n\t문장입니다. 뒷부분.',
  '🙂 앞부분. 첫\u00a0\u00a0문장입니다. 뒷부분.',
]) {
  test(`highlight offsets preserve original text: ${JSON.stringify(text)}`, () => {
    const ctx = loadScript('content.js');
    ctx.original = text;
    const matches = vm.runInContext("state.highlightTargets = [{text: '첫 문장입니다.', reason: '이유'}]; findMatches(original, normalizeText(original))", ctx);
    assert.equal(matches.length, 1);
    assert.equal(matches[0].startIndex, text.indexOf('첫'));
    assert.equal(matches[0].endIndex, text.indexOf('뒷부분.') - 1);
    assert.equal(matches[0].text, text.slice(matches[0].startIndex, matches[0].endIndex));
  });
}

test('duplicate, overlapping and empty targets cannot duplicate page text', () => {
  const ctx = loadScript('content.js');
  const matches = vm.runInContext("state.highlightTargets = ['첫 문장입니다.', '문장입니다.', '첫 문장입니다.', '   ']; findMatches('첫 문장입니다.', '첫 문장입니다.')", ctx);
  assert.equal(matches.length, 1);
  assert.equal(matches[0].text, '첫 문장입니다.');
});

test('a sentence split across inline nodes keeps whitespace and original offsets', () => {
  const ctx = loadScript('content.js');
  ctx.nodes = ['앞부분. 첫', '  ', '문장', '입니다. 뒷부분.'].map(textContent => ({textContent}));
  const plans = vm.runInContext("state.highlightTargets = [{text: '첫 문장입니다.', reason: '이유'}]; planNodeHighlights(nodes)", ctx);
  assert.deepEqual(Array.from(plans, plan => Array.from(plan, match => match.text)), [
    ['첫'], ['  '], ['문장'], ['입니다.'],
  ]);
  for (const [index, plan] of plans.entries()) {
    for (const match of plan) {
      assert.equal(ctx.nodes[index].textContent.slice(match.startIndex, match.endIndex), match.text);
      assert.equal(match.metadata.reason, '이유');
    }
  }
});

test('all non-overlapping occurrences are highlighted', () => {
  const ctx = loadScript('content.js');
  const matches = vm.runInContext("state.highlightTargets = ['문장.']; findMatches('문장. 중간. 문장.')", ctx);
  assert.deepEqual(Array.from(matches, match => [match.startIndex, match.endIndex]), [[0, 3], [8, 11]]);
});

test('text runs join inline markup but stop at blocks and excluded descendants', () => {
  const text = textContent => ({nodeType: 3, textContent});
  const element = (tagName, ...childNodes) => ({nodeType: 1, tagName, childNodes});
  const root = element('BODY',
    element('P', text('첫'), element('EM', text(' 문장.'))),
    element('P', text('다음'), element('SCRIPT', element('SPAN', text('제외'))), text('문장.')),
    element('P', text('줄'), element('BR'), text('바꿈.')),
    element('MARK', element('SPAN', text('기존 하이라이트'))));
  const ctx = loadScript('content.js');
  const runs = ctx.collectTextRuns(root);
  assert.deepEqual(Array.from(runs, nodes => Array.from(nodes, node => node.textContent).join('')),
    ['첫 문장.', '다음', '문장.', '줄', '바꿈.']);
});

test('cache expiry uses a controlled clock and triggers another analysis', async () => {
  const result = {success: true, sentences: [], count: 0};
  const {ctx, calls} = backgroundFixture({mode: 'single', providers: ['gemini']}, [result, result]);
  let now = 1000;
  ctx.Date = class extends Date { static now() { return now; } };
  await analyze(ctx);
  now += 60 * 60 * 1000;
  await analyze(ctx);
  assert.equal(calls.length, 2);
});

test('a body-read failure also releases the request timeout', async () => {
  const ctx = loadScript('background.js', {}, {
    async fetch() {
      return {ok: true, async json() {
        assert.ok([...ctx.testTimers.values()].some(timer => timer.delay === 90000));
        throw new Error('Broken response');
      }};
    },
  });
  const result = await ctx.fetchHighlightSentences(articleURL, {mode: 'single', providers: ['gemini']});
  assert.equal(result.success, false);
  assert.equal(result.error, 'Broken response');
  assert.ok([...ctx.testTimers.values()].every(timer => timer.delay !== 90000));
});
