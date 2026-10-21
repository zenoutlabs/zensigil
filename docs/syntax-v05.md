# ZenSigil 0.5: closures and compositional annotations

This reference adds anonymous functions and nested runtime annotations to the
[0.4 grammar](syntax-v04.md). Existing statements and expression operators retain
their meanings. ZenSigil still executes its own AST, without host evaluation,
implicit I/O, or host-object imports.

## Anonymous function grammar

```text
let double = fn (n: number) -> number => n * 2
emit map([1, 2, 3], double)
emit filter([1, 2, 3], fn (n) => n > 1)
emit (fn (n) => n + 1)(5)
```

The additional expression form is:

```ebnf
lambda          = "fn", "(", [parameters], ")", ["->", annotation], "=>", expression ;
parameters      = parameter, {",", parameter}, [","] ;
parameter       = NAME, [":", annotation] ;
annotation      = type_atom, {"|", type_atom} ;
type_atom       = primitive_type | "list", "<", annotation, ">"
                  | "record", "<", annotation, ">" ;
primitive_type  = "any" | "number" | "integer" | "string" | "boolean"
                  | "list" | "record" | "null" | "function" ;
```

`fn` is an existing keyword. `=>` and `|` are new tokens; `|` belongs to
annotations and is not a bitwise or boolean expression operator. Identifier,
string, comment, indentation, and numeric spelling rules are unchanged. Generic
annotation delimiters can be adjacent to `=` or `=>`, as in
`let xs:list<integer>=[1]`. Outside annotations, `>=` remains comparison.

A lambda's body is **one expression** and extends as far to the right as an
ordinary full expression, stopping at its enclosing delimiter. For example,
`fn (x) => x + 1` returns `x + 1`. Parenthesize the lambda itself to call it
immediately or compare its value. A lambda can return another lambda. Existing
operator precedence applies inside its body. `=>` is not a binary operator and
cannot appear outside a lambda.

A lambda has only positional parameters. Annotations are optional. There are no
default arguments, variadic arguments, statement bodies, implicit return
statements, or anonymous function declarations. Named top-level functions retain
the existing `fn name(parameters):` block form.

## Lexical capture and timing

```text
var factor = 2
let scale = fn (n) => factor * n
set factor = 100
emit scale(3)  # 6: factor was captured when scale was created.

fn make_adder(base: number) -> function:
    return fn (value: number) -> number => base + value

let add_five = make_adder(5)
emit add_five(7)  # 12, after make_adder has returned.
```

Evaluating a lambda creates a distinct function value. It captures only the free
bindings referenced in its body, including bindings needed by nested lambdas.
A free binding is a name used without being declared as a parameter of that
lambda or a surrounding nested lambda. The nearest visible binding wins. Unused
variables are not captured. Named top-level functions and built-ins are resolved
as functions rather than captured data.

Captures are an **immutable snapshot of bindings at creation time**. A subsequent
`set` in the creating scope cannot change an existing closure. Lists and records
already have immutable value semantics: operators produce new collections, and
ZenSigil has no field/index mutation. The implementation can therefore retain
references to their existing values without copying them. A captured closure is
also a snapshot reference; changing the original variable to another function
does not change the captured function.

Parameters shadow captured or outer names. Each loop iteration still creates a
fresh scope. Returning a closure preserves the values it captured after the
creating call or block finishes. A nested closure captures an outer lambda's
parameters when the nested closure is evaluated, not when the outer lambda is
created.

A name must already be bound when a lambda is created. Closures do not obtain
forward-declared local variables or implicit self-recursion. Use a named function
for recursion, or pass a function explicitly as an argument. Function declarations
remain known throughout the program.

Root-level lambdas may capture supplied input values. Lambdas inside named
functions see that function's parameters and local variables. They do not grant
named functions implicit access to root inputs or root bindings. Test bodies
remain isolated from main-program inputs and bindings, but can create closures
from their own local variables.

Binding checking visits every lambda body, including unused functions and untaken
branches. Checking without input data can report free names in root expressions
as possible inputs. Checking with input data requires those names to exist.
Creating a lambda does not execute its body or check its eventual return value.

## Purity, identity, and call behavior

A lambda body cannot contain `set`, `say`, `emit`, `propose`, or other statements.
It can call existing pure named functions, including functions that use their own
local mutation. It cannot mutate a captured binding. There are no captured
mutable cells, ambient host capabilities, or externally visible effects.

Closures are accepted by the existing `function` annotation and higher-order
functions such as `map`, `filter`, `fold`, `any`, `all`, and `sort_by`.
Callback arity is validated even for empty collections. Arguments evaluate in
source order; callee evaluation occurs before its arguments.

Named function equality retains its existing name-based semantics. Closures use
identity equality: aliases of one closure are equal; two separately evaluated
lambda expressions are unequal even when their source and captured values match.
Ordering functions is invalid. `type_of` reports `"function"` for both forms.
Functions can be bound, passed, returned, and called, but cannot be placed in
lists or records, emitted, serialized as JSON, or converted to text. Collection
transformations must still produce JSON-compatible collection elements.

Call failures retain normal transactional rollback. Closure trace frames are
named `fn@<logical-source>:line:column`, identifying the lambda definition; the
frame's location fields identify the call site. The root source is `<program>`.
The original diagnostic location identifies the actual failing body expression.
Both named and anonymous calls share the existing 48-call depth limit.

## Nested and union annotations

```text
let rows: list<record<number | null>> = [{count: 3, estimate: null}]
var pending: list<string> | null = null
set pending = ["review", "publish"]

fn total(values: list<integer>) -> integer | null:
    return choose len(values) == 0 then null otherwise sum(values)

let first = fn (groups: record<list<string>>) -> string => groups.names[0]
```

`list<T>` checks every element against `T`. `record<T>` checks every string-keyed
field value against `T`; it describes homogeneous value types, not named fields
or required keys. Empty lists and records satisfy any matching container
annotation. Existing shallow `list` and `record` annotations continue accepting
any JSON-compatible contents.

`T | U` accepts a value matching either alternative, evaluated left to right with
short-circuiting. `null` is the nullable alternative: `list<number> | null` accepts
a list of numbers or null; `list<number | null>` accepts a list whose elements may
be numbers or null. Generic brackets delimit their inner union, so these forms
are unambiguous. Parenthesized types and `T?` shorthand are not supported.

All existing primitive distinctions remain: `boolean` excludes numbers;
`integer` accepts integer values but excludes `1.0`; `number` accepts either
numeric representation. `any` accepts any language value, including a standalone
function value. Annotations perform no coercion.

Annotations check binding initialization, every `set` of an annotated variable,
function arguments, and function results. Both named functions and closures use
the same rules. A mismatch reports `E_TYPE` and prints the full annotation in
source-like form. These are **runtime checks**, not static inference, named type
aliases, generic functions, structural record schemas, or an effect type system.
Untaken code does not undergo value checks. Input and proposal contracts remain
the mechanism for required fields and validation before/after execution.

## Bounds and work accounting

Every annotation match operation consumes execution steps, including container
elements and attempted union alternatives. An annotation can nest at most 16
generic levels, contain at most 64 primitive/container names, and have at most
eight alternatives in any one union. These syntax limits prevent unchecked
recursive annotation complexity; runtime work is separately bounded.

Closure free-name discovery and capture traversal consume execution steps.
Across one runtime (or one test suite), creating closures and capturing their
values is limited cumulatively to 20,000 counted nodes and 1 MiB of text/scalar
content. Each closure and captured binding name counts; JSON collection keys and
elements are traversed. A reference to an already-created closure is counted
once rather than recursively re-counting its previously charged environment.
Repeated captures of the same JSON value are conservatively charged again.
These counters do not reset when a closure becomes unreachable. This intentionally
bounds long chains and repeated allocation; it is not a garbage-collected heap
quota. The existing per-value, source, step, output, and call limits also apply.
Exceeding a closure or work budget reports `E_LIMIT` and discards all output.

## AST compatibility

The new `lambda` node contains
`(parameter_tokens, body_expression, parameter_annotations, return_annotation)`.
Named `fn` node fields keep their 0.4 order. Annotation primitives remain strings;
container annotations are `("list", T)` or `("record", T)`; unions are
`("union", (T, U, ...))`. The public AST serializer represents these tuples as
JSON arrays. Tools must recurse through annotation arrays rather than assuming
every non-null annotation is a string. The formatter validates the resulting AST
and preserves the new syntax and literal spelling.

Behavioral regression evidence lives in `tests/test_core_v05.py`.
