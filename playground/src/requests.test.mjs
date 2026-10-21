import test from 'node:test';
import assert from 'node:assert/strict';
import {requestProgram} from './requests.mjs';
import {blankProgram} from './programs.mjs';

test('check request carries optional input and proposal contracts without parsing raw drafts', async () => {
  let call;
  const program = {...blankProgram(), contract_text: '{input', proposal_contract_text: '{output'};
  const result = await requestProgram('check', program, {fetcher: async (url, options) => {
    call = {url, payload: JSON.parse(options.body)};
    return {ok: true, json: async () => ({ok: false, diagnostics: [{code: 'E_CONTRACT'}]})};
  }});
  assert.equal(call.url, '/api/check');
  assert.deepEqual(call.payload, {source: program.source, modules: {}, data_text: '{}', contract_text: '{input', proposal_contract_text: '{output'});
  assert.equal(result.ok, false);
});
test('empty optional contracts are omitted and an empty object remains active', async () => {
  let payload;
  await requestProgram('run', {...blankProgram(), contract_text: ' ', proposal_contract_text: '{}'}, {fetcher: async (_, options) => {
    payload = JSON.parse(options.body); return {ok: true, json: async () => ({ok: true})};
  }});
  assert.equal(Object.hasOwn(payload, 'contract_text'), false);
  assert.equal(payload.proposal_contract_text, '{}');
});
test('lint carries the active source, data, and modules and preserves advisory success', async () => {
  const program = {...blankProgram(), source: 'let n: integer = "text"\n', data_text: '{"count":2}', modules: {'lib/a.zs':'fn value():\n    return 1\n'}};
  const result = await requestProgram('lint', program, {fetcher: async (url, options) => {
    assert.equal(url, '/api/lint');
    assert.deepEqual(JSON.parse(options.body), {source:program.source, modules:program.modules, data_text:program.data_text});
    return {ok:true, json:async()=>({ok:true, mode:'lint', warnings:[{code:'W_TYPE', severity:'warning'}]})};
  }});
  assert.equal(result.ok, true);
  assert.equal(result.warnings[0].severity, 'warning');
});
test('timeout aborts stalled requests with a recoverable message', async () => {
  let aborted = false;
  const fetcher = (_, {signal}) => new Promise((_, reject) => signal.addEventListener('abort', () => {
    aborted = true; reject(new DOMException('Aborted', 'AbortError'));
  }, {once: true}));
  await assert.rejects(requestProgram('run', blankProgram(), {fetcher, timeoutMs: 5}), /draft is safe/);
  assert.equal(aborted, true);
});
test('editing cancellation propagates to pending fetches', async () => {
  const controller = new AbortController();
  const pending = requestProgram('run', blankProgram(), {signal: controller.signal, fetcher: (_, {signal}) => new Promise((_, reject) => {
    signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), {once: true});
  })});
  controller.abort();
  await assert.rejects(pending, {name: 'AbortError'});
});
test('HTTP failure is not treated as a successful program result', async () => {
  await assert.rejects(requestProgram('run', blankProgram(), {fetcher: async () => ({ok: false, json: async () => ({error: 'Request too large'})})}), /Request too large/);
});
test('isolated tests and formatting do not parse unrelated unfinished input JSON', async () => {
  for (const mode of ['test','format']) {
    let payload;
    const program = {...blankProgram(), data_text: '{unfinished', modules: {'lib/math.zs': 'fn two():\n    return 2\n'}};
    await requestProgram(mode, program, {fetcher: async (_, options) => {payload=JSON.parse(options.body); return {ok:true,json:async()=>({ok:true})};}});
    assert.equal(Object.hasOwn(payload,'data_text'),false);
    assert.deepEqual(payload.modules,program.modules);
  }
});
