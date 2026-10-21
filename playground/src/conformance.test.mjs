import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {decodeProgram} from './programs.mjs';

const fixtures = JSON.parse(await readFile(new URL('../../tests/fixtures/portable-cases.json', import.meta.url), 'utf8'));
for (const fixture of fixtures) {
  test(`shared portable fixture: ${fixture.name}`, () => {
    if (fixture.valid) {
      const result = decodeProgram(fixture.text);
      assert.equal(result.language_version, '0.7.0');
      assert.equal(result.data_text, '{unfinished');
    } else {
      assert.throws(() => decodeProgram(fixture.text));
    }
  });
}
