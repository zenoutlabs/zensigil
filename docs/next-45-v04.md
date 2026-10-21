# ZenSigil 0.4: 45 implementation steps

The 45 steps implement and verify the capability assessment. They overlap deliberately: this is not a claim of 90 independent new features. External beginner-course participation and public-account access are not completion dependencies for this local language milestone.

| # | Outcome | Acceptance condition | Status |
|---|---|---|---|
| 1 | Define the 45-capability assessment | Record baseline, new scope and acceptance for each capability. | Verified — language-capabilities.md |
| 2 | Write the linguistic design rationale | Explain vocabulary, grammar, composition, reference and ambiguity. | Verified — linguistic-design.md |
| 3 | Specify the new grammar | Document EBNF, precedence, evaluation order and reserved-name migration. | Verified — grammar.ebnf; syntax-v04.md; compatibility.md |
| 4 | Implement explicit mutable bindings | var/set work lexically; let and inputs remain fixed. | Verified — tests/test_core_v04.py |
| 5 | Implement bounded while loops | Conditions are boolean and each iteration consumes steps. | Verified — tests/test_core_v04.py |
| 6 | Implement break/continue | Static checks and runtime target the nearest valid loop. | Verified — tests/test_core_v04.py |
| 7 | Implement annotated bindings | Declared types are checked on initial and later assignment. | Verified — tests/test_core_v04.py |
| 8 | Implement function signatures | Parameter/return types fail at the correct call or return. | Verified — tests/test_core_v04.py |
| 9 | Implement named function values | Aliases, function arguments, returns and dynamic calls work. | Verified — tests/test_core_v04.py |
| 10 | Implement lazy choice expressions | Only the selected branch evaluates. | Verified — tests/test_core_v04.py |
| 11 | Implement lazy null fallback | Only null selects fallback; missing fields still fail. | Verified — tests/test_core_v04.py |
| 12 | Implement membership operators | List, record and string membership have strict semantics. | Verified — tests/test_core_v04.py |
| 13 | Implement slices and list concatenation | Operations preserve input values and respect bounds. | Verified — tests/test_core_v04.py |
| 14 | Implement structured emitted values | Values appear in API/CLI/UI and obey transactional failure. | Verified — tests/test_core_v04.py |
| 15 | Implement executable test blocks | Tests isolate fixtures and do not execute main effects. | Verified — tests/test_core_v04.py |
| 16 | Add function call traces | Failures carry bounded source-aware frames. | Verified — tests/test_core_v04.py |
| 17 | Build bounded sequence helpers | Range, enumerate, zip, reverse and unique have explicit limits. | Verified — tests/test_stdlib_v04.py; stdlib.md |
| 18 | Build aggregation and ordering | sum, sorted and sort_by behave deterministically. | Verified — tests/test_stdlib_v04.py; stdlib.md |
| 19 | Build higher-order transformations | map/filter/fold/any/all call pure ZenSigil functions. | Verified — tests/test_stdlib_v04.py; stdlib.md |
| 20 | Build record transformations | Record inspection and immutable merge work. | Verified — tests/test_stdlib_v04.py; stdlib.md |
| 21 | Build text operations | Case, whitespace, splitting, joining and replacement are strict. | Verified — tests/test_stdlib_v04.py; stdlib.md |
| 22 | Build explicit conversions | type_of, parse_number, parse_json and json_text are bounded. | Verified — tests/test_stdlib_v04.py; stdlib.md |
| 23 | Build exact decimal-text operations | Canonical decimal text supports arithmetic, division, rounding and comparison. | Verified — tests/test_stdlib_v04.py; stdlib.md |
| 24 | Implement the module resolver | Explicit source maps resolve root-relative pure use imports. | Verified — tests/test_modules_v04.py; modules.md |
| 25 | Constrain host module loading | CLI file loading stays in the selected root; cycles and symlinks are checked. | Verified — tests/test_modules_v04.py; modules.md |
| 26 | Preserve module error locations | Module source and call traces identify the actual file. | Verified — tests/test_modules_v04.py; modules.md |
| 27 | Carry modules in portable files | 0.2/0.3 imports migrate to0.4; new module bundles survive roundtrips. | Verified — shared portable fixtures; browser export/CLI run |
| 28 | Build the formatter | Formatting is idempotent and preserves comments and semantic structure. | Verified — tests/test_tooling_v04.py; tooling.md |
| 29 | Expose formatter and AST in CLI | fmt --check/--write and ast --json work with useful failures. | Verified — tests/test_tooling_v04.py; tooling.md |
| 30 | Add project manifests and scaffolding | init creates a runnable project; directory commands use its manifest. | Verified — tests/test_tooling_v04.py; tooling.md |
| 31 | Run project tests from CLI | test runs declared tests and produces machine-readable results. | Verified — tests/test_tooling_v04.py; tooling.md |
| 32 | Add local HTTP tools | Run/check/test/format use the same semantics and supplied modules. | Verified — tests/test_modules_v04.py HTTP checks |
| 33 | Expose rich language tools in playground | Format, tests, modules and emitted values work through visible controls. | Verified — release-evidence-v04.md browser checks |
| 34 | Update highlighting and reference | The editor and guide understand the new vocabulary and signatures. | Verified — Guide.jsx; live function search verified |
| 35 | Package editor support | Ship a VSCode-compatible syntax/snippet extension as a local installable artifact. | Verified — local VSIX integrity/metadata checks; host launch untested |
| 36 | Add an algorithm example | An iterative algorithm uses typed state and loops with fixed expected output. | Verified — examples/algorithms.zs; golden output |
| 37 | Add a transformation example | Higher-order functions transform a collection into structured values. | Verified — examples/transformations.zs; golden output |
| 38 | Add a module example | Reusable pure source and explicit tests travel in one portable program. | Verified — examples/module-lab.zs; browser/CLI roundtrip |
| 39 | Add a decimal example | Exact decimal-text operations demonstrate rounding and equality boundaries. | Verified — examples/decimal-lab.zs; golden output |
| 40 | Add an executable conformance corpus | Examples test language principles independently of proposal explanations. | Verified — conformance/language.zs (8 test blocks) |
| 41 | Run cross-version and interface checks | Existing examples plus new grammar/CLI/HTTP/codec cases pass. | Verified — 168 Python tests on 3.9.6 and 3.12; 45 Node tests |
| 42 | Review semantics independently | A different worker probes ambiguity, scope, purity and limits; findings are resolved. | Verified — independent worker reviews; resolved findings in release-evidence-v04.md |
| 43 | Validate rendered flows | Desktop/mobile browser checks exercise modules, formatting, tests, values and errors. | Verified — 390px and 1440px rendered QA; screenshot evidence |
| 44 | Verify installed delivery | Build/install the wheel outside the source checkout and verify packaged tools/examples. | Verified — fresh isolated Python 3.12 wheel install verified |
| 45 | Deliver the language milestone | Version0.4 docs, evidence, source, wheel, extension and checksums reflect actual capabilities. | Verified — versioned ZIP/wheel/VSIX/checksums; release-evidence-v04.md |
