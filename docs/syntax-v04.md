# ZenSigil 0.4 syntax and semantics

This reference supplements the core language reference. The parser still uses its
own tokens and AST, four-space indentation, JSON strings and explicit statements.
No language construct evaluates host code. The [statement EBNF and expression
parsing algorithm](grammar.ebnf) specify the grammar alongside this reference.

## Bindings and controlled state

```text
let greeting: string = "Hello"
var total: integer = 0
for item in [1, 2, 3]:
    set total = total + item
emit total
```

`let`, function parameters, input keys and loop variables are immutable bindings.
`var` permits rebinding with `set name = expression`. Assignment targets a name,
never a field or index. `set` finds the nearest lexical binding and rejects it if
immutable, even if an outer binding with that name is mutable. Child blocks may
shadow outer names. Each loop iteration has a fresh child scope. Local mutation
inside a function is pure: it cannot reach input keys or outer bindings.

Optional annotations are `any`, `number`, `integer`, `string`, `boolean`, `list`,
`record`, `null`, and `function`. `integer` excludes decimal literals such as `1.0`
and booleans; `number` accepts integers and floating-point numbers. Collections
are shallow annotations, not generics. Annotations check binding initialization,
assignment, function arguments and return values at execution. They do not claim
static inference or validate untaken values. The binding checker still checks
names, structure and purity in every branch.

## Functions and expressions

```text
fn apply(operation: function, value: number) -> number:
    return operation(value)

fn double(value: number) -> number:
    return value * 2

let twice = double
emit apply(twice, 6)
emit choose true then "yes" otherwise "no"
emit null ?? "fallback"
```

Named user functions and built-ins evaluate to opaque function references. Aliases,
higher-order arguments, returned function references, and calls on a callee
expression are supported. Functions remain top-level declarations and capture
neither inputs nor top-level bindings. There are no closures or anonymous functions.
Direct calls have checked arity; aliased and computed calls check arity at execution.
Falling off a function returns `null`, which must satisfy any return annotation.
A runtime failure carries source call frames in innermost-to-outermost order.

Function references cannot occur inside lists or records, be emitted, be converted
to text, or cross other JSON boundaries. Standalone local function bindings and
function arguments/results are allowed. Equality of two references to the same
named function is true; function ordering is invalid.

`choose condition then yes otherwise no` requires a boolean and evaluates only the
selected branch. Its branches are full expressions; parenthesize the whole choice
to apply an operator to its result. `a ?? b` evaluates `b` only when `a` is exactly
`null`. It preserves `false`, `0` and empty strings. Missing record fields still
raise `E_FIELD`; use `get(record, "key", null)` for optional keys. Both choice
branches and both coalescing operands are checked for valid bindings.

Precedence, lowest first: `choose` (prefix with full expression branches), `??`,
`or`, `and`, `not`, comparisons and membership, `+ -`, `* / %`, unary `+ -`, then
field access/indexing/slicing/calls. Binary operators, including `??`, associate
left to right; lazy evaluation is preserved. Chained comparisons or membership
expressions are rejected; combine separate comparisons with `and`.

## Collections and strings

```text
emit [1, 2] + [3]
emit {id: 1} in [{id: 1.0}]
emit "id" in {id: null}
emit "word" not in "other text"
emit "a🦊b"[1]
emit [1, 2, 3][1:99]
```

`+` concatenates two lists or two strings. No implicit conversion occurs.
Membership `in` and `not in` uses strict structural equality for list elements
(`1 == 1.0`, `true != 1`), string keys for records, and substrings for strings.
The left operand of record/string membership must be a string. Equality work is
charged to the execution budget.

List and string indices require a nonnegative integer within bounds. Strings are
indexed by Unicode code point, not byte or visible grapheme. Slices support
`[start:stop]`, `[:stop]`, `[start:]`, and `[:]`; omitted bounds mean beginning/end.
Explicit bounds are nonnegative integers, stop is exclusive, and oversized bounds
clamp to the sequence length. Reversed bounds return an empty sequence. Slice
steps, negative indices and record slices are rejected.

## Loops and outputs

```text
var remaining = 3
while remaining > 0:
    set remaining = remaining - 1
    when remaining == 1:
        continue
    emit remaining
    when remaining == 0:
        break
```

`while` requires a boolean condition each iteration. `break` exits the nearest
loop; `continue` starts its next iteration. Both require a lexical loop in the
same function. A function cannot break a caller's loop. All loop conditions,
bodies, calls and emitted values obey existing execution and value limits.

`emit expression` adds a JSON value to the ordered `values` result array. Its
entries share the 1,000-entry and 1 MiB output budget with notes and proposals.
Any failure discards every value, note and proposal. `emit`, `say` and `propose`
are effects and cannot appear in pure functions or test bodies.

## Tests and modules

```text
use "math_helpers.zs"

test "Double a number":
    require double(3) == 6, "Expected six."
```

`test "label":` is top-level, labels must be unique, and bodies are isolated pure
blocks. They can use functions and their own bindings but cannot capture input or
program bindings. Tests can use local mutation, loops and `require`; `return`
requires a function. Ordinary runs skip test bodies. The test command executes
them independently with a shared suite execution budget and reports each result.
A test that exhausts the budget terminates the suite. Check still validates every
test body, so malformed tests fail checking even when normal execution skips them.

`use "path.zs"` parses as a top-level import declaration. Imports must be resolved
by the project loader before binding checks. Unresolved or nested imports fail
with `E_IMPORT`; they are never silently ignored. See the module guide for path
and library restrictions.

## AST contract for tools

All nodes are immutable `Node(kind, token, parts)` records. Token fields are
`kind`, `value`, `line`, `column`, and optional logical `source_name`.

| Node kind | Parts |
| --- | --- |
| `let`, `var`, `set` | `(name_token, expression, annotation_or_none)`; set annotation is none |
| `fn` | `(name_token, parameter_tokens, body, parameter_annotations, return_annotation)` |
| `call` | `(callee_expression, argument_expressions)` |
| `choose` | `(condition, yes_expression, no_expression)` |
| `slice` | `(sequence_expression, start_or_none, stop_or_none)` |
| `while` | `(condition, body)` |
| `break`, `continue` | `()` |
| `emit` | `(expression,)` |
| `test` | `(label_string, body)` |
| `use` | `(path_string,)` |

Binary membership/coalescing reuse `binary(operator, left, right)` parts. Existing
function AST tools can keep reading the first three function parts; calls now
store a callee node rather than a name string. New syntax words and standard
library names are reserved; consult the migration guide before upgrading.
