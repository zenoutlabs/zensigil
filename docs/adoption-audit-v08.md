# ZenSigil adoption audit for 0.8

The target user is a developer who wants a small local data program. The target
is not every possible software task. This table checks 45 needs against the
implementation. A working feature can still have documented limits.

**Working** means implementation and checks exist. **Partial** means useful support
exists, with a material gap. **Missing** means the needed evidence or feature is
absent. **Unnecessary** means it is outside the current purpose. The final
[release evidence](release-evidence-v08.md) records which checks passed this release.

| # | Need | State | Evidence or remaining limit |
|---|---|---|---|
| 1 | Clear purpose | Working | README: local data programs and reviewed proposals |
| 2 | Consistent keyword roles | Working | let, var, set, fn, when, propose have distinct roles |
| 3 | Defined tokens and characters | Working | syntax.py and language reference |
| 4 | Written grammar | Working | grammar.ebnf and syntax references |
| 5 | Operator precedence | Working | Parser and conformance examples |
| 6 | Evaluation order | Working | Short-circuit and callback-order regressions |
| 7 | Lexical scope | Working | Binding checker, module and closure tests |
| 8 | Immutable values and explicit state | Working | Immutable let; local var/set; snapshot captures |
| 9 | Strict type distinctions | Working | Boolean/number and structural equality tests |
| 10 | Nested runtime annotations | Working | List, record, and union checks |
| 11 | Checks before execution | Partial | Binding errors and conservative type advice; no full inference |
| 12 | Reusable pure functions | Working | Named functions and recursion with limits |
| 13 | Closures and callbacks | Working | Snapshot captures and bounded collection operations |
| 14 | Conditions and loops | Working | when, for, while, break, continue |
| 15 | Explicit missing/null behavior | Working | has/get/??; missing fields fail |
| 16 | Collection library | Working | 69 functions; growing-result limits now consistent |
| 17 | Numeric rules | Working | Finite bounded numbers; explicit exact decimal-text helpers |
| 18 | Private modules and public exports | Working | Source identity, named imports, export fn |
| 19 | Portable program files | Working | Source, input, contracts, modules, tests, entry identity |
| 20 | Project definition | Working | Manifest selects entry, tests, and input defaults |
| 21 | Short project commands | Working | run/check/lint/test/pack accept a project |
| 22 | Complete project sharing | Working | Test-only imports survive pack and unpack |
| 23 | Useful starter | Working | init provides runnable source, tests, README, ignore rules |
| 24 | Fresh installation | Working | Isolated wheel and first-task verifier |
| 25 | Platform checks | Working | Python 3.9/3.12 CI matrix; check actual release run |
| 26 | Useful diagnostics | Working | Source/call locations and improved delimiter messages |
| 27 | Controlled failures | Partial | Reproduced boundary defects fixed; no proof for all inputs |
| 28 | Multiple parser errors per pass | Missing | Parser still stops at its first syntax error |
| 29 | Meaning-preserving formatter | Working | Canonical source and format/run checks |
| 30 | Advisory and strict lint | Working | Type warnings remain conservative; --strict is opt-in |
| 31 | Editor navigation | Working | Completion, definition, hover, symbols, bounded references |
| 32 | Editor refresh and recovery | Working | File events, folder changes, restart, process cleanup |
| 33 | Real editor host evidence | Partial | See exact host scope in release evidence; simulated tests alone do not count |
| 34 | Browser checks and persistence | Working | Run/check/lint/test; shared tests; save/recover/export/import |
| 35 | Interactive experiments | Working | Transactional replay REPL; bounded source/work |
| 36 | Test execution and reports | Working | Shared module tests once; source identities and JUnit |
| 37 | Resource limits | Partial | Work/value/source limits; not a shared-tenant sandbox |
| 38 | Output-file protection | Working | Paths, source/default protection, extraction rollback tests |
| 39 | Regression and conformance evidence | Working | Explicit outcomes, malformed-source probes, collection oracles |
| 40 | Release integrity | Working | Strict inventory, checksums, example results, optimized-Python checks |
| 41 | Stable compatibility promise | Partial | Migration notes exist; proposed 1.0 surface is not frozen |
| 42 | License and contribution route | Working | MIT, contribution guide, focused issue forms |
| 43 | Independent developer use | Missing | No completed outside trial recorded |
| 44 | Measured performance target | Partial | Local measurements exist; no user-derived target or broad speed claim |
| 45 | Large ecosystem features | Unnecessary | Native compiler, async, registry, classes, macros chosen only from need |

## What changed in this audit

The largest 0.8 additions concern test sharing, source identity, editor recovery,
reference search, and release verification. The core language grammar did not grow.
Independent review found additional failures in reference performance, duplicate
tests, source labels, and result size. Each accepted fix needs a regression check.

The remaining stability work is explicit in [the stability plan](stability.md).
A row marked Working is not a claim of widespread use, production safety, or a
permanent compatibility guarantee.
