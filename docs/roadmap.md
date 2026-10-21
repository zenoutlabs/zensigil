# ZenSigil roadmap

## Delivered in 0.6

Source-scoped module identities, named imports, explicit exports, private helpers,
namespace function values and closure captures. A bounded transactional REPL,
eight collection functions, JUnit reports and editor namespace navigation accompany
the language changes. See [the 45-outcome ledger](next-45-v06.md) for acceptance evidence.
The public source destination is [zenoutlabs/zensigil](https://github.com/zenoutlabs/zensigil).

## Next priorities from real programs

1. Multi-error parser recovery and more precise diagnostic spans.
2. A typed intermediate representation and conservative static checks.
3. User-defined record schemas and deliberate pattern-matching semantics.
4. A debugger with source stepping, immutable snapshots and explicit limits.
5. Measured performance work before choosing bytecode or native compilation.
6. Versioned package manifests and lockfile semantics before a package registry.
7. A capability model before adding filesystem, network or asynchronous effects.
8. Independent developer trials, compatibility fixtures and a stable 1.0 process.

These are future designs, not hidden capabilities of the current release. Python
hosts the interpreter; users write and execute ZenSigil syntax. MIT source publication
and local packaging do not imply PyPI or editor-marketplace publication.
