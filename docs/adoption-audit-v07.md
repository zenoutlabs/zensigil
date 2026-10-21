# ZenSigil: 45 needs for developer adoption

This audit checks ZenSigil as a small programming language for local calculations,
data transforms, and reviewable proposals. It does not assume that every language
needs classes, a virtual machine, or a package registry.

Baseline: public version 0.6.0, commit `e54a614`. The last column records the 0.7 work.
**Working** means that implementation and automated evidence exist. **Partial** means
that a useful part works, but the stated need has a limit. **Missing** means no usable
implementation exists. **Unnecessary** means it is outside this release's purpose.
These labels do not establish production safety or independent developer adoption.

| # | Need | 0.6 status | Evidence or limit | 0.7 action |
|---|---|---|---|---|
| 1 | Clear purpose and audience | Working | README defines local data programs and reviewable output | Clarify public claims |
| 2 | Consistent keyword roles | Working | syntax.py; linguistic-design.md | Preserve vocabulary |
| 3 | Explicit characters and tokens | Working | ASCII identifiers, JSON strings, indentation in syntax.py | Preserve lexical rules |
| 4 | Documented grammar | Working | grammar.ebnf; parser regressions | No new grammar in this release |
| 5 | Defined operator precedence | Working | PRECEDENCE; conformance/language.zs | Preserve behavior |
| 6 | Predictable evaluation order | Working | runtime.py; language/core tests | Preserve behavior |
| 7 | Lexical name scope | Working | checker.py; module and closure tests | Check lint scope too |
| 8 | Immutable values and explicit local state | Working | let/var/set; core tests | Avoid type guesses for mutable values |
| 9 | Strict type distinctions | Working | typesys.py; true differs from 1 | Check known type errors before execution |
| 10 | Nested runtime annotations | Working | list/record/union annotations; core_v05 tests | Add advisory checks for known values |
| 11 | Useful checks before execution | Partial | check finds syntax/name/arity errors; types are checked at runtime | Add conservative type warnings |
| 12 | Pure reusable functions | Working | named functions and calls; core tests | Check known argument/return types |
| 13 | Closures and higher-order functions | Working | immutable captures; map/filter/fold | Keep unknown callback results unknown |
| 14 | Conditions and loops | Working | when/for/while/break/continue | Warn for known non-boolean conditions |
| 15 | Explicit missing and null behavior | Working | has/get/??; type and runtime tests | Keep runtime checks authoritative |
| 16 | Useful collection operations | Working | 69 built-ins; stdlib tests | Validate through existing examples |
| 17 | Deliberate numeric behavior | Working | finite floats, integer bounds, exact decimal-text helpers | Correct stale reference wording |
| 18 | Modules with private implementation | Working | named imports/export fn; modules_v06 tests | Preserve module identities in warnings |
| 19 | Portable source and data | Working | versioned .sigil.json; Python/JS fixtures | Support 0.7 migration |
| 20 | A runnable project definition | Partial | manifest selects source/tests, but not inputs/contracts | Add bounded manifest input paths |
| 21 | Short project commands | Partial | repeated data/contract flags required | Use defaults; retain explicit overrides |
| 22 | Runnable project export | Missing | pack rejects project directories | Export entry, modules, inputs, and contracts |
| 23 | New-project starter | Partial | init works; no local instructions or input example | Add a useful project and local guide |
| 24 | Fresh installation proof | Working | isolated wheel verification | Add a repeatable first-task journey |
| 25 | Windows, macOS, Linux support | Working | all seven v0.6 tag CI jobs passed | Keep the platform matrix |
| 26 | Error locations and call traces | Working | SigilError; runtime/interface tests | Preserve module source locations |
| 27 | Helpful failure boundaries | Partial | output symlink loop and invalid manifest version can leak tracebacks | Reproduce and fix both |
| 28 | Several parser errors in one pass | Missing | parser stops at the first syntax error | Defer; needs a recovery design |
| 29 | Formatting that preserves meaning | Working | formatter.py; project formatting tests | Verify the new starter is formatted |
| 30 | Lint with a strict CI mode | Partial | unused/shadow/unreachable checks; no type warnings | Add type advisories; preserve --strict |
| 31 | Editor completion and navigation | Working | protocol/provider tests; namespace fixtures | Test changes against real provider calls |
| 32 | Correct editor warning severity | Missing | LSP calls check only; no advisory path | Display warnings separately from errors |
| 33 | Real editor application proof | Partial | v0.6 provider tests passed; host stopped at trust | Record exact new host result and limit |
| 34 | Browser access to advisory checks | Missing | browser offers check/run/test, not lint | Add Find warnings and source navigation |
| 35 | Interactive experiments | Working | bounded REPL with undo/reset/save | Keep regression coverage |
| 36 | Executable tests and CI reports | Working | isolated test blocks; JUnit reports | Use them in the adoption example |
| 37 | Resource and data limits | Partial | source/work/depth/output bounds; not a tenant security boundary | Keep bounds; test warning-pass behavior |
| 38 | Safe output-file handling | Partial | most inputs protected; one symlink-loop failure | Protect project defaults and recover cleanly |
| 39 | Conformance and regression evidence | Working | language corpus; Python/JS checks | Add tests for found failures |
| 40 | Release integrity and recovery | Working | verified public hashes; Git backup | Build and verify the new artifacts |
| 41 | Version and migration policy | Partial | pre-1.0 changes documented; no stable 1.0 guarantee | Document additive project keys and warning limits |
| 42 | License and contribution route | Working | MIT; public repo; CONTRIBUTING | Add focused setup and syntax report forms |
| 43 | Independent developer trials | Missing | automated checks are not outside-user evidence | Prepare a five-person trial brief |
| 44 | Measured speed and a performance target | Partial | local benchmark exists; no external comparison or target | Make no speed claim; defer optimization |
| 45 | Broad ecosystem features now | Unnecessary | registry, async effects, native compiler, classes, macros, debugger | Choose each from real use; do not add for count |

## Work selected

The release focuses on first use, source checks, editor feedback, and runnable project
sharing. It does not attempt the missing parser recovery or a full static type system.
Those changes need a separate design and failure model. See [the release plan](next-v07.md)
and [the current claim check](reality-check-v07.md).
