# ZenSigil 0.6 language reference

ZenSigil is an experimental, deterministic language for readable rules. A program
consumes a JSON object and produces structured values, notes and proposed actions. It does not call
APIs, send messages, buy stock, or execute Python. The interpreter is written in
Python; ZenSigil programs use their own lexer, parser, and evaluator.

## First program

```text
rule "Restock review":
    for item in inventory:
        when item.days_of_stock < 14:
            propose reorder(sku: item.sku, target_days: 30)
```

The root keys of the input JSON are available as variables. Every indented block
uses exactly four additional spaces. Tabs are rejected in indentation. `#` starts
a comment outside a string. Expressions can span lines inside `()`, `[]`, or `{}`.

## Values and expressions

- Numbers: finite integers and decimals, including `1e3`. Arithmetic uses Python's
  double-precision floating-point behavior for decimals, not financial decimal
  arithmetic. Use integer cents for amounts; exact fixed-point money is future work.
  Magnitudes above `1e100` are rejected.
- Strings: double-quoted with JSON escapes, e.g. `"hello\nworld"`.
- Booleans: `true`, `false`; empty/missing value: explicit `null`.
- Lists: `[1, 2, 3]`; records: `{sku: "A17", stock: 15}`.
- Fields: `item.sku`; indexing: `items[0]`, `record["sku"]`. Indexes must be
  nonnegative integers within the list. Missing fields are errors, not null.
- Arithmetic: `+ - * / %`; string concatenation: `"Hi " + name`. No implicit
  conversion or string repetition. List + list concatenation is supported in 0.4. `/` divides; zero errors.
- Comparison: `== != < <= > >=`. Ordering requires two numbers or two strings.
  Equality is structural and type-aware: `true != 1`, `1 == 1.0`.
- Logic: `and`, `or`, `not` requires booleans. `and` and `or` short-circuit.
- Core precedence, low to high (see syntax-v04.md for the full 0.4 expression grammar): `or`, `and`, `not`, comparisons, `+ -`, `* / %`,
  unary `- +`, field/index/function call. Use parentheses to group expressions.
  Chained comparisons (`1 < x < 10`) are rejected; write `1 < x and x < 10`.

## Statements

```text
let threshold = 14
say "A note for the reviewer"
require threshold > 0, "Threshold must be positive."

when threshold < 20:
    say "Small threshold"
otherwise:
    say "Large threshold"

for value in [1, 2, 3]:
    say text(value)

fn double(value):
    return value * 2

rule "Example":
    propose review(sku: "A17", quantity: double(3))
```

`let` creates an immutable binding in its block. Duplicate declarations in one
block are errors. Child blocks may shadow outer variables. Each loop iteration
has a fresh scope; loop variables and inner bindings do not escape. In 0.4, var and set add explicit mutable bindings; let stays immutable. A program runs top to bottom; every rule runs once
in source order. `rule` supplies a label, not an event trigger or schedule.

`fn` and `rule` declarations are top-level only. Function names are known throughout
the program. Functions are pure: they can use parameters, local variables, other
functions and built-ins, but cannot capture inputs/top-level variables, write notes,
emit values, or propose actions. They may contain `let`, `var`, `set`, `when`,
`for`, `while`, `break`, `continue`, `require`, and `return`. Falling off
the end returns `null`. Recursive calls have a depth limit. Functions take positional
arguments; proposals take named fields. Reserved words, built-ins and function names
cannot be rebound. Input names must be valid nonreserved identifiers.

`require condition, message` enforces a program invariant. The condition must be a
boolean. If false, the message expression must produce a string, and execution fails
with `E_REQUIRE` at that statement. The entire preview is discarded. The message is
evaluated only on failure; bindings in it are still checked. `require` can appear in
functions and other blocks. In 0.2 it is a newly reserved word; rename 0.1 variables
or functions called `require` when upgrading.

`say` requires a string. `propose action(field: value, ...)` requires one or more
uniquely named fields and records JSON-compatible values. Action names are open:
`reorder`, `review_shipment`, or a domain of your own. This is a proposal envelope,
not a validated connector contract. Every proposal is marked `requires_review: true`.

## Built-ins

| Call | Meaning |
| --- | --- |
| `len(value)` | Length of a list, record, or string |
| `has(record, "field")` | Whether a record contains a key |
| `get(record, "field", fallback)` | Field or explicit fallback; present null stays null |
| `text(value)` | String, or compact JSON representation of another value |
| `ceil(number)`, `floor(number)`, `abs(number)` | Numeric operations |
| `min(a, b)`, `max(a, b)` | Minimum/maximum of two numbers |
| `round(number, places)` | Round for display; places is an integer from 0 to 10, ties to even |
| `fraction(number)` | Exact integer numerator/denominator record for its decimal spelling |
| `ceil_div(a, b)` | Exact integer ceiling of a / b; both operands must be integers and b nonzero |

`fraction(0.14)` returns `{numerator: 7, denominator: 50}`. It interprets the
decimal spelling of the supplied number, including a floating-point result if one
was computed earlier. It cannot recover precision already lost in an earlier
calculation. Its returned integers obey the usual magnitude limit; extremely tiny
rates may exceed the denominator limit. `ceil_div(7, 2)` returns `4`; negative
operands round toward positive infinity. These built-in names and `round` are reserved in 0.2. `round` uses the runtime's floating-point ties-to-even behavior; use exact ratio helpers for quantity decisions.

## Failure and preview contract

Parsing and binding checks cover untaken branches too. Types and fields are checked
when evaluated; the checker is not a full static type checker. `check` without data
allows unresolved names as possible input keys; supply `--data` to check root names.
Successful checking does not guarantee a successful run.

A runtime error discards all accumulated proposals and notes. The diagnostic includes
an error code, source line and column, and a plain-language message. Optional fields
must be handled explicitly with `has` or `get`, or represented as explicit null.

An optional **input contract** validates supplied JSON before interpretation. A
contract is a sidecar JSON object, not commerce-specific syntax. CLI commands accept
`--contract path.contract.json`; Python `check` and `run` accept `contract=...`.
The playground carries the contract alongside source and data. Contracts check
structure, types, required fields, ranges and unique record identifiers. Multiple
data issues are reported with paths such as `$.inventory[0].stock`. See
[the contract reference](contracts.md) for the supported subset and limits.

Contracts describe individual fields and records. Use `require` in the program for
relationships such as `policy.target_days >= policy.review_below_days`. Checking
with a contract validates supplied data; it still does not execute program assertions.

For readable previews, programs may include `explanation: "..."` and
`evidence: ["calculation step", "another step"]` in proposal fields. The playground
shows these as prose and calculation steps. They remain ordinary user-defined
fields: the evaluator does not inject explanations or give them special privileges.

Identical action name + fields + rule label share an ID, regardless of field order.
Duplicates within one successful preview are collapsed and reported. Source locations
are retained. Repeating a preview with the same input yields the same IDs. **This is
not persistent idempotency or exactly-once delivery:** no executor or order store exists.

The local runtime bounds source size, nesting, data size, executed steps, call depth,
and output size. These are guardrails for a prototype, not a multi-tenant sandbox.

## Future work

Module namespaces, user-defined static types, asynchronous work, real connectors,
scheduling, persistent approvals, persistent deduplication, financial decimal types,
package registry, production deployment and compatibility
guarantees are future work. Syntax may change before 1.0.

## Optional proposal contracts in 0.3

The core syntax is unchanged. A separate action-to-object-contract map can validate
proposal fields after evaluation. An undeclared action or invalid field discards
all output, with `E_PROPOSAL` and an output path. `check` only validates contract
definitions, never future proposals. See [proposal contracts](proposal-contracts.md).

## 0.4 expressive core

The complete additive grammar and changed AST shapes are documented in
[syntax-v04.md](syntax-v04.md). New constructs include var/set, while, break/continue,
runtime type annotations, named function values, choose expressions, ??, membership,
slices, emit and test blocks. Imported pure source is described in [modules.md](modules.md).
The [standard library](stdlib.md) adds bounded sequences, transformations, records,
text, JSON conversion and exact decimal-text arithmetic.

Successful previews now include a values array, populated by emit. Failures discard
values, notes and proposals together. Pure functions and tests cannot emit effects.
The test API and CLI execute only explicit test blocks; the main program is checked
but not executed. Checking alone does not perform runtime annotation checks.

New reserved words and standard names can conflict with earlier user bindings; see
[compatibility.md](compatibility.md). Old portable envelopes migrate with an empty
module map. The version marker does not mean older reserved-name assumptions are
retained: rename a conflicting user identifier when upgrading.

## 0.5 functions and collection types

[syntax-v05.md](syntax-v05.md) specifies anonymous fn expressions, immutable
lexical snapshots, nested list/record annotations and unions. Named top-level
functions keep their no-implicit-input rule; a lambda explicitly captures values
from its creation scope. The 0.5 additions extend the grammar above.
Runtime annotation checks are recursive but do not infer types statically.
See [developer-workflows.md](developer-workflows.md) for lint, project formatting,
stdin and selective tests, and [editor-v05.md](editor-v05.md) for editor support.

## 0.6 module boundaries

See [modules-v06.md](modules-v06.md) for `use ... as`, `export fn`, private helpers,
namespace values, source-local dependencies and imported test semantics.
