# ZenSigil 0.3: the next 50 steps

Goal: make a broadly useful experimental language easy to try, share and review. This release keeps the language core domain-neutral. Public hosting, registry publication and third-party user feedback require external destinations or participants and are not implied by local completion.

All 50 scoped local release steps are complete. Public repository creation, hosted CI runs, website deployment and outside-user feedback remain separate external launch steps. See [release evidence](release-evidence.md) for verification and limits.

| # | Outcome | Acceptance condition | Status |
|---|---|---|---|
| 1 | Portable program specification | One documented envelope shared by CLI and browser. | Complete — [CLI guide](cli.md), shared fixtures and portable/CLI tests |
| 2 | Python portable decoder | Bounded strict JSON decoding preserves source/input/contracts. | Complete — [CLI guide](cli.md), shared fixtures and portable/CLI tests |
| 3 | Run exported programs | run accepts .sigil.json with embedded inputs. | Complete — [CLI guide](cli.md), shared fixtures and portable/CLI tests |
| 4 | Check exported programs | check accepts the same file without evaluating proposals. | Complete — [CLI guide](cli.md), shared fixtures and portable/CLI tests |
| 5 | Explicit input overrides | CLI replacements override the corresponding embedded field only. | Complete — [CLI guide](cli.md), shared fixtures and portable/CLI tests |
| 6 | Pack source files | pack creates a portable file; existing files need --force. | Complete — [CLI guide](cli.md), shared fixtures and portable/CLI tests |
| 7 | Unpack portable files | unpack writes raw program parts to a new directory. | Complete — [CLI guide](cli.md), shared fixtures and portable/CLI tests |
| 8 | Discover examples from CLI | examples lists the included example names. | Complete — [CLI guide](cli.md), shared fixtures and portable/CLI tests |
| 9 | Scaffold an example | example copies a runnable example and its contracts. | Complete — [CLI guide](cli.md), shared fixtures and portable/CLI tests |
| 10 | Diagnose an installation | doctor reports interpreter and bundled resource health. | Complete — [CLI guide](cli.md), shared fixtures and portable/CLI tests |
| 11 | Save command-line results | run --output writes JSON with overwrite protection. | Complete — [CLI guide](cli.md), shared fixtures and portable/CLI tests |
| 12 | Preserve 0.2 programs | Old portable files, saved programs and drafts open in 0.3. | Complete — [CLI guide](cli.md), shared fixtures and portable/CLI tests |
| 13 | Declare proposal contracts | An optional action-to-fields contract map uses the existing generic type rules. | Complete — [proposal contracts](proposal-contracts.md), API/HTTP regression suite |
| 14 | Reject undeclared actions | A supplied proposal contract closes the set of permitted action names. | Complete — [proposal contracts](proposal-contracts.md), API/HTTP regression suite |
| 15 | Validate proposal fields | Missing, wrong-type and out-of-range output fields fail clearly. | Complete — [proposal contracts](proposal-contracts.md), API/HTTP regression suite |
| 16 | Keep previews atomic | A bad proposal discards all proposals and notes in the preview. | Complete — [proposal contracts](proposal-contracts.md), API/HTTP regression suite |
| 17 | Locate proposal failures | Diagnostics identify the output path, action and source location. | Complete — [proposal contracts](proposal-contracts.md), API/HTTP regression suite |
| 18 | Expose output checks in Python | run/check accept optional proposal_contract; check states its limits. | Complete — [proposal contracts](proposal-contracts.md), API/HTTP regression suite |
| 19 | Expose output checks over local HTTP | Strict object/text contract inputs work through the local API. | Complete — [proposal contracts](proposal-contracts.md), API/HTTP regression suite |
| 20 | Add contracts to practical examples | Stock and general examples include reviewable output expectations. | Complete — [proposal contracts](proposal-contracts.md), API/HTTP regression suite |
| 21 | Bound output-contract work | Definition size, nesting and diagnostic counts are capped. | Complete — [proposal contracts](proposal-contracts.md), API/HTTP regression suite |
| 22 | Explain output contracts | A guide explains supported rules and what they do not execute. | Complete — [proposal contracts](proposal-contracts.md), API/HTTP regression suite |
| 23 | Edit output contracts in the playground | Optional proposal contract travels with saves and imports. | Complete — Node tests and browser checks; [evidence](release-evidence.md) |
| 24 | Check without running | A separate check action never enables a preview download. | Complete — Node tests and browser checks; [evidence](release-evidence.md) |
| 25 | Add keyboard commands | Save and run shortcuts work and are discoverable. | Complete — Node tests and browser checks; [evidence](release-evidence.md) |
| 26 | Download source independently | Users can export the current .zs source. | Complete — Node tests and browser checks; [evidence](release-evidence.md) |
| 27 | Manage saved programs | Delete requires an explicit choice and preserves the open draft. | Complete — Node tests and browser checks; [evidence](release-evidence.md) |
| 28 | Refresh across tabs | Library choices refresh when another tab changes browser storage. | Complete — Node tests and browser checks; [evidence](release-evidence.md) |
| 29 | Inspect proposal origins | A result shows its rule, source line, ID and raw JSON. | Complete — Node tests and browser checks; [evidence](release-evidence.md) |
| 30 | Jump to source errors | Source diagnostics focus the relevant editor location. | Complete — Node tests and browser checks; [evidence](release-evidence.md) |
| 31 | Recover from a stalled server | Requests time out with retry guidance and stale results stay discarded. | Complete — Node tests and browser checks; [evidence](release-evidence.md) |
| 32 | Update the in-app guide | Explain generic uses, check vs run, contracts and portable files. | Complete — Node tests and browser checks; [evidence](release-evidence.md) |
| 33 | Add a reading-list program | A personal example prioritizes unread books with exact expected results. | Complete — example fixtures and expected-result tests |
| 34 | Add an event-capacity program | A community example handles full, overbooked and open sessions. | Complete — example fixtures and expected-result tests |
| 35 | Add a project-budget program | An integer-cents example reviews overruns with validated input. | Complete — example fixtures and expected-result tests |
| 36 | Create a beginner learning path | Short exercises include expected outputs and self-check answers. | Complete — [beginner course](learn.md) |
| 37 | Publish an error troubleshooting guide | Common failures have a cause and a concrete correction. | Complete — [error guide](troubleshooting.md) |
| 38 | Show Python embedding | A runnable standard-library example demonstrates the public API. | Complete — [runnable embedding example](../examples/embed.py) |
| 39 | Define compatibility expectations | Document migrations, file versions and experimental status. | Complete — [compatibility policy](compatibility.md) |
| 40 | Write release notes | Explain the 0.3 changes, limitations and upgrade path. | Complete — [changelog](../CHANGELOG.md) |
| 41 | Create a release checklist | Provide exact build, verify, install and publication commands. | Complete — [release checklist](releasing.md) |
| 42 | Prepare a project landing page | A static page explains ZenSigil with working local documentation links. | Complete — [static introduction](index.html), desktop/mobile inspection |
| 43 | Expand CI coverage | Configure Windows/macOS/Linux checks and build/package verification. | Complete — CI configuration; remote runs await publication |
| 44 | Prove a clean installation | Build and run the wheel outside the source checkout. | Complete — isolated installed-wheel verification |
| 45 | Verify all example outcomes | Golden results cover every sample, including the intentional error. | Complete — all 14 examples match declared outcomes |
| 46 | Check cross-interface compatibility | Shared fixtures are accepted/rejected consistently in Python and JavaScript. | Complete — 14 shared Python/JavaScript fixtures |
| 47 | Exercise malformed programs | Deterministic hostile/malformed input probes return bounded diagnostics. | Complete — 1,000 seeded malformed-source probes plus independent review probes |
| 48 | Produce reproducible release files | Stable source ZIP, SHA-256 manifest and portable examples verify successfully. | Complete — deterministic ZIP test, 7 release checksums and portable runs |
| 49 | Complete independent review | A different worker probes the integrated release; confirmed findings are resolved. | Complete — independent findings repaired and original reproductions rechecked |
| 50 | Ship the release candidate | Deliver the tested source ZIP, wheel, preview and publication handoff; identify external launch dependencies honestly. | Complete — local source ZIP, wheel, preview, checksums and [launch kit](launch-copy.md); public destination pending |
