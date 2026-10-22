# ZenSigil 0.8 verification

Checked on 22 October 2026. This is an experimental release. The checks below
establish specific behavior. They do not establish general production readiness.
The [stability plan](stability.md) gives the conditions for beta and 1.0.

## Scope

The [45-item work plan](next-v08.md) covers reliability, portable tests, editor
support, public copy, and release checks. It does not add 45 syntax features.
The [language-needs audit](adoption-audit-v08.md) keeps working, partial, missing,
and unnecessary capabilities separate.

## Audit 1: expected behavior

The complete interpreter suite passed 451 tests on Python 3.9.6 and Python
3.12.14 on macOS.
The browser suite passed 74 tests. The editor client suite passed 15 tests.
The browser build completed and refreshed the packaged files.

The exact README program returned `[10.8, 27.0, 54.0]`. Its declared test passed.
Generated checks exercised 2,000 malformed sources through two public APIs
(4,000 checks) and compared 4,500 collection results with independent expectations.
These are bounded generated checks, not an exhaustive proof.

New regressions cover callback result limits, source locations, rollback, parser
errors, portable test identity, shared budgets, archive paths, manifest contents,
editor references, and process recovery.

## Audit 2: independent review

Each implementation area was reviewed by another agent. The review found and
resolved these defects:

| Finding | Correction and check |
|---|---|
| A large reference search exceeded the editor timeout | Removed unnecessary completion-scope work. The same measured case changed from 8.115 seconds to 0.108 seconds. A structural regression protects the algorithm. This is not a general speed claim. |
| Display labels could appear as name references | Excluded rule/test labels from lexical references. Symbols remain available. |
| Entry source imported by a test could run twice | Added explicit entry identity and checked consistent source maps. Distinct files with identical text remain distinct. |
| Diagnostics could point at the wrong portable source | Preserved source identity through test results and call traces. |
| Many long failures produced a 6.47 MB test result | Added a shared 1 MiB compact JSON result budget. The original bundle case now stops at 1,035,170 bytes with `E_TEST_LIMIT` and `stopped_early`. |
| Fixture checks could confuse booleans with numbers | Added type-aware JSON comparison. `true` cannot satisfy an expected `1`. |
| Release archives accepted unsafe drive paths, case aliases, or links | Added path, file-kind, and file/directory collision checks. Valid packages still pass. |

## Audit 3: installed package and user task

The final wheel was installed into an isolated Python 3.12 environment. The
installed-package check and fresh adoption check passed. These checks use isolated
Python so the checkout cannot satisfy imports by accident. They cover examples,
invalid input, modules, tests, reports, the local HTTP service, and editor protocol.
A packed project was tested after its original source folder was moved. Unpack
restored a runnable project with its inputs, contracts, and tests.

This pass found stale browser assets in the first wheel. That wheel was rejected.
The build directory was preserved outside the project, and the wheel was rebuilt.
The release verifier now compares the wheel package inventory and bytes with the
source ZIP. An added regression rejects the original stale wheel.

In the actual browser, a separate failing test identified its file and line.
The source jump selected the correct line. Repair, save, draft recovery, export,
import, and rerun passed. A second case verified that an imported entry test runs
once. Editing that entry kept its module copy consistent. Both tests passed.
The tested application logged no browser warnings or errors. The revised static
project page loaded correctly. The old local page port was no longer running;
that page check used a separate local server.

## Editor host evidence

The real VS Code 1.141.0 standalone Extension Development Host passed 10 checks
against the installed final wheel. These include references and restart, plus
completion, hover, definitions, symbols, formatting, warning/error severity, and
repair. Protocol and mocked-client tests are separate from this real-host check.
The separate workspace host remains unverified. The isolated test instance was
running, but the available native control could not reach its trust prompt.
Workspace trust was not disabled. Do not infer a workspace-host pass from the
standalone result.

## Release checks and public evidence

The release requires a source ZIP, 14 portable examples, a Python wheel, a VSIX,
and a checksum manifest. Strict verification checks every listed byte, required
inventory, archive paths, and expected example results. It also runs with Python
optimization enabled. The source archive is reproducible from unchanged files.

Public source, CI, tag, and download results must be checked after publication.
See the [0.8 release page](https://github.com/zenoutlabs/zensigil/releases/tag/v0.8.0)
for the final public verification record. This source document does not claim
that a future CI run has passed.

## Limits that remain

There is no outside-user trial result. There is no stable compatibility promise,
PyPI package, Marketplace release, complete static type checker, native compiler,
or language package registry. The interpreter is not a security boundary for
untrusted tenants. Reference searches cover open programs and explicit imports.
Tests check expected cases; they cannot prove the absence of defects.

The proposed $100 feedback trial has not started. No payment or reward offer was
sent. Publishing this release is suitable for focused feedback, with the
experimental label retained.
