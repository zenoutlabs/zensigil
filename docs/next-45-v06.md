# ZenSigil 0.6: 45 outcomes for larger programs and developer adoption

This milestone extends 0.5 with module boundaries, an interactive shell, collection
operations and test reports. The count includes delivery and verification; it is
not a claim of 45 independent syntax features or a finished language.

| # | Outcome | Acceptance | Status/evidence |
|---|---|---|---|
| 1 | Named module imports | use path as alias parses with clear errors. | Done — modules-v06.md; test_modules_v06.py |
| 2 | Isolated module function identities | Same helper names in separate modules coexist. | Done — modules-v06.md; test_modules_v06.py |
| 3 | Explicit public functions | export fn declares module API. | Done — modules-v06.md; test_modules_v06.py |
| 4 | Private helpers | Unexported helpers remain internal in explicit-export modules. | Done — modules-v06.md; test_modules_v06.py |
| 5 | Legacy import compatibility | Unmarked modules and bare imports preserve existing programs. | Done — modules-v06.md; test_modules_v06.py |
| 6 | Transitive imports | Each source resolves its own module aliases. | Done — modules-v06.md; test_modules_v06.py |
| 7 | Module name collisions | Duplicate aliases and conflicting exposed functions fail clearly. | Done — modules-v06.md; test_modules_v06.py |
| 8 | Qualified function values | Namespace members pass as callbacks and can be returned. | Done — modules-v06.md; test_modules_v06.py |
| 9 | Namespaces in closures | Captured module references preserve source identity. | Done — modules-v06.md; test_modules_v06.py |
| 10 | Opaque module values | Namespace handles cannot become JSON records or effects. | Done — modules-v06.md; test_modules_v06.py |
| 11 | Namespace annotation | Runtime namespace type has explicit meaning. | Done — modules-v06.md; test_modules_v06.py |
| 12 | Module tests | Imported tests execute in their defining source scope. | Done — modules-v06.md; test_modules_v06.py |
| 13 | Inspectable and formattable syntax | New constructs preserve source locations and formatting meaning. | Done — modules-v06.md; test_modules_v06.py |
| 14 | Bounded module work | Existing cycle, count, path, depth and work limits remain effective. | Done — modules-v06.md; test_modules_v06.py |
| 15 | Member completion | Editor suggests public members after a namespace dot. | Done — editor.md; test_editor_v06.py; protocol/client checks |
| 16 | Qualified hover | Imported member signatures identify their declaration. | Done — editor.md; test_editor_v06.py; protocol/client checks |
| 17 | Qualified definitions | Member names navigate to the correct module source. | Done — editor.md; test_editor_v06.py; protocol/client checks |
| 18 | Scope-correct editor names | Private and unrelated module names do not leak. | Done — editor.md; test_editor_v06.py; protocol/client checks |
| 19 | Unsaved module APIs | Editor reflects changed exports in open buffers. | Done — editor.md; test_editor_v06.py; protocol/client checks |
| 20 | Grammar and snippets | Editor syntax support covers as and export. | Done — editor.md; test_editor_v06.py; protocol/client checks |
| 21 | Persistent REPL cells | Successful cells form a replayable session. | Done — repl.md; test_repl_v06.py and test_cli_v06.py |
| 22 | Expression exploration | Bare expressions return structured values. | Done — repl.md; test_repl_v06.py and test_cli_v06.py |
| 23 | Multiline REPL input | Indented declarations and blocks can be entered. | Done — repl.md; test_repl_v06.py and test_cli_v06.py |
| 24 | Transactional REPL errors | Failed cells preserve earlier successful state. | Done — repl.md; test_repl_v06.py and test_cli_v06.py |
| 25 | Output deltas | Only new cell outputs are displayed. | Done — repl.md; test_repl_v06.py and test_cli_v06.py |
| 26 | Undo and reset | Session changes can be reversed or cleared. | Done — repl.md; test_repl_v06.py and test_cli_v06.py |
| 27 | REPL help and source inspection | Commands expose state and usage. | Done — repl.md; test_repl_v06.py and test_cli_v06.py |
| 28 | Explicit REPL input and modules | Launch options supply bounded JSON/module maps. | Done — repl.md; test_repl_v06.py and test_cli_v06.py |
| 29 | REPL loading and export | Explicit source loads and exclusive portable saves work. | Done — repl.md; test_repl_v06.py and test_cli_v06.py |
| 30 | REPL resource limits | Cumulative source and replay work are bounded. | Done — repl.md; test_repl_v06.py and test_cli_v06.py |
| 31 | Cumulative folds | scan produces stable intermediate accumulators. | Done — stdlib.md; test_stdlib_v06.py |
| 32 | Keyed extrema | min_by and max_by define stable ties and empty results. | Done — stdlib.md; test_stdlib_v06.py |
| 33 | Keyed numeric aggregation | sum_by validates numeric callback results. | Done — stdlib.md; test_stdlib_v06.py |
| 34 | Keyed uniqueness | unique_by uses deterministic strict structural keys. | Done — stdlib.md; test_stdlib_v06.py |
| 35 | Frequency counts | frequencies counts string values in stable order. | Done — stdlib.md; test_stdlib_v06.py |
| 36 | Single-level flattening | flatten checks and bounds every nested list. | Done — stdlib.md; test_stdlib_v06.py |
| 37 | Records from entries | record_from_entries validates pairs and rejects duplicate keys. | Done — stdlib.md; test_stdlib_v06.py |
| 38 | JUnit interoperability | Test results become bounded escaped XML with honest failures/errors. | Done — test-reports.md; report and CLI regression tests |
| 39 | Protected report files | CLI --junit never overwrites input or existing files. | Done — test-reports.md; report and CLI regression tests |
| 40 | Runnable adoption examples | New module and collection programs have independent expected outputs. | Done — 23 example fixtures; two new browser-verified programs |
| 41 | Portable migration | Older supported programs normalize to the new version. | Done — shared Python/JS portable fixtures; compatibility.md |
| 42 | Release integration | Python, JS, editor and installed-package checks pass with limitations recorded. | Done — release-evidence-v06.md; VS Code host limitation recorded |
| 43 | Verified distributables | Wheel, VSIX, source ZIP and checksums match the release. | Done — 17 checksums, archive verification and installed-wheel smoke |
| 44 | Public source repository | Reviewed source is available at zenoutlabs/zensigil. | In progress |
| 45 | Public delivery verification | Published files and actual remote checks are inspected. | In progress |
