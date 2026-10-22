import test from 'node:test';
import assert from 'node:assert/strict';
import {blankProgram, decodeProgram, encodeProgram, decodeDraft, readLibrary, editProgram} from './programs.mjs';
import {requestProgram} from './requests.mjs';

test('separate unfinished tests survive export, draft, and saved library', () => {
  const program = {...blankProgram(), tests: {'tests/math.zs': 'test "Still editing":\n    require ('}};
  assert.deepEqual(decodeProgram(encodeProgram(program)), program);
  assert.deepEqual(decodeDraft(JSON.stringify({version: 1, program})), program);
  assert.deepEqual(readLibrary({getItem: () => JSON.stringify({version: 1, programs: [{id: 'one', program}]})})[0].program, program);
});
test('old programs get an empty tests map', () => {
  const old = {...blankProgram(), language_version: '0.7.0'}; delete old.tests;
  assert.deepEqual(decodeProgram(JSON.stringify(old)).tests, {});
});
test('test source limits and cross-map collisions match the portable contract', () => {
  for (const tests of [null, [], {'../outside.zs': ''}, {'tests.zs': 'x'.repeat(65537)},
    {'Lib/math.zs': ''}, {'lib/math.zs/child.zs': ''}, {'lib/math.zs': 'different'}]) {
    assert.throws(() => encodeProgram({...blankProgram(), modules: {'lib/math.zs': ''}, tests}));
  }
  assert.doesNotThrow(() => encodeProgram({...blankProgram(), modules: {'lib/math.zs': 'same'}, tests: {'lib/math.zs': 'same'}}));
});
test('run preview does not send separate tests; test requests do', async () => {
  const program = {...blankProgram(), tests: {'tests/case.zs': 'test "Case":\n    require true, "ok"\n'}};
  for (const mode of ['run', 'check', 'test', 'lint', 'format']) {
    let payload;
    await requestProgram(mode, program, {fetcher: async (_, options) => {
      payload = JSON.parse(options.body); return {ok: true, json: async () => ({ok: true})};
    }});
    if (mode === 'test') assert.deepEqual(payload.tests, program.tests);
    else assert.equal(Object.hasOwn(payload, 'tests'), false);
  }
});
test('export rejects a document larger than its import limit after escaping', () => {
  const raw = '\u0000';
  const modules = Object.fromEntries(Array.from({length: 4}, (_, i) => [`lib/m${i}.zs`, raw.repeat(65536)]));
  const tests = Object.fromEntries(Array.from({length: 4}, (_, i) => [`tests/t${i}.zs`, raw.repeat(65536)]));
  assert.throws(() => encodeProgram({...blankProgram(), source: raw.repeat(65536), data_text: raw.repeat(1048576),
    contract_text: raw.repeat(262144), proposal_contract_text: raw.repeat(262144), modules, tests}), /10 MiB/);
});

test('entry identity survives exports and rejects ambiguous paths', () => {
  const program = {...blankProgram(), entry_path: 'src/main.zs'};
  assert.deepEqual(decodeProgram(encodeProgram(program)), program);
  for (const entry_path of [null, '', '../main.zs', 'main.txt']) assert.throws(() => encodeProgram({...program, entry_path}));
  assert.throws(() => encodeProgram({...program, modules: {'SRC/main.zs': program.source}}));
  assert.throws(() => encodeProgram({...program, tests: {'src/main.zs': 'different'}}));
});
test('editing a shared source path updates all roles of that file', () => {
  const original = {...blankProgram(), entry_path: 'main.zs', source: 'same',
    modules: {'main.zs': 'same', 'lib.zs': 'keep'}, tests: {'main.zs': 'same'}};
  for (const [field, value] of [['source', 'new'], ['modules', {...original.modules, 'main.zs': 'new'}], ['tests', {'main.zs': 'new'}]]) {
    const changed = editProgram(original, field, value);
    assert.equal(changed.source, 'new'); assert.equal(changed.modules['main.zs'], 'new'); assert.equal(changed.tests['main.zs'], 'new');
    assert.equal(changed.modules['lib.zs'], 'keep'); assert.equal(original.source, 'same');
    assert.doesNotThrow(() => encodeProgram(changed));
  }
});
