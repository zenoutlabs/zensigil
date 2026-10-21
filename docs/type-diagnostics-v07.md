# Type advice

`zensigil lint` can find some type errors before you run a program. These checks
produce `W_TYPE` warnings. They do not change `check` or `run`.

```text
let count: integer = "three"
emit count
```

The binding cannot pass its integer annotation. Lint reports a warning at line 1.
`check` still accepts the syntax and names. `run` still reports `E_TYPE`.
Use `lint --strict` if you want warnings to fail a check in your build process.

## What the checks can find

- A known value that cannot pass a binding, assignment, parameter, or result annotation.
- An invalid element in a list or record literal, including nested annotations and unions.
- A known non-boolean condition or logical operand.
- Incompatible arithmetic, ordering, or membership operand types.
- A known value that cannot be called, indexed, sliced, or read as a record.
- A wrong argument count through an immutable alias of a known function.
- A known invalid note, failure message, or loop sequence.

The original core functions (`len`, `has`, `get`, `text`, `ceil`, `floor`,
`abs`, `min`, `max`, `fraction`, `ceil_div`, and `round`) and `type_of` have
advisory signatures. Other built-ins keep unknown result types in this pass.

The analysis reads function bodies and both branches of a condition. A warning
can describe code that will not run for the current input. For example, the
failure message in `require true, 12` is never evaluated at runtime, but lint
can still warn that its type is invalid for a failure message.
The same rule applies to short-circuit expressions such as `true or 12`.

The source name, line, and column identify each warning. Imported functions use
their own module scope. Functions with the same private name in two modules do
not share a signature. Named imports keep their public function signatures.

## What the checks do not prove

This is advisory analysis, not a full static type system. No warnings does not
mean that a program will run successfully. The pass does not execute source,
resolve input values, infer callback results, or evaluate numeric expressions.
It does not prove array bounds, record fields, termination, or numeric ranges.
It does not infer the result of a function that has no result annotation.

Unknown values do not produce type warnings. Immutable bindings retain known
types. An unannotated mutable binding remains unknown, because a branch or loop
can change it. An annotated mutable binding retains only its enforced type.
A union produces a warning only if none of its possible types can work.
An empty container can pass any element annotation for that container type.

The pass stops after 100,000 analysis visits, 128 nested analysis calls, or 200
type warnings. A `W_TYPE_LIMIT` warning states that analysis is incomplete.
These limits do not change the separate execution budget.

Regression cases are in `tests/test_type_lint_v07.py`.
