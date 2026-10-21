# ZenSigil 0.4.0 local release evidence

Recorded 2026-10-20 on macOS. This is a locally tested experimental release;
public GitHub publication, registry publication and remote CI success are not claimed.

## Scope and language decisions

The [45-capability assessment](language-capabilities.md) and
[45-step implementation ledger](next-45-v04.md) describe one milestone from two
perspectives. Retained capabilities are identified explicitly; this is not 90
independent new features. Beginner-course completion is not a dependency.

The language adds state and loops, shallow runtime annotations, named function
values, lazy choices and null fallback, membership, slices, structured outputs,
isolated executable tests, source-aware traces, pure modules and 37 pure standard
functions (49 total). Tooling adds formatting, AST export, project manifests,
module-aware portable files, playground controls and a local VSIX.
See [syntax](syntax-v04.md), [grammar](grammar.ebnf), [standard library](stdlib.md),
[modules](modules.md), [tooling](tooling.md), and [linguistic rationale](linguistic-design.md).

## Automated checks

| Check | Observed result |
|---|---|
| Python standard-library suite, system Python 3.9.6 | 168 test methods passed |
| Same suite, bundled Python 3.12 | 168 test methods passed |
| Node 22 playground suite | 45 tests passed |
| Production playground build | Passed; built assets and 18 bundled examples synchronized |
| Golden behavior fixtures | All 18 examples matched explicit expected proposals/notes/values |
| Executable conformance corpus | 8 isolated test blocks passed |
| Portable codec fixtures | 20 shared cases; Python and JavaScript readers agree |
| Source archive reproducibility | Two archives from identical source bytes had equal SHA-256 hashes |
| Fresh wheel installation | Passed in a new isolated Python 3.12 environment outside the checkout |
| Installed CLI | doctor, original contracted example pack/run, init, run/test project, fmt --check and ast --json passed |
| Installed modules | Scaffolded module example packed and ran; mean 6, squares [9,36,81]; both tests passed |
| Installed resources | HTTP UI, health, 18 example catalog entries and packaged nested library source passed |
| VSIX | Official packager succeeded; ZIP integrity, publisher ZenOutMan, version 0.4.0 and payload checked |

Packaging scripts verify the final artifact hashes and execute all nine portable
examples. The local SHA256SUMS file covers source ZIP, wheel, VSIX and portable
examples. Hashes detect byte changes; they do not authenticate a publisher.

## Rendered browser QA

Tested the running built application at http://127.0.0.1:8766/ with native browser
controls. The title was ZenSigil — Playground and the rendered version was 0.4.0.

- Loaded Modules & executable tests: one JSON result, mean 6 and squares [9,36,81].
- Ran root and imported test blocks: 2 passed, no main effects; preview download disabled in test mode.
- Deliberate library divide-by-zero: E_ZERO named lib/statistics.zs line 7, showed
  squared/map call frames, returned no outputs, and jumped to the exact expression.
  The module textarea received focus and selected `/ 0`.
- Restored the module; tests passed again. Rejected ../escape.zs visibly at Add module.
- Saved, reloaded and reopened the named module program. Both source files survived.
- Exported modules-executable-tests.sigil.json, ran that browser export through the
  CLI, reimported it in the browser and reran both tests successfully.
- Formatted `emit   1+2` to `emit 1 + 2`. A program without tests explicitly reported
  No tests declared. A deliberate failed test showed its message and source jump.
- Function reference search for dec_ returned the six matching functions.
- At 390 × 844 and 1440 × 1000 viewport overrides, inspected screenshots and observed
  no document overflow. Mobile code scrolls within its editor; controls wrap.
- Browser console warnings/errors: none observed during these checks. Temporary
  viewport override reset; the modular example was restored with successful output.

[Desktop proof](../../zensigil-v0.4-preview.jpg). The local browser tab remains open.
This is focused rendered QA, not a claim of every assistive-technology/browser combination.

## Independent worker review

Separate implementation workers reviewed language semantics and integration.
Reported probes included 3,000 malformed grammar cases, 726 signed-range comparisons,
5,000 seeded malformed run/check/test cases and 22 API/HTTP assertions. No uncaught
exceptions were reported in those probes. These are bounded probes, not exhaustive proof.

Resolved findings included test suites incorrectly requiring unrelated main inputs,
module-path errors losing the importing source location, Unicode line-separator
characters shifting diagnostic excerpts, early HTTP failures missing test-result
fields, and output overwrite protection around failed module discovery. Regression
checks exercise the fixes. Callback arity is checked even for empty collections.

## Explicit limitations

Annotations check executed values; there is no full static inference or generic
collection type system. Named function references do not capture lexical closures.
Functions cannot be stored in JSON collections. Module names are flat and imports
are explicit root-relative paths. Decimal helpers use canonical decimal strings,
not a native decimal value type. Ordinary decimals use floating point.

The VSIX was packaged and inspected but not launched in an actual VS Code host.
Local macOS Python checks are not evidence that the configured Linux/Windows CI
matrix has run. No independent human adoption or usability study was conducted.
The loopback server remains a local development tool, not a multi-tenant sandbox.
There is no network I/O, package registry, async runtime, optimizer or durable
external action executor. These are future language/ecosystem designs.
