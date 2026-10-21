# ZenSigil 0.5.0 release evidence

Recorded 2026-10-20 on macOS. This is an experimental local release candidate.
Public GitHub publication and remote CI success are not claimed.

## Delivered scope

The [45-step ledger](next-45-v05.md) records 42 local implementation and verification
outcomes, with three external-publication outcomes pending account access. The
[original 45 capabilities](language-capabilities.md) remain a verified baseline,
with limitations stated. The [30 additional needs](additional-capabilities.md)
bring the assessment to 75; some are deliberate future designs, not completed features.
These lists overlap and must not be added together as independent feature counts.

0.5 adds expression lambdas, immutable lexical captures, function factories,
nested list/record annotations and unions; 12 pure standard functions (61 total);
a stdio language server and VS Code client; lint, explicit project formatting,
stdin source, and test filtering/discovery. There are 21 catalog examples.
The grammar and linguistic rationale document consistent vocabulary, composition,
precedence, scope, capture timing, and explicit runtime semantics.

## Observed checks

| Check | Observed result |
|---|---|
| Python suite, system Python 3.9.6 | 227 methods passed |
| Python suite, bundled Python 3.12 | 227 methods passed |
| Playground, Node 22 | 45 tests passed; production build passed |
| Editor client, Node 22 | 6 tests passed: transport plus simulated host providers and trust gate |
| Language-server protocol/service | 16 Python methods included in the 227; real stdio process traffic included |
| Example conformance | All 21 examples match explicit expected outputs; executable corpus retained |
| Fresh installed wheel | Isolated Python 3.12 environment; no checkout imports; developer tools, HTTP resources, examples, closures, annotations, collections and LSP stdio passed |
| Browser-exported closure program | Installed CLI returned values [[21, 30]] |
| VSIX | Official packager passed; publisher ZenOutMan, version 0.5.0, extension.js and client.js verified |
| Portable releases | Twelve programs executed successfully; values checked against golden fixtures |
| Release manifest | 15 SHA-256 checksums verified: source ZIP, wheel, VSIX and twelve portable programs |
| Source ZIP repeatability | Two builds from identical source bytes have equal SHA-256 hashes |
| Source hygiene | git diff --check passed; dependency/build/cache directories excluded |

The wheel is not claimed byte-reproducible. Checksums detect changes but do not
prove publisher identity. The release scripts are `tools/package_release.py`,
`tools/verify_release.py`, and `tools/verify_install.py`.

## Rendered playground

Verified the built application at http://127.0.0.1:8766/ with version 0.5.0 visible:

- Closure factory output [21, 30], two executable tests passed, saved locally,
  reloaded and reopened, exported to a portable file, and run through the installed CLI.
- Nested types produced {first: 7, empty: null, total: 18}; its test passed.
- Collection analysis produced counts {design: 2, engineering: 1}, ordered names,
  even/odd partitions and flattened skills; its test passed.
- The guide renders the new syntax and all 61 live standard-library entries.
- Inspected mobile guide at 390 × 844 and desktop program at 1440 × 1000;
  no document horizontal overflow. Temporary viewport settings were reset.
- No browser console warnings/errors observed during these checks.

The local desktop screenshot is delivered separately as `zensigil-v0.5-preview.jpg`.
The saved closure program remains open. This was focused QA, not an exhaustive
browser or accessibility certification.

## Actual VS Code host limitation

Two isolated launches reached the test harness in VS Code 1.141.0. Both timed out
at the workspace-trust gate before provider assertions ran. Native UI control
selected a different running VS Code instance; the synthetic host could not be
approved through that surface. No trust setting was disabled. The harness and
reproduction recipe are in `editors/vscode/test/host.js` and `docs/editor-v05.md`.
Actual-host provider compatibility remains unverified despite protocol/client tests.

## Independent review and resource checks

Separate workers reviewed one another's language, library, editor and CLI changes.
Bounded reported probes included 300 closure-capture equivalence cases, 700 nested
annotation cases, 3,000 malformed-source cases, 200 randomized library comparisons,
empty-callback arity cases, annotation/capture budgets and JSON boundaries.

Fixed findings have regression coverage: quoted string tokens accepted as type
names; symlink cycles escaping structured editor errors; completion names leaking
from closed scopes or lambda parameters; error-output paths overwriting a malformed
project manifest; and stdin output protection implicitly reading local modules.
Original reproductions were rerun independently. No remaining actionable finding
was reported in those review scopes. This is not exhaustive proof or human adoption.

`tools/benchmark.py` provides a repeatable verified baseline. On this machine,
25 iterations including parse/check/run had medians of 1.332 ms (100-item closure
map), 1.830 ms (100-item group counts), and 0.484 ms (typed sum). Results depend on
hardware/runtime; there is no claim of superiority or stable performance targets.

## Publication status and remaining designs

The authorized destination is ZenOutMan/zensigil. The authenticated connector
identifies ZenOutMan but has no repository-creation capability. The browser session
available for creation identifies a different account. A ZenOutMan sign-in handoff
is pending. The latest repository metadata request returned 404. Source has not
been uploaded; no public release, registry package or remote CI pass is claimed.

Annotations check executed values, not full static inference. Lambdas have one
expression and immutable snapshots; function values cannot enter JSON containers.
Modules have flat names and explicit supplied source. Host I/O, namespaces, native
value types, a debugger, concurrency, package resolution and 1.0 governance remain
separate designs. The interpreter's budgets are prototype guardrails, not a
multi-tenant security boundary. There has been no independent human adoption study.
