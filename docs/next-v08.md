# ZenSigil 0.8 work plan

This milestone prepares ZenSigil for outside developers. It keeps the language
small and tests the guarantees that users already depend on. It does not declare
1.0, start a paid trial, or add external action execution.

Baseline: public 0.7.0, main commit `14ffa4198a5c2a1d5bc27ecc4be97fb93a4968c2`.
The initial checkout was clean. The 0.7 evidence remains in its release documents.

The 45 steps below include implementation, documentation, and verification.
They are work items, not 45 new language features. A result is complete only after
its stated check passes. The final evidence document records failures and limits.

| # | Work item | Completion check |
|---|---|---|
| 1 | Check public and local source state | Record baseline commit and clean state |
| 2 | Audit the next stability gaps | Trace concrete failures to their implementation |
| 3 | Replace the long repository introduction | One example, one setup route, useful links |
| 4 | Write a natural release note | Describe user-visible changes without inflated claims |
| 5 | Define stable-release gates | Separate real language status from stability evidence |
| 6 | Check collection callback results early | Reject unsupported values before accumulation |
| 7 | Bound accumulated collection results | Large callback results fail with a language error |
| 8 | Preserve callback error locations | Errors identify the relevant source and call |
| 9 | Check preview rollback after callback failure | No partial values, notes, or proposals escape |
| 10 | Improve mismatched bracket errors | Error identifies the incorrect closing bracket |
| 11 | Improve unfinished bracket errors | Error identifies the opening location |
| 12 | Improve invalid-statement errors | Diagnostic gives a useful correction |
| 13 | Preserve valid language behavior | Existing conformance and example results still pass |
| 14 | Carry separate test sources in portable files | Pack retains project tests and raw text |
| 15 | Carry modules used only by tests | Tests run after the source folder is moved |
| 16 | Run tests from portable files | Test filtering and result counts remain correct |
| 17 | Export test reports from portable files | JUnit records correct cases and failures |
| 18 | Restore runnable projects on unpack | Manifest restores inputs, contracts, and tests |
| 19 | Reject ambiguous portable paths | Case and file/directory collisions fail clearly |
| 20 | Protect input files during export | Output cannot replace project sources or defaults |
| 21 | Preserve portable tests in the browser | Import, save, recovery, and export retain tests |
| 22 | Explain the browser test boundary | UI states which test sources it runs |
| 23 | Keep Python and browser format rules aligned | Shared valid and invalid fixtures agree |
| 24 | Add editor Find References | References respect bindings and source identity |
| 25 | Update editor workspace folders | Folder changes take effect without reload |
| 26 | Refresh editor results after disk changes | Watched imports invalidate affected diagnostics |
| 27 | Add an editor restart command | User can restart a failed server |
| 28 | Restart after interpreter setting changes | New process uses the new interpreter path |
| 29 | Clean up failed editor processes | Pending requests end and resources close |
| 30 | Reject invalid editor cursor positions | Invalid offsets do not select another symbol |
| 31 | Check release manifests strictly | Empty, duplicate, unsafe, or invalid entries fail |
| 32 | Check the required release inventory | Missing source, examples, or requested packages fail |
| 33 | Check portable release outputs fully | Values, proposals, notes, and deduplication match fixtures |
| 34 | Keep release verification active under Python optimization | Checks do not depend on assert statements |
| 35 | Add portable compatibility fixtures | Old files migrate; new test maps survive round trips |
| 36 | Record repeatable performance measurements | Expected results and work counts pass before timing |
| 37 | Extend the installed first-task check | Share, test, unpack, and rerun without checkout imports |
| 38 | Update version and migration instructions | 0.8 accepts supported older program and project versions |
| 39 | Run audit 1: behavior and specification | Focused regressions plus complete local suites |
| 40 | Run audit 2: independent defect review | Other reviewers inspect changes and resolve findings |
| 41 | Run audit 3: fresh release and user journey | Isolated wheel, browser, packages, and public checks |
| 42 | Publish the tested source and release | Public commit, CI, and downloaded bytes verified |
| 43 | Update the language-needs audit | Working, partial, missing, and unnecessary stay distinct |
| 44 | Save the full report in Obsidian | Linked project note, evidence, decisions, and open work |
| 45 | Save a completion record for continuation | Self-contained report and exact remaining gates |

## Review method

Audit 1 checks behavior against explicit expected results. Audit 2 uses a different
reviewer for each implementation area. Audit 3 installs the built package and
repeats the first useful task. Repeating the same test three times is not three
independent reviews.

## Stable release decision

The next label after experimental should be a beta with a stated compatibility
policy. A stable 1.0 requires outside-user results, an agreed public surface,
recorded release-candidate use, and no unresolved defects that block supported
tasks. A feature count or passing test count cannot replace those results.

## Remaining work

Implementation is complete. Local verification and the three review methods are
recorded in [release evidence](release-evidence-v08.md). Public publication and its
checks are recorded on the release page after they finish. The Obsidian report
and local completion record preserve the full evidence and remaining stability
gates. Do not treat this plan alone as proof that a check passed.
