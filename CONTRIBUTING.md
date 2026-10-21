# Reviewing ZenSigil

This is an early AI-assisted language project. Specific, reproducible criticism is
welcome. Start by reading `docs/language.md`, then run:

```sh
python3 -m unittest discover -s tests -v
```

Useful first review requests:

1. Find a disagreement between documented operator/scoping rules and execution.
2. Challenge missing/null behavior and the all-or-nothing preview contract.
3. Find input that escapes the value/step limits or crashes outside a diagnostic.
4. Assess proposal identity: numeric normalization, rule identity and business keys.
5. Review the usability of one diagnostic with a beginner who did not write it.

For a bug report include the smallest .zs program, synthetic JSON, expected result,
actual result, Python version and operating system. Never include credentials or
private customer data. A good fix adds a regression test, updates the specification
if behavior intentionally changes, and runs the existing suite.

The tests are not an independent security audit. Please do not report the project
as production-ready merely because they pass. No stable compatibility promise is
made before 1.0.
The source is now licensed under MIT; public publication is still a separate step.

For the playground codec tests and production build:

```sh
cd playground
npm test
npm run build
```

Contributions should work across use cases. Add generic language/tooling capabilities
to the core; put stock, support and other domain policies in example programs or
future libraries. Do not hard-code customer names or business fields in the evaluator.

For proposed syntax or semantic changes, use [the language evolution checklist](docs/language-evolution.md).
For everyday development, use [the workflow guide](docs/developer-workflows.md).
Run editor client tests with `npm --prefix editors/vscode test`.
