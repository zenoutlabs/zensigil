# Runtime limits and source errors in 0.8

This change keeps the language grammar. It makes collection limits and source
errors more consistent. It does not make the interpreter a secure shared server.

## Collection results

`map` checks each callback result before it calls the callback for the next item.
Each result must be a JSON value. The growing result list must fit the normal
value limits: 20,000 nodes, 32 levels of nesting, and 1 MiB of UTF-8 text.
Repeated values count each time they occur in the result. The outer list adds a
node and a nesting level.

For example, this program fails at the first callback result:

```zensigil
fn transform(n):
    return choose n == 0 then abs otherwise 1 / 0

emit map([0, 1], transform)
```

The first result is a function. Functions cannot be list elements. The diagnostic
is `E_VALUE` at the `map` call. The second callback does not run. Earlier versions
could report its division by zero before they checked the first result.

`sort_by` checks each key before it calls the callback for the next item. All
keys must be numbers, or all must be strings. Integers and floating-point numbers
can share a sort. Booleans are not numbers. Keys with equal values keep their
input order.

Retained sort keys have a separate value budget. Their combined list
representation must fit 20,000 nodes, 32 levels of nesting, and 1 MiB of UTF-8
text. This bounds temporary key storage even when the final sorted list is small.
The key function still runs once per item in input order, until an error occurs.

`zip`, `enumerate`, `record_keys`, `record_values`, `record_entries`, and
`record_merge` also check growing results before they retain each piece. In a
record merge, only the final value of a replaced field counts. Key order stays
the same: existing left-hand keys keep their positions, and new right-hand keys
follow them. These functions do not change their inputs.

Each copied JSON node consumes an execution step in these builders. This matches
the collection builders introduced in 0.5 and 0.6. Nested copies can now reach
the step limit sooner. The API's step count is work accounting, not a stable
performance measure. Programs that depend on an exact previous step count need
to be checked again.

An error discards all values, notes, and proposals from the preview. Callback
errors keep their original source location and call trace. A call trace lists
the functions through which the error passed.

## Parser diagnostics

- An unclosed delimiter points to its opening character. The message names the
  closing character to add.
- A mismatched closing delimiter points to the closing character. The message
  names the expected character and the opening character's line and column.
- An unmatched closing delimiter still points to that character.
- An assignment without a statement keyword gives `let`, `var`, and `set`
  examples.
- Unexpected indentation gives `E_INDENT` and explains that a block needs `:`.
- An `otherwise` without a matching `when` gives a specific explanation.
- The general statement hint includes the current statement keywords.

The same locations apply to imported source files. Comments, quoted delimiter
characters, multiline expressions, and Windows line endings keep their meaning.

## API execution limits

The Python `run` and `test` APIs require `max_steps` to be an integer from 1 to
1,000,000. The default stays 100,000. Booleans, floating-point numbers, strings,
null, and values outside that range return a structured `E_INPUT` diagnostic.
There is no automatic conversion. The check also applies to empty programs and
test listing. The direct runtime constructor enforces the same rule.

This prevents a nonfinite floating-point value from disabling the execution
limit. It also prevents an invalid Python argument from causing a host exception
instead of a language diagnostic. Exhausting a valid limit still gives `E_LIMIT`.

## Test report limits

A test report must fit 1 MiB when encoded as compact JSON with ASCII escapes.
The count includes each test case and the top-level copy of its diagnostics.
It also includes source lines and call trace lines after they are resolved.
Unicode characters count by their JSON escape bytes, not their visible length.
The public API checks the complete final result as well.

The test runner checks each completed case before it adds that case to the
report. If the case would exceed the budget, the runner stops. It replaces that
case with a short failed case named `Test output limit`. This case contains
`E_TEST_LIMIT`. Earlier retained cases stay in order. Later tests do not run.
The result has `ok: false` and `stopped_early: true`. The diagnostic uses the
logical source name `<test output>` because it describes a report limit.

The returned `total`, `passed`, and `failed` counts describe the retained report,
including the failed limit case. They do not claim that all selected tests ran.
The step count includes the work spent on the rejected case. A work limit also
sets `stopped_early: true`, with its existing `E_LIMIT` diagnostic.

Test listing applies the same output limit without executing test bodies. A
bundled project shares one report budget across its entry program, imported
tests, and separate test files. It does not receive a new report budget for each
file. Use a test name filter to run a smaller group, or shorten failure messages.

## Compatibility and checks

The accepted syntax is unchanged. Normal collection results keep their values and
order. These observable changes need attention:

1. A collection error can stop evaluation before a later callback error.
2. Sort keys that exceed the aggregate budget now fail with `E_VALUE`.
3. Copied collection nodes consume steps. Some large programs can reach
   `E_LIMIT` earlier.
4. An unexpected indentation error now uses `E_INDENT`. Some diagnostic text and
   source positions changed.
5. Invalid or excessive `max_steps` arguments now fail with `E_INPUT`. The maximum
   of 1,000,000 matches the existing interactive session limit.
6. Large test reports now fail explicitly with `E_TEST_LIMIT`. Test results add
   `stopped_early` to show when a result or execution limit stopped the suite.

`tests/test_runtime_stability_v08.py` covers callback order, exact node boundaries,
UTF-8 text limits, nesting, input preservation, rollback, module call traces,
delimiter locations, and valid syntax nearby. The full language test suite also
checks the existing examples and language behavior.

`tests/test_test_limits_v08.py` covers large failure reports, resolved imported
source, Unicode expansion, duplicated diagnostics, test listing, and the final
JSON size check. Small failure reports retain their source and trace details.
