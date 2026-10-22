# When ZenSigil can be called stable

ZenSigil is already a programming language. It has its own source syntax,
name rules, value rules, parser, and interpreter. Python implements the
interpreter. This does not make a ZenSigil program a Python program.

Experimental describes the project's promises. It does not mean the language
is fake. A stable release means users can depend on a defined set of behavior.
It does not mean that every possible program is correct or that no bugs remain.

## Current decision

Keep 0.8 experimental. It is suitable for small local projects and focused
developer trials. A website project entry and a request for feedback are
reasonable. Claims of production readiness or broad adoption are not supported.

The largest missing evidence is outside use. Another large feature list cannot
supply that evidence. There is no reliable completion date until developers try
the language and report what fails.

## Gate A: a beta for outside developers

1. Publish a tested release with verified downloads and working setup instructions.
2. Define the supported public surface below and record the current behavior.
3. Complete a five-person first-task trial. At least four people must finish
   without the author repairing their environment or source for them.
4. Record setup time, failures, unclear syntax, and incorrect results. Preserve
   failed attempts. A negative report is as useful as a successful one.
5. Fix every reproducible defect that blocks the documented first task. Add a
   regression test for each fix. Ask affected testers to repeat the failed step.
6. Check the VS Code extension in a trusted test workspace on the supported host.
   Do not disable workspace trust for this test.

The five-person threshold is a project release rule, not a statistical proof.
The proposed $100 trial could pay five people $20 each for their time and report.
It is not active. Payment terms and a payment route still need a decision.

## Gate B: a stable 1.0

1. Freeze the public surface for a release candidate. Record all deliberate
   exceptions. Publish a migration note for any change from the beta.
2. Run at least three independently written programs in different problem areas.
   Include one reusable module and one saved project that another developer opens.
3. Keep the release candidate in use for at least 30 days. This is an observation
   window, not a substitute for use. Record the programs and their outcomes.
4. Have no unresolved critical or high-impact defect in the supported workflows.
   Critical means data loss, an incorrect result without an error, or a boundary
   failure with serious consequences. High impact means a documented common task
   cannot be completed and has no practical workaround.
5. Pass the full language suite, compatibility fixtures, supported platform jobs,
   fresh package installation, and release-download verification.
6. Publish a maintenance policy, supported versions, and a way to report defects.
   Give changes to stable behavior a deprecation and migration path.

If a release-candidate fix changes language behavior, repeat the affected checks
and extend the observation window for that behavior. Do not reset unrelated work.

## Proposed 1.0 public surface

| Surface | Intended promise | Current boundary |
|---|---|---|
| Source syntax and evaluation | A valid supported program keeps its meaning in 1.x | Pre-1.0 changes remain possible |
| Values and built-ins | Documented arguments, results, and errors remain compatible | Resource limits can reject large work |
| Modules | Import, export, and scope rules remain compatible | Explicit local source only |
| Input and proposal contracts | Documented contract subset remains compatible | Not the full JSON Schema standard |
| CLI commands and exit status | Documented commands remain available in 1.x | Human error wording can improve |
| JSON result fields and diagnostic codes | Required field shapes and published codes remain compatible | Extra fields can be added; wording is not an API |
| Portable files and project manifests | Supported versions remain readable, with documented migrations | Files do not include an interpreter |
| Python API | Documented entry points remain compatible | Internal modules and AST shapes are private |
| Editor protocol | Supported Language Server Protocol methods remain compatible | Completion and advice can improve |
| Proposal IDs | No stable external delivery promise yet | They are not durable idempotency keys |

## What is not required for 1.0

Classes, a native compiler, a package registry, macros, asynchronous work, and an
action executor are not automatic requirements. Add them only when a useful
program needs them and the design fits. Stability is possible with a smaller scope.

## How far away?

The remaining path has two evidence milestones: a successful outside trial, then
a release candidate used under the compatibility policy. There is at least a
30-day observation stage after that candidate is ready. This is a chosen release
condition, not a forecast. Recruitment and the defects found can extend the work.

Read the [0.8 evidence](release-evidence-v08.md) for the checks that actually passed.
Read the [developer trial brief](developer-trial.md) before starting a paid trial.
