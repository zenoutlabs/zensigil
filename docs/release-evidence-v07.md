# ZenSigil 0.7 release evidence

This record covers the 0.7 implementation and its local release checks. It does not
claim that an independent developer trial or production deployment is complete.
The public release is at [v0.7.0](https://github.com/zenoutlabs/zensigil/releases/tag/v0.7.0).
Its attached files and the repository commit must match the tested local files.
The completion report records that final publication check separately.

## Checks performed

| Check | Observed result | Scope |
|---|---|---|
| Full Python regression suite | 362 tests passed on Python 3.9 and 3.12 | Local macOS run on the integrated source |
| Playground tests | 49 tests passed | Request, state, module, and portable-file behavior |
| Editor client tests | 6 tests passed | Protocol framing and provider behavior |
| Playground production build | Passed | Bundled offline assets synchronized |
| Installed wheel checks | Passed with isolated Python 3.12 | 23 examples, projects, contracts, modules, closures, collections, REPL, JUnit, editor protocol, HTTP resources |
| Fresh first-task check | Passed with source imports excluded | Console entry point, new project, six quickstart files, expected results, tests, format, lint, invalid input, portable export |
| Actual browser use | Passed | Type warning, source jump, repair, execution, save, reload |
| Real VS Code standalone host | 8 of 8 checks passed on VS Code 1.141.0 | Completion, hover, definition, symbols, formatting, warning/error severity, unsaved repair |
| Editor package build | Passed | Local 0.7 VSIX with project publisher metadata |
| Independent type-advice probes | 38 passed | Known typed values through functions, aliases and lambdas; module identity; UTF-16 location |

The real editor run used the final 0.7 wheel. All 25 installed Python source files
matched that wheel. The wheel SHA-256 was
`a148869e08926cf56e9602d88a9d4176e3a7cfa29bd1ecef8410a10f000ecb9c`.

The first task returned count 3, total 300 ms, and average 100 ms. Changed input
returned count 2, total 60 ms, and average 30 ms. Invalid input failed before
execution. The exported program produced the expected result after the original
source folder was moved. Separate project test files are not part of that export.

## Defect evidence

Regression tests cover malformed manifest versions, output symlink loops, blank
input overrides, module-root symlink loops, and oversized editor diagnostics.
The oversized case used a valid 42,324-byte program. Its previous warning message
exceeded the client's 1 MiB limit. Count and byte limits now preserve errors and
state when some diagnostics are omitted.

The first remote Windows run found a fixture problem. Default text writes changed
LF line endings to CRLF. The formatter correctly reported a change. The test and
installed-package verifier now write LF explicitly. A regression checks that
`fmt --write` converts CRLF to LF without changing the program result.

## Release checks

Use `tools/package_release.py` to create the source ZIP, fourteen portable examples,
and checksums. Use `tools/verify_release.py` to check archive contents, example
outputs, version metadata, and hashes. A local VSIX and wheel are included in the
checksum manifest when present. Build the source ZIP twice and compare bytes.

The public workflow runs six Python jobs across Linux, macOS, and Windows, plus
one playground/package job. Inspect the actual 0.7 run before claiming those jobs
passed. The preceding 0.6 tag run 39652018874 finished with all seven jobs successful.

## Limits that remain

- The real editor workspace-import test did not complete. Workspace trust stopped that automated run. Trust settings were not changed.
- Type warnings use known facts. They do not prove a program correct or infer every type.
- No outside developer has completed the proposed trial yet.
- The package is not published to PyPI or the VS Code Marketplace. Use the release files.
- No performance comparison or production security claim is established.
- Public website and social copy is prepared. It is not posted to a separate website or social account.

See the [45-need audit](adoption-audit-v07.md), [24-outcome plan](next-v07.md),
[reality check](reality-check-v07.md), and [trial proposal](developer-trial.md).
