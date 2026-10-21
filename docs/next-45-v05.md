# ZenSigil 0.5: 45 steps toward developer adoption

This is a bounded release plan. The prior 45 language capabilities remain a baseline;
new work extends them. Public access and actual remote checks are tracked separately
from local implementation. Prompt-library curation is a separate user-requested chat.

| # | Outcome | Acceptance | Status/evidence |
|---|---|---|---|
| 1 | Audit the prior 45 capabilities | Retained claims map to code/tests, with limitations preserved. | Complete — language-capabilities.md; additional-capabilities.md |
| 2 | Expand the language capability assessment | Additional needs have implemented, partial or future status; no blanket completeness claim. | Complete — language-capabilities.md; additional-capabilities.md |
| 3 | Specify new grammar and semantics | Anonymous functions, captures and type syntax have explicit rules. | Complete — syntax-v05.md; test_core_v05.py |
| 4 | Add anonymous function expressions | Typed/untyped fn expressions parse and execute. | Complete — syntax-v05.md; test_core_v05.py |
| 5 | Add lexical capture | Closures preserve values from their definition environment. | Complete — syntax-v05.md; test_core_v05.py |
| 6 | Compose and return closures | Factories and callbacks work under existing call limits. | Complete — syntax-v05.md; test_core_v05.py |
| 7 | Bound closure capture and preserve purity | Captures consume budget and cannot mutate outer bindings. | Complete — syntax-v05.md; test_core_v05.py |
| 8 | Add nested list annotations | list<T> checks elements at runtime with bounded traversal. | Complete — syntax-v05.md; test_core_v05.py |
| 9 | Add record value annotations | record<T> checks string-keyed values recursively. | Complete — syntax-v05.md; test_core_v05.py |
| 10 | Add union and nullable annotations | T | U and T | null work on bindings, parameters and returns. | Complete — syntax-v05.md; test_core_v05.py |
| 11 | Diagnose richer type failures | Useful type messages identify the failing program location. | Complete — syntax-v05.md; test_core_v05.py |
| 12 | Group collections | group_by preserves stable order and requires string keys. | Complete — stdlib.md; test_stdlib_v05.py |
| 13 | Count collection groups | count_by produces explicit counts with strict keys. | Complete — stdlib.md; test_stdlib_v05.py |
| 14 | Partition collections | partition returns matched/unmatched lists with strict booleans. | Complete — stdlib.md; test_stdlib_v05.py |
| 15 | Flatten transformations | flat_map builds bounded lists from callbacks. | Complete — stdlib.md; test_stdlib_v05.py |
| 16 | Find elements and positions | find and find_index define absent/empty behavior. | Complete — stdlib.md; test_stdlib_v05.py |
| 17 | Take and drop sequence prefixes | Counts are integers, nonnegative, and clamp at length. | Complete — stdlib.md; test_stdlib_v05.py |
| 18 | Chunk sequences | Positive sizes produce stable bounded chunks. | Complete — stdlib.md; test_stdlib_v05.py |
| 19 | Project record fields | record_pick/record_omit preserve original record order. | Complete — stdlib.md; test_stdlib_v05.py |
| 20 | Clamp numeric values | clamp validates numeric bounds and ordering. | Complete — stdlib.md; test_stdlib_v05.py |
| 21 | Implement editor protocol transport | Bounded Content-Length JSON-RPC runs over stdio. | Complete locally — editor-v05.md; test_lsp_v05.py; editor client tests |
| 22 | Implement editor lifecycle | Initialize, shutdown and exit behave predictably. | Complete locally — editor-v05.md; test_lsp_v05.py; editor client tests |
| 23 | Check unsaved editor documents | Open/change/close overlays produce diagnostics without execution. | Complete locally — editor-v05.md; test_lsp_v05.py; editor client tests |
| 24 | Complete language names | Keywords, built-ins and declarations appear in completion. | Complete locally — editor-v05.md; test_lsp_v05.py; editor client tests |
| 25 | Show hover information | Signatures and language information are available at identifiers. | Complete locally — editor-v05.md; test_lsp_v05.py; editor client tests |
| 26 | Navigate definitions | Local and supplied module names lead to source locations. | Complete locally — editor-v05.md; test_lsp_v05.py; editor client tests |
| 27 | Expose document symbols | Declarations are available to editor navigation. | Complete locally — editor-v05.md; test_lsp_v05.py; editor client tests |
| 28 | Format through the editor protocol | Formatting produces UTF-16 text edits preserving semantics. | Complete locally — editor-v05.md; test_lsp_v05.py; editor client tests |
| 29 | Integrate VS Code | Trusted workspaces use the installed runtime through a bounded client. | Complete locally — editor-v05.md; test_lsp_v05.py; editor client tests |
| 30 | Add advisory lint checks | Unused bindings, shadowing and unreachable statements get stable warning codes. | Complete — developer-workflows.md; test_cli_v05.py |
| 31 | Lint explicit projects | Entry/tests/imports are checked; strict warnings are opt-in. | Complete — developer-workflows.md; test_cli_v05.py |
| 32 | Format explicit projects | All sources preflight before per-file atomic writes; unrelated files untouched. | Complete — developer-workflows.md; test_cli_v05.py |
| 33 | Support source from stdin | run/check/test/lint/fmt/ast accept bounded source; imports require an explicit root. | Complete — developer-workflows.md; test_cli_v05.py |
| 34 | Filter test runs | Selected test names run; excluded bodies do not execute. | Complete — developer-workflows.md; test_cli_v05.py |
| 35 | List tests without running them | Discovery reports names and zero execution steps, without claiming passes. | Complete — developer-workflows.md; test_cli_v05.py |
| 36 | Fail empty test selections on demand | --fail-if-empty supports CI without changing default behavior. | Complete — developer-workflows.md; test_cli_v05.py |
| 37 | Add substantial runnable examples | Closures, typed transformations and collection analysis match independent expected values. | Complete — 21 golden examples; three new browser examples verified |
| 38 | Migrate portable files and manifests | 0.2–0.4 files open with documented reserved-name changes. | Complete — compatibility.md; shared codec and project tests |
| 39 | Prepare developer documentation and contribution process | Quickstart, API/tool references, language-change RFC guidance and known limits agree. | Complete — README; language-evolution.md; current documentation reviewed |
| 40 | Verify compatibility and conformance | Existing and new Python/JavaScript behavior suites pass. | Complete — 227 Python tests on 3.9 and 3.12; 45 playground tests |
| 41 | Verify editor integration | Protocol and client tests pass; actual host evidence or limitations are recorded. | Bounded verification complete — 16 protocol + 6 client tests; actual VS Code host stopped at workspace-trust gate, providers unverified there |
| 42 | Verify distributable packages | Fresh wheel install, VSIX payload, source archive and hashes are checked. | Complete — fresh wheel install; VSIX payload; reproducible ZIP; 15 checksums; release-evidence-v05.md |
| 43 | Create the public repository | ZenOutMan/zensigil exists publicly under the authorized owner. | Blocked on account access — connector cannot create repositories; browser account differs from authorized owner |
| 44 | Publish reviewed source | Public files match the tested release source; remote commit is recorded. | Pending #43 — reviewed local source and release artifacts ready |
| 45 | Verify public delivery | Repository onboarding and actual remote checks are inspected; release status is explicit. | Pending #43–44 — remote commit, GitHub release and CI success are not claimed |
