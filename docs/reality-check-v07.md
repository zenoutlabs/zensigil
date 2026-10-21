# What ZenSigil actually does

This check started from public version 0.6.0 (`e54a614`) and inspected the 0.7 changes.
It checks source, regression tests, an installed package, the browser, and editor providers.
The [release evidence](release-evidence-v07.md) records exact final counts and publication state.

## Demonstrated results

| Claim | Evidence | What that evidence establishes |
|---|---|---|
| ZenSigil is its own programming language | syntax.py, checker.py, runtime.py; conformance tests | Source has its own tokens, grammar, rules, and evaluation |
| It runs without an AI service | Standard-library Python runtime; isolated installed checks | Execution does not call a model or need an API key |
| It has a domain-neutral core | Core constructs; 23 examples across several tasks | Stock review is an example, not part of the grammar |
| Functions and modules work | Core/module tests; independent module probes | Pure functions, closures, exports, private helpers, and source scopes |
| Data checks and preview rollback work | Contract and runtime tests; invalid quickstart input | Invalid data or runtime failure returns no accumulated output |
| Portable files run outside their source folder | Installed adoption test moves the source folder | Entry source, imports, input, and contracts are carried in the file |
| Project input settings work | adoption_v07 tests; exact quickstart journey | Defaults work; explicit overrides are checked; output cannot replace inputs |
| Type advice works for known facts | type_lint_v07 tests; independent operand probes | Known incompatibilities produce warnings without source execution |
| Browser warnings work | HTTP regression tests and actual browser use | Warnings show source locations; a repair clears the warning |
| Editor protocol and providers work | Python/Node tests; eight real standalone VS Code assertions | Completion, hover, definitions, symbols, formatting, severity, and unsaved repair |
| Public 0.6 delivery works | Public source and downloaded hash comparison; final tag CI | The 0.6 files are public and all seven tag jobs passed |

## Partial work

- Type advice uses known literals and explicit annotations. It does not infer all types or prove correctness.
- The parser reports its first syntax failure. It does not recover and report several parser errors.
- Resource limits bound local work. They are not proof of a safe public multi-tenant service.
- The VS Code standalone host passed. The workspace-import host remains unverified because workspace trust stopped the automated run.
- Runtime decimal numbers are floating point. Exact decimal-text helpers are available and return strings.
- Portable project export includes the runnable entry and its imports. It does not include separate project test files.
- Version migration works for supported envelopes. A stable 1.0 language guarantee does not exist.

## Untested assumptions

No independent developer trial is complete. We do not yet know how often a new user
can finish setup without help. Automated first-use checks cannot answer that question.
The language's usefulness for a larger real application is also unmeasured.
There is no evidence of wide adoption, performance superiority, or an established ecosystem.

## Defects reproduced and fixed

| Failure | Root cause | Fix and nearby checks |
|---|---|---|
| Invalid manifest version printed a traceback | A list reached a set-membership operation | Check the field type first; test malformed versions and older supported versions |
| Output symlink loop printed a traceback | Path resolution raised RuntimeError outside the output boundary | Convert path errors to a diagnostic; preserve source and output files |
| Empty override disabled a project contract | Empty text was treated as an absent flag | Reject blank paths; test each override and invalid file contents |
| Module-root symlink loop printed a traceback | Root resolution occurred before the guarded module loader | Use checked root resolution; test run and pack |
| Large warning publication disconnected the editor | Diagnostic JSON could exceed the client's frame limit | Bound count and bytes; include an explicit incomplete-results notice |

`pack PROJECT` was an unsupported operation in 0.6. It is a new capability, not a
regression fix. Known type warnings are also new advice. `check` never claimed full
static type checking. The code and documentation preserve that distinction.

## Blockers and next decisions

No blocker remains for a small local developer trial with the tested release.
The proposed $100 trial still needs the owner's approval of its terms and payment route.
No money is committed by the brief. No website or social account has been selected
for automatic posting. Ready-to-use text is in [launch copy](launch-copy.md).

Package-index and editor-marketplace publication remain separate tasks. Do not use
an unverified package name as an installation instruction. Use the release wheel or source.
A full compiler, debugger, registry, async runtime, and network capability model remain future designs.
