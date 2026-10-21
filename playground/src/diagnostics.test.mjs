import test from 'node:test';
import assert from 'node:assert/strict';
import {hasSourceLocation} from './diagnostics.mjs';

test('input and contract sidecar diagnostics never pretend to point to source line one', () => {
  for (const code of ['E_INPUT_DATA', 'E_CONTRACT', 'E_PROPOSAL_CONTRACT']) {
    assert.equal(hasSourceLocation({code, line: 1, column: 1, source_line: '', output_path: '$.reserve.properties.count'}), false);
  }
});
test('runtime proposal and syntax errors retain their real source jump locations', () => {
  assert.equal(hasSourceLocation({code: 'E_PROPOSAL', line: 3, column: 5, source_line: '    propose reserve(count: 0)', output_path: '$.proposals[0].fields.count'}), true);
  assert.equal(hasSourceLocation({code: 'E_SYNTAX', line: 2, column: 1, source_line: 'when :'}), true);
  assert.equal(hasSourceLocation({line: 0, source_line: 'source'}), false);
  assert.equal(hasSourceLocation({line: 2}), false);
});
