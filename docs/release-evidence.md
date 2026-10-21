# ZenSigil 0.3 release evidence

The 50-step plan produced a local experimental release candidate. All planned
implementation, documentation, verification and packaging outcomes are complete.
This is not a claim of a public launch, outside-user validation or a security audit.

## Automated checks

| Check | Observed result |
|---|---|
| Full Python suite, macOS / Python 3.9.6 | 117 test methods passed |
| Full Python suite, macOS / Python 3.12.14 | The same 117 test methods passed |
| Node 22.23.1 tests | 35 tests passed |
| Production playground build | Vite build succeeded; packaged examples synchronized |
| Example expectations | All 14 examples checked; the intentional error discards all output |
| Portable compatibility | 14 shared fixtures exercised by Python and JavaScript |
| Malformed source | 1,000 seeded programs returned bounded structured results |
| Independent contract probes | 1,500 malformed mappings through check/run; generic action and HTTP edge cases |
| Source packaging | Two archives from identical source matched byte hashes; ZIP contents and portable examples checked |
| Clean wheel install | Installed into an isolated Python 3.12 environment with no dependencies or network access |
| Installed smoke test | Doctor, 14 bundled examples, scaffold/pack/run roundtrip and HTTP resources passed |
| Browser-exported file in CLI | Reading-list export ran with its input and proposal contracts and matched the browser result |

CI is configured for Python 3.9 and 3.12 on Linux, macOS and Windows. Those hosted
jobs have **not** run from this workspace; the local evidence above is macOS only.

## Browser verification

The updated application was inspected at desktop (1440×1000) and mobile (390×844)
viewports. The mobile page had no horizontal document overflow; the source editor
has its own intentional horizontal scrolling. Browser console checks found no
warnings or errors during the tested flows.

Verified interactively:

- The earlier 0.2 draft and named library entry opened in 0.3.
- Choosing another program with unsaved changes offered Save / Discard / Cancel.
- Check succeeded without running or enabling Download preview.
- Ctrl/Cmd+Enter ran a preview; Ctrl/Cmd+S saved the program.
- An empty proposal contract rejected the emitted action and removed all output.
- The output-error jump focused and selected the actual source instruction.
- Proposal origin, ID and full JSON were available for inspection.
- Both source and portable downloads produced files; the portable file ran in CLI.
- Delete opened an explicit confirmation; Cancel retained the saved program.
  Actual removal and storage-failure behavior are covered by Node tests.
- Saving in a second tab refreshed the first tab's library without replacing its editor.
- The static introduction rendered at desktop and mobile sizes; its local links
  were checked against the delivered documentation.

Timeout cancellation, stale-request handling and draft/codec boundaries are covered
by Node tests. The browser timeout aborts its request; it does not stop Python work
already running. Browser storage remains local and has ordinary localStorage
concurrency limits; it is not a synchronized account service.

## Independent review and repairs

1. Case-insensitive filenames could bypass CLI input protection: on macOS,
   `run program.zs --output PROGRAM.ZS --force` could replace the source. File-identity
   checks now include case aliases and hard links. The original reproduction now
   returns E_OUTPUT and leaves the source unchanged.
2. Scaffolding looked for the wrong proposal-sidecar filename, silently omitting
   output validation. The filename and regression test were corrected. The installed
   wheel's scaffold carries its proposal contract.
3. Portable release examples initially omitted proposal contracts. The packager now
   includes both contracts for all five exported examples, and release verification
   runs them with validation enabled.
4. Sidecar diagnostics used placeholder line 1 for source jumps. Jump links now
   require an actual source line; real program and proposal errors remain navigable.
5. Large enum contracts were rebuilt for every proposal. Per-run schema validation
   and enum caches reduced the measured 8,500-value enum / 1,000-proposal test from
   9.097 seconds to 0.063 seconds locally. This is one workload, not a general speed claim.
6. Doctor could report healthy resources despite missing JS or a missing catalog
   example. It now checks local script/style references and every catalog source/input pair.

Reviewers were separate AI workers, not outside human users. Real beginner sessions
with Nikko, Tyler or independent developers remain to be conducted.

## Delivered and pending

Delivered: source ZIP, installable wheel, five portable examples, SHA-256 manifest,
local playground, static introduction, beginner materials and publication copy.
The manifest verifies the seven release files (ZIP, wheel and five examples); the
preview screenshot is separate. The source ZIP is reproducible with identical bytes
and compression implementation; the wheel is not claimed reproducible across builds.

Pending: choosing the public repository/hosting destination, publishing, observing
actual remote CI, registry name/ownership checks, and gathering outside feedback.
No public repository, package-registry release, social post or website deployment
was created by this milestone. The language remains experimental and preview-only.
