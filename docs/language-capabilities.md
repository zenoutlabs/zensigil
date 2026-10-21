# What a good language needs: 45 capabilities

These are design goals for ZenSigil, not a universal requirement that every language needs the same feature set. A capability can be retained, strengthened or newly implemented. Version 0.6 adds scoped module namespaces, explicit exports and an interactive shell on top of 0.5 closures and recursive runtime annotations. Stateful closures, native decimal values, static inference, async execution, a package registry and an optimizing compiler remain separate future designs. The additional-capabilities assessment extends this baseline.

| # | Capability | Acceptance | Change | Evidence/status |
|---|---|---|---|---|
| 1 | A consistent vocabulary | Each keyword has a stable grammatical role. | Strengthen | Verified — docs/linguistic-design.md |
| 2 | An explicit lexical specification | Characters, identifiers, strings, comments and numbers have written rules. | Strengthen | Verified — docs/language.md; docs/grammar.ebnf |
| 3 | An unambiguous grammar | Source has one documented structural reading. | Strengthen | Verified — docs/grammar.ebnf; docs/syntax-v04.md |
| 4 | Predictable operator precedence | Grouping and associativity are specified and exercised. | Strengthen | Verified — conformance/language.zs; tests/test_core_v04.py |
| 5 | Compositional expressions | Expressions combine into larger expressions without ad hoc interpretation. | Strengthen | Verified — tests/test_core_v04.py |
| 6 | Explicit evaluation order | Operands and arguments evaluate in a defined order. | Retain | Verified — docs/syntax-v04.md; tests/test_language.py |
| 7 | Lexical scope | Names refer to the nearest visible binding. | Strengthen | Verified — tests/test_core_v04.py |
| 8 | Immutable bindings | let cannot be reassigned. | Retain | Verified — tests/test_core_v04.py |
| 9 | Explicit local mutation | var and set permit state changes without changing let semantics. | New | Verified — tests/test_core_v04.py |
| 10 | Strict value types | Strings, numbers and booleans are not implicitly interchanged. | Retain | Verified — tests/test_language.py |
| 11 | Optional type annotations | Bindings, parameters and returns can declare runtime-checked types. | New | Verified — tests/test_core_v04.py |
| 12 | Reusable functions | Calculations accept arguments and return results. | Strengthen | Verified — tests/test_core_v04.py |
| 13 | First-class named functions | Named function references can be passed, returned and called. | New | Verified — tests/test_core_v04.py |
| 14 | Higher-order collection operations | map, filter and fold compose reusable calculations. | New | Verified — tests/test_stdlib_v04.py |
| 15 | Effect boundaries | Functions and imported libraries cannot emit external-looking effects. | Strengthen | Verified — tests/test_modules_v04.py |
| 16 | Structured output | emit returns JSON values independently of notes and proposals. | New | Verified — tests/test_modules_v04.py; release browser checks |
| 17 | Conditional statements | when and otherwise express branch structure. | Retain | Verified — tests/test_language.py |
| 18 | Conditional expressions | choose condition then value otherwise fallback is lazy. | New | Verified — tests/test_core_v04.py |
| 19 | Lazy boolean logic | and/or short-circuit with strict booleans. | Retain | Verified — tests/test_language.py |
| 20 | Explicit null fallback | ?? handles null lazily while missing fields remain errors. | New | Verified — tests/test_core_v04.py |
| 21 | Collection iteration | for visits collection values in order. | Retain | Verified — tests/test_language.py |
| 22 | Bounded conditional loops | while supports iterative algorithms under the step limit. | New | Verified — tests/test_core_v04.py |
| 23 | Structured loop control | break and continue stay inside their nearest loop. | New | Verified — tests/test_core_v04.py |
| 24 | Collection composition | Concatenation, slices and sequence helpers build new values. | New | Verified — tests/test_stdlib_v04.py; tests/test_core_v04.py |
| 25 | Membership and structural equality | in/not in and equality have strict documented semantics. | Strengthen | Verified — conformance/language.zs |
| 26 | Record transformation | keys, values, entries and merge work across domains. | New | Verified — tests/test_stdlib_v04.py |
| 27 | Text processing | Unicode-aware string operations support ordinary data work. | New | Verified — tests/test_stdlib_v04.py |
| 28 | Numeric aggregation and ordering | Numeric sums and stable sorting have clear type rules. | New | Verified — tests/test_stdlib_v04.py |
| 29 | Exact decimal operations | Explicit decimal-text helpers avoid float quantity surprises. | New | Verified — tests/test_stdlib_v04.py; examples/decimal-lab.zs |
| 30 | Strict JSON interoperability | JSON parsing/serialization is explicit and bounded. | Strengthen | Verified — tests/test_stdlib_v04.py |
| 31 | Local reusable modules | Explicit use declarations load supplied pure source modules. | New | Verified — tests/test_modules_v04.py |
| 32 | Module boundaries and diagnostics | Missing modules, cycles, collisions and paths fail clearly. | New | Verified — tests/test_modules_v04.py |
| 33 | Program invariants | require states relationships that must hold. | Retain | Verified — tests/test_language.py |
| 34 | Executable language tests | test blocks verify expectations without running the main program. | New | Verified — tests/test_core_v04.py; conformance/language.zs |
| 35 | Transactional failure | Failed runs discard notes, values and proposals. | Strengthen | Verified — tests/test_modules_v04.py |
| 36 | Actionable diagnostics | Errors identify the source, location and likely correction. | Strengthen | Verified — tests/test_modules_v04.py; release browser checks |
| 37 | Function call traces | Nested failures show the chain of calls. | New | Verified — tests/test_modules_v04.py |
| 38 | Deterministic execution | Same explicit inputs and code yield equivalent results. | Retain | Verified — tests/test_release_behavior.py |
| 39 | Explicit resource limits | New loops, libraries and modules respect bounded work. | Strengthen | Verified — tests/test_core_v04.py; tests/test_stdlib_v04.py |
| 40 | A semantics-preserving formatter | Formatting preserves comments and program meaning. | New | Verified — tests/test_tooling_v04.py |
| 41 | Inspectable syntax trees | A stable AST document makes parsing visible. | New | Verified — tests/test_tooling_v04.py |
| 42 | A project structure | A manifest identifies entry code and project test files. | New | Verified — tests/test_tooling_v04.py; tools/verify_install.py |
| 43 | Editor support | Syntax highlighting, brackets and snippets are distributable. | New | Verified — editors/vscode; local VSIX verified; actual host provider checks blocked by workspace trust; see release-evidence-v05.md |
| 44 | Portable versioned programs | Code, input, contracts and modules travel together. | Strengthen | Verified — tests/fixtures/portable-cases.json; release browser/CLI roundtrip |
| 45 | A specification and conformance suite | Language claims map to examples and observable checks. | Strengthen | Verified — docs/syntax-v04.md; conformance/language.zs; release-evidence-v04.md |
