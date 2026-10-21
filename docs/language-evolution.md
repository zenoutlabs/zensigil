# Evolving ZenSigil deliberately

ZenSigil is experimental before 1.0. A larger keyword inventory is not a measure
of language quality. New constructs should compose with existing scope, type,
effect and error rules, and solve a concrete program-writing problem.

For a language change, open a focused proposal with:

1. A small motivating program and the current obstacle.
2. Proposed spelling, grammar, precedence and ambiguity resolution.
3. Evaluation order, scope/capture, type, equality and effect semantics.
4. Representative successes and failures, including empty and boundary cases.
5. Interaction with modules, formatting, diagnostics, tests and portable files.
6. Resource limits, compatibility costs and a migration example.
7. Alternatives and the observable acceptance conditions for implementation.

A proposal does not become a language promise until implementation, specification
and independent regression expectations agree. A local passing test is not evidence
of public deployment, cross-platform CI, human usability or performance superiority.
Report those outcomes separately. Keep experimental limitations visible in releases.

Prioritize a small number of coherent changes per release. Grammar changes should
include the parser/checker/runtime, formatter, editor grammar, examples and migration
notes in one tested release. Pure libraries are preferable when a keyword is not
necessary. Industry-specific policies belong in programs and contracts.

For 1.0, define the compatibility window, deprecation process, supported platforms,
conformance commitments, security-reporting route and maintainer decision process
based on outside developer use. MIT licensing is already included; package-registry
ownership and publication must be verified before advertising registry installs.
