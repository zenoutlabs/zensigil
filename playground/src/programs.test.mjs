import test from 'node:test';
import assert from 'node:assert/strict';
import {blankProgram, decodeProgram, encodeProgram, validateProgram, readLibrary, decodeDraft, readSavedProgram, removeSavedProgram, sourceSelection} from './programs.mjs';
test('portable programs preserve invalid raw drafts exactly', () => {
  const original = {...blankProgram(), source: 'when :', data_text: '{broken', contract_text: '[broken'};
  assert.deepEqual(decodeProgram(encodeProgram(original)), original);
});
test('rejects unsupported file versions and malformed fields', () => {
  for (const change of [{format: 'other'}, {format_version: 2}, {language_version: '9'}, {name: ''}, {source: null}, {data_text: []}]) assert.throws(() => validateProgram({...blankProgram(), ...change}));
  assert.throws(() => decodeProgram('not json'));
});
test('enforces UTF-8 byte limits rather than character count', () => {
  assert.throws(() => validateProgram({...blankProgram(), source: '🙂'.repeat(16385)}));
  assert.doesNotThrow(() => validateProgram({...blankProgram(), source: '🙂'.repeat(16384)}));
  assert.throws(() => validateProgram({...blankProgram(), contract_text: 'x'.repeat(262145)}));
});
test('loads library only after validating all records', () => {
  assert.deepEqual(readLibrary({getItem: () => JSON.stringify({version: 1, programs: [{id: 'one', program: blankProgram()}]})}), [{id: 'one', program: blankProgram()}]);
  assert.throws(() => readLibrary({getItem: () => '{broken'}));
  assert.throws(() => readLibrary({getItem: () => JSON.stringify({version: 2, programs: []})}));
});

test('draft recovery preserves whitespace or unfinished names and invalid raw JSON', () => {
  for (const name of ['', '   ', '\t ']) {
    const original = {...blankProgram(), name, source: 'when :', data_text: '{unfinished', contract_text: '[unfinished'};
    assert.deepEqual(decodeDraft(JSON.stringify({version: 1, program: original})), original);
    assert.throws(() => encodeProgram(original), /name/);
  }
  assert.throws(() => decodeDraft(JSON.stringify({version: 2, program: blankProgram()})));
  assert.throws(() => decodeDraft(JSON.stringify({version: 1, program: {...blankProgram(), name: null}})));
});
test('delayed saved-program opening reads the snapshot written by Save & open', () => {
  let stored = JSON.stringify({version: 1, programs: [{id: 'same', program: blankProgram()}]});
  const storage = {getItem: () => stored};
  const openLater = () => readSavedProgram(storage, 'same');
  const edited = {...blankProgram(), source: 'say "Latest edited source"', data_text: '{unfinished'};
  stored = JSON.stringify({version: 1, programs: [{id: 'same', program: edited}]});
  assert.deepEqual(openLater(), edited);
  assert.throws(() => readSavedProgram(storage, 'removed'), /no longer available/);
});

test('migrates v0.2 portable files, browser library, and unfinished drafts losslessly', () => {
  const old = {...blankProgram(), language_version: '0.2.0', data_text: '{unfinished', contract_text: '[unfinished'};
  delete old.proposal_contract_text;
  const expected = {...old, language_version: '0.8.0', proposal_contract_text: ''};
  assert.deepEqual(decodeProgram(JSON.stringify(old)), expected);
  assert.deepEqual(readLibrary({getItem: () => JSON.stringify({version: 1, programs: [{id: 'old', program: old}]})})[0].program, expected);
  assert.deepEqual(decodeDraft(JSON.stringify({version: 1, program: {...old, name: ' '}})), {...expected, name: ' '});
});
test('proposal contracts preserve raw drafts and reject malformed fields or unknown keys', () => {
  const draft = {...blankProgram(), proposal_contract_text: '{unfinished'};
  assert.deepEqual(decodeProgram(encodeProgram(draft)), draft);
  for (const extra of [{proposal_contract_text: null}, {proposal_contract_text: {}}, {surprise: true}, {proposal_contract_text: 'x'.repeat(262145)}]) assert.throws(() => validateProgram({...blankProgram(), ...extra}));
});
test('deletion re-reads storage and preserves another tab’s most recent save', () => {
  let saved = [{id: 'delete-me', program: blankProgram()}];
  const storage = {getItem: () => JSON.stringify({version: 1, programs: saved}), setItem: (_, value) => {saved = JSON.parse(value).programs;}};
  saved.push({id: 'other-tab', program: {...blankProgram(), name: 'Other tab'}});
  assert.deepEqual(removeSavedProgram(storage, 'delete-me').map(item => item.id), ['other-tab']);
  assert.deepEqual(saved.map(item => item.id), ['other-tab']);
  assert.throws(() => removeSavedProgram(storage, 'delete-me'), /no longer available/);
});
test('failed deletion never reports success or changes the stored library', () => {
  const original = [{id: 'keep', program: blankProgram()}];
  const storage = {getItem: () => JSON.stringify({version: 1, programs: original}), setItem: () => {throw new Error('Storage unavailable');}};
  assert.throws(() => removeSavedProgram(storage, 'keep'), /Storage unavailable/);
  assert.deepEqual(readLibrary(storage), original);
});
test('source jumps target the reported line and clamp out-of-range coordinates', () => {
  assert.deepEqual(sourceSelection('say "ok"\n    missing\nsay "end"', 2, 5), {start: 13, end: 20, index: 1});
  assert.deepEqual(sourceSelection('abc', 99, 99), {start: 3, end: 3, index: 0});
  assert.deepEqual(sourceSelection('abc', -2, -1), {start: 0, end: 3, index: 0});
});

test('portable imports reject duplicate outer fields, including escaped key spellings', () => {
  const text = encodeProgram(blankProgram());
  assert.throws(() => decodeProgram(text.replace('"name":', '"name":"ambiguous", "name":')), /Duplicate/);
  assert.throws(() => decodeProgram(text.replace('"name":', '"na\\u006de":"ambiguous", "name":')), /Duplicate/);
  assert.deepEqual(decodeProgram(encodeProgram({...blankProgram(), source: 'say "name: {x}"'})).source, 'say "name: {x}"');
});
test('source locations translate Unicode code-point columns to textarea offsets', () => {
  assert.deepEqual(sourceSelection('"🙂" + missing', 1, 7), {start: 7, end: 14, index: 0});
});

test('portable text rejects unpaired Unicode surrogates and accepts valid emoji pairs', () => {
  for (const field of ['name', 'source', 'data_text', 'contract_text', 'proposal_contract_text']) {
    for (const value of ['\ud800', '\udc00', 'x\ud800x', '\ud800\ud800']) assert.throws(() => validateProgram({...blankProgram(), [field]: value}), /Unicode/);
    assert.doesNotThrow(() => validateProgram({...blankProgram(), [field]: '🙂'}));
  }
});
