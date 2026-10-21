# JUnit test reports

`zensigil.reports.junit_xml(result, suite_name="ZenSigil")` turns a completed
ZenSigil test result into JUnit-style XML text. It performs no file or network
operations and does not execute source. The interpreter remains standard-library
only; XML serialization uses Python's `xml.etree.ElementTree`.

```python
from pathlib import Path
from zensigil import test
from zensigil.reports import junit_xml

result = test('test "Arithmetic":\n    require 2 + 2 == 4, "Expected four."\n')
xml = junit_xml(result, suite_name="Example project")
Path("test-results.xml").write_text(xml, encoding="utf-8")
```

The explicit file write above belongs to the host program. Choose a separate
report destination; the serializer does not inspect or protect filesystem paths.
The CLI's report integration provides its own source/output protection.

## Command line

```sh
zensigil test my-project --junit results.xml
zensigil test tests.zs --filter Arithmetic --junit arithmetic.xml --json
```

The report path must be a new file and separate from inputs, source, contracts,
modules and the project manifest. There is no overwrite option. The exit status
still reflects test success; a report write failure produces `E_OUTPUT` and exits
with status 1. `--list` with `--junit` is rejected before execution. An empty test
selection reports zero cases; use `--fail-if-empty` to make that a failure.

## Outcome mapping

The document has one `testsuites` root and one named `testsuite`. Each executed
case becomes a `testcase` in result order, preserving its name. Its `file`
attribute uses the module's logical `source_name`, or the host's `source_file`
for a root program. The `classname` includes that source identity, plus the
entry source when a project aggregate supplies one, so equal test labels in
different modules or entry programs remain distinct to report consumers.
Cases without source metadata use the suite name as their class. Counters are
computed from emitted cases rather than trusting the supplied summary totals.

| Test result | XML outcome |
| --- | --- |
| Successful case with no diagnostics | Case without failure/error children |
| Failed case containing only `E_REQUIRE` diagnostics | One `failure` child |
| Runtime/type/import/limit failure in a case | One `error` child |
| Failed case without a diagnostic | One synthetic `E_TEST` error |
| Diagnostic before tests can be discovered | A synthetic `Program check` case with an error |
| Failed overall result with no failing case or diagnostic | A synthetic `Test run` case with an `E_TEST_RUN` error |
| Empty successful execution | A suite with zero tests, failures and errors |

When aggregated CLI diagnostics repeat a case's diagnostics, the serializer
matches those occurrences and avoids counting them twice. Additional global
diagnostics each receive an error case, including errors in a separate source
that could not be checked. A failed overall command can therefore never become
an all-passing report merely because it discovered zero tests.

Diagnostic text includes the code, message, source location, source excerpt,
input/output validation paths and available call frames. All diagnostics for one
case are joined into its single failure/error element. At most 64 frames per
diagnostic are included. Report consumers can differ in how they display these
optional details; no particular CI product's rendering is implied.

## Listing, timing and limits

The helper raises `ValueError` for a result with `listed: true`, or any case whose
`ok` is `None`, so enumerating tests cannot manufacture passing cases. An unmarked
empty list-only API result is indistinguishable from an executed empty suite;
both produce zero cases and zero passes. Callers should prevent list/report
combinations or supply the `listed` marker explicitly.

Reports contain no invented duration, timestamp, hostname or test assertion
count. Execution-step counts are not elapsed time. A run that stops on its work
budget reports its executed cases and the observed limit error; the serializer
does not invent outcomes for undiscovered or unexecuted tests. `skipped` is zero
because this runtime does not supply an explicit skipped-case result.

Names, paths and diagnostic text are escaped as XML. Characters disallowed by
XML 1.0, including NUL, other forbidden control characters and lone surrogate
code points, become the replacement character `U+FFFD`. Ordinary Unicode,
newlines and tabs remain readable. The function does not mutate the input result.

A report is bounded to 10,000 emitted cases and 8 MiB of escaped UTF-8 XML, with
conservative text accounting during construction. Oversized reports and invalid
result shapes raise `ValueError`; callers should finish serialization successfully
before writing a destination. Synthetic error cases count toward the same bounds.
