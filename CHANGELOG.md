# Changelog

## 0.8.0 — projects that travel with their tests

- Keep separate test files and test-only modules in portable programs. Unpack a runnable project with its input and contracts.
- Run bundled tests in the terminal and playground. Shared module tests run once under a shared work limit.
- Add editor Find References, import refresh, workspace-folder updates, and a server restart command.
- Check collection results before retaining them. Report earlier callback errors and more precise bracket errors.
- Reject invalid Python execution limits with a structured error.
- Reject empty or incomplete release manifests. Verify expected proposals and notes as well as structured values.
- Keep the source grammar. See [compatibility](docs/compatibility.md) for changed limits, test counts, and diagnostic behavior.
- Define the outside-use and compatibility evidence needed before beta and stable releases. 0.8 remains experimental.

## 0.7.0 — developer adoption and type advice

- Add bounded input and contract paths to project manifests, with explicit flag overrides.
- Export a runnable project with `pack PROJECT`.
- Add conservative type warnings to lint, editor diagnostics, and the playground.
- Keep warning severity separate from blocking errors.
- Improve the project starter and add an isolated first-task check.
- Return diagnostics for invalid manifest versions and output symlink loops.
- Add a current 45-needs audit, public claim check, feedback forms, and a proposed developer trial.
- Preserve the source grammar and runtime behavior. The checks do not provide full static type inference.


## 0.6.0 — 2026-10-21

- Named module imports, explicit exports, private helpers and isolated source scopes.
- Opaque namespace references, qualified function values and closure captures.
- A transactional replay REPL with expressions, multiline cells, undo/reset and portable saves.
- Eight collection operations: scan, min_by, max_by, sum_by, unique_by, frequencies, flatten and record_from_entries.
- JUnit XML test reports with protected output paths and honest failure/error counts.
- Namespace-aware editor completion, hover and definition navigation.
- Two runnable examples, 0.2–0.5 portable migration and public source under zenoutlabs/zensigil.
- New reserved words as/export and new standard names; libraries must import their own dependencies. See docs/compatibility.md.

## 0.5.0 — developer adoption milestone

- Add anonymous pure functions, immutable lexical snapshots, nested returned closures,
  recursive list/record annotations and union/nullable types.
- Add 12 bounded collection/record/numeric functions, bringing the library to 61.
- Add a stdio language server and VS Code diagnostics, completion, hover, definitions,
  symbols and formatting with UTF-16 positions and unsaved module overlays.
- Add advisory linting, explicit project formatting, stdin source and test filtering,
  listing and optional empty-suite failure.
- Add three examples, developer workflows, evolution guidance and a 75-capability assessment.
- Preserve invalid project manifests from diagnostic-output replacement; keep stdin
  imports behind an explicit module root, including failure paths.

Annotations remain runtime checks. Closures snapshot immutable values; there are
no mutable captured cells. Public publication and actual remote checks are recorded
separately in the 0.5 release evidence.

## 0.4.0 — expressive language milestone

- Add explicit typed local state, while, break/continue, lazy choices/null fallback,
  membership, slices, list composition and first-class named functions.
- Add structured emit results, isolated test blocks, runtime annotation checks and
  source-aware call traces. Functions keep their explicit effect boundary.
- Add 37 pure library functions for transformations, records, sequences, text,
  conversions and exact decimal-text operations.
- Add supplied pure source modules, project manifests, scaffolding, a formatter,
  AST inspection, module-aware portable files and command-line tests.
- Add playground formatting, testing, modules, values, call traces and a live
  standard-function reference, plus four substantial examples.
- Package local VS Code highlighting/snippets and saved-file diagnostics as VSIX.

New reserved names require migration if an earlier program used them. Annotations
are runtime checks, decimal helpers operate on text, and named function values do
not capture local environments. See the capability matrix and implementation ledger
for evidence and explicit limits. This local milestone does not establish public
publication, remote CI success, human adoption or production readiness.

## 0.3.0 — adoption preview

- Run and check exported `.sigil.json` programs directly from the command line.
- Pack and unpack portable programs, scaffold bundled examples, diagnose an
  installation, and save preview JSON to a file with overwrite protection.
- Optionally validate proposals against a closed action-to-fields contract map.
  Invalid outputs discard the whole preview and identify the affected field.
- Check programs independently from running them in the playground. Download
  source, inspect proposal origins, jump to source errors, use save/run shortcuts,
  remove named saves, and refresh library choices across tabs.
- Preserve 0.2 portable files and browser drafts when opening them in 0.3.
- Add reading-list, event-capacity and project-budget examples, a beginner course,
  troubleshooting, embedding and compatibility documentation.
- Add release packaging checks, shared compatibility fixtures, example expectations
  and CI configuration for multiple operating systems.

The core syntax is unchanged. The runtime still runs locally, uses floating point
for ordinary decimal arithmetic, and only describes proposed actions. It has no
connectors, durable approvals, hosted accounts or action executor. Local checks do
not claim that CI has already run on other operating systems.

## 0.2.0

Input contracts, `require`, exact quantity helpers, readable explanations, named
browser saves, draft recovery, portable files and the MIT license.

## 0.1.0

Initial custom lexer, parser, checker, interpreter, CLI and local playground.
