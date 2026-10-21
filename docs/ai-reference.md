# Give this file to an AI writing ZenSigil

You are writing **ZenSigil 0.6**, an experimental language. Use only the syntax
specified here and in `docs/language.md`. Do not invent import forms, connectors,
language keywords, or purchasing commands.

Programs consume a JSON object: root keys become variables. They return JSON values with emit, proposed actions and notes. All proposals require review and no external action executes.
Use four spaces per block. Strings are double-quoted with JSON escapes. Comments
start with `#`. Lists `[1, 2]`, records `{key: "value"}`, numbers, `true`, `false`,
and `null` are supported. Fields use `item.sku`; lists use zero-based indexes.

Statements:

```text
let name = expression
say "message"
require boolean_expression, "A useful failure message"
when boolean_expression:
    statement
otherwise:
    statement
for name in list_expression:
    statement
fn function_name(parameter):
    return expression
rule "Label":
    statement
propose action_name(field: expression)
```

`fn` and `rule` are top-level only. Functions may use parameters, locals, other
functions and built-ins, but cannot capture input/global variables, say, emit or propose.
`let` is immutable and block-scoped. Use explicit `var`/`set` for local state,
`while`/`break`/`continue` for bounded loops, and `use "lib/math.zs"` for pure modules.
See syntax-v04.md for annotations, choose/then/otherwise, ??, membership and slices.

Operators: arithmetic `+ - * / %`, comparison `== != < <= > >=`, boolean
`and or not`. Strict types: conditions are booleans, arithmetic is numeric,
and `+` also joins two strings or two lists. No chained comparisons; use `and`.

Original built-ins (see stdlib.md for all 49): `len(x)`, `text(x)`, `has(record, "key")`,
`get(record, "key", fallback)`, `ceil(x)`, `floor(x)`, `abs(x)`, `min(a, b)`,
`max(a, b)`, `fraction(number)`, `ceil_div(integer, integer)`, `round(number, places)`. Function arguments are positional; proposal fields are named.
`get` does not replace a present null. Missing direct field access fails.

Workflow when asked to write a rule:

1. Establish the input fields and expected output with a small synthetic fixture.
2. Write the .zs code and matching JSON.
3. Add a generic sidecar input contract when data needs validation. Run
   `python3 -m zensigil check program.zs --data input.json --contract input.contract.json`.
   Omit --contract when no contract is supplied.
4. Add an optional action-to-fields proposal contract when output needs validation. Run
   `python3 -m zensigil run program.zs --data input.json --contract input.contract.json --proposal-contract proposal.contract.json --json`.
   Omit either contract flag only when that contract is not supplied.
5. Compare actual proposals with expected values and test a boundary/missing field.
6. Do not claim a successful preview placed orders or delivered an action.

Example with optional data:

```text
rule "Stock review":
    for item in inventory:
        let daily = get(item, "daily_sales", null)
        when daily == null:
            say "Missing sales for " + item.sku
        otherwise:
            when daily > 0 and item.stock / daily < 14:
                propose reorder(sku: item.sku, quantity: ceil(daily * 30 - item.stock))
```

Input:

```json
{"inventory": [{"sku": "A17", "stock": 15, "daily_sales": 4}]}
```

Expected: one reorder proposal for A17, quantity 105. Decimal arithmetic is floating
point; use integer cents in simple financial examples. Real financial policy and
connector validation are outside this prototype.

Use `explanation` string and `evidence` list-of-strings fields for readable proposals.
They are ordinary fields, not privileged runtime features. For fractional rates and
whole-day stock decisions, follow `examples/stock-review.zs`: use exact fractions
and integer ceiling division. Do not rely on ceil of a floating-point product for
quantity correctness. `require` failure discards the entire preview. The portable
`.sigil.json` format carries raw source, input text and optional input and proposal contract text; it is
separate from the .zs language grammar.

Proposal contracts map each allowed action to an object contract. They validate the
whole preview after execution; `check` checks their definitions only. Keep intended
expected results separate from program-generated explanations. Exported `.sigil.json`
programs can run or check directly through the CLI. Version 0.4 bundles may also carry a modules source map.

For 0.4 programs, read syntax-v04.md and stdlib.md. Use emit for structured results,
explicit var/set for local state, and optional runtime annotations. Named function
references can be passed to map/filter/fold; they do not capture local bindings.
Use pure .zs modules supplied explicitly through modules= or CLI project roots.
Write test blocks with require expectations, run them, and compare emitted values
against independent expected results. Ordinary decimals remain floating point;
exact decimal helpers accept and return decimal strings.

For 0.5, use `fn (x: number) -> number => expression` for anonymous pure functions.
Closures snapshot visible bindings; later set operations do not alter captures.
`list<integer>`, `record<list<number>>` and `integer | null` are recursive runtime
annotations, not inferred types. Read syntax-v05.md for all interactions and limits.
Use group_by/count_by/partition/flat_map when the transformation calls for them.
For API and CLI adoption, use developer-workflows.md.

## 0.6 additions

Use `use "lib/math.zs" as math` and `math.double(2)` for namespaced calls.
Use `export fn` for public functions; unmarked helpers become private once any
function is exported. Each module must import its own dependencies. Namespace
handles are not JSON records. New standard functions: scan, min_by, max_by, sum_by,
unique_by, frequencies, flatten, record_from_entries. Consult stdlib.md for exact
arity, empty-input and tie behavior. Do not invent I/O, classes, async or packages.
