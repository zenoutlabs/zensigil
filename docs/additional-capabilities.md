# Beyond the first 45: 30 additional language and ecosystem needs

The original [45-capability assessment](language-capabilities.md) is a tested baseline,
not a declaration that ZenSigil has every feature any language could need. The
following 30 additions bring the assessment to 75. These are design and adoption
concerns, not a demand to implement every paradigm. A language can deliberately
omit a feature; claims must still explain the choice.

| # | Capability | Current status and evidence |
|---|---|---|
| 46 | Anonymous function expressions | 0.5 implemented; syntax-v05.md and test_core_v05.py |
| 47 | Lexical closures with defined capture timing | 0.5 immutable snapshot captures; no mutable captured cells |
| 48 | Function composition and factories | 0.5 returned/nested closures and callbacks; closure-lab example |
| 49 | Recursive collection annotations | 0.5 list<T> and record<T>; bounded runtime traversal |
| 50 | Explicit type alternatives | 0.5 unions including null; no implicit coercion |
| 51 | Data grouping and partitioning | 0.5 stable pure standard functions; test_stdlib_v05.py |
| 52 | A documented value and memory model | Immutable JSON collections, explicit rebinding, bounded capture snapshots; host memory management |
| 53 | Editor protocol interoperability | 0.5 stdio language server; editor-v05.md |
| 54 | Unsaved-buffer diagnostics | 0.5 open-document overlays and version handling |
| 55 | Completion and hover | 0.6 lexical names, signatures and direct namespace members; no general type inference |
| 56 | Navigation and editor formatting | 0.5 definitions, symbols and UTF-16 formatting edits |
| 57 | Advisory code-quality analysis | 0.5 unused, shadowed and unreachable-source warnings; conservative and opt-in |
| 58 | Automation-friendly command lines | 0.5 bounded stdin, JSON results and meaningful exit codes |
| 59 | Selective test discovery and execution | 0.5 list/filter/empty-selection modes; never count listed tests as passes |
| 60 | Project-level source tooling | 0.5 explicit source graph lint/format; no implicit directory scan |
| 61 | Backward compatibility and migration | 0.2–0.5 portable readers retained; new reserved names documented |
| 62 | Public source and issue reporting | Public zenoutlabs/zensigil source; release evidence records remote verification separately |
| 63 | A contribution and language-change process | CONTRIBUTING.md and language-evolution.md define focused proposals and review criteria |
| 64 | Reproducible builds and provenance | Source ZIP deterministic for fixed bytes/compressor; wheel reproducibility and signing remain future work |
| 65 | Installation from a clean environment | Release install verifier checks wheel resources and developer workflows |
| 66 | Independent semantic review | Separate workers and randomized probes; no claim of independent human adoption |
| 67 | Cross-platform behavior | Local Python compatibility tests plus CI matrix; actual remote results recorded separately |
| 68 | Performance baselines | Repeatable benchmark script records environment and verified workloads; no superiority claims |
| 69 | Error recovery while editing | Diagnostics on incomplete source; multi-error parser recovery remains future work |
| 70 | Static inference and user-defined data types | Future design: distinguish optional annotations from a full static type system |
| 71 | Module namespaces, exports and dependency resolution | 0.6 namespaces, exports and source-scoped resolution; registry/package resolution remains future work |
| 72 | Interactive REPL and debugger | 0.6 transactional replay REPL with undo and bounded work; stepping debugger remains future work |
| 73 | Explicit host interoperability | Current JSON/Python API boundary; controlled file/network adapters remain future work |
| 74 | Concurrency and asynchronous effects | Future design: needs scheduling, cancellation, error and capability semantics |
| 75 | Stable 1.0 specification and ecosystem governance | Future milestone requiring compatibility evidence, outside use and deliberate release policy |

The next language architecture decisions should prioritize static analysis and
error recovery from real programs, then a debugger with explicit stepping semantics.
Native decimal values, pattern matching, algebraic data types, generics, package
registries, native compilation and async I/O are candidate designs. They should
enter a release only with coherent semantics and observable acceptance criteria.
