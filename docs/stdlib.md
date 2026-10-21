# Standard library

ZenSigil's standard functions transform values and return new values. They do not change their arguments or access files, networks, clocks, or host-language code. The language keeps its existing `len`, `has`, `get`, `text`, arithmetic, `fraction`, `ceil_div`, and display `round` functions.

Version 0.6 adds eight functions, bringing the total to **69**: `scan`, `min_by`,
`max_by`, `sum_by`, `unique_by`, `frequencies`, `flatten` and
`record_from_entries`. These names are reserved like other built-ins.

Version 0.5 added twelve functions, bringing that version's total to 61. Their names are
reserved like other built-ins; rename earlier bindings that conflict with
`group_by`, `count_by`, `partition`, `flat_map`, `find`, `find_index`, `take`,
`drop`, `chunk`, `record_pick`, `record_omit`, or `clamp`.

## Lists and sequences

| Function | Meaning | Example result |
| --- | --- | --- |
| `range(stop)` | Integers from zero, excluding stop | `range(3)` → `[0, 1, 2]` |
| `range(start, stop)` | Integers starting at start, excluding stop | `range(2, 4)` → `[2, 3]` |
| `range(start, stop, step)` | Positive or negative integer step | `range(5, 0, -2)` → `[5, 3, 1]` |
| `enumerate(items)` | Zero-based index/value records | `enumerate(["a"])` → `[{index: 0, value: "a"}]` |
| `zip(left, right)` | Pairs, stopping at the shorter list | `zip([1, 2], ["a"])` → `[[1, "a"]]` |
| `sum(numbers)` | Sum in list order; empty sum is zero | `sum([2, 3])` → `5` |
| `sorted(items)` | Ascending numeric or Unicode string ordering | `sorted([3, 1])` → `[1, 3]` |
| `reverse(value)` | Reverse a list or string | `reverse("abc")` → `"cba"` |
| `unique(items)` | First occurrence of each structurally equal value | `unique([1, 1.0, true])` → `[1, true]` |
| `contains(container, value)` | List equality, record key, or string substring | `contains([true], 1)` → `false` |
| `take(items, count)` | New list containing at most the first count items | `take([1, 2, 3], 2)` → `[1, 2]` |
| `drop(items, count)` | New list after skipping the first count items | `drop([1, 2, 3], 2)` → `[3]` |
| `chunk(items, size)` | Consecutive lists of at most size items | `chunk([1, 2, 3], 2)` → `[[1, 2], [3]]` |
| `flatten(lists)` | Concatenate lists, removing exactly one outer level | `flatten([[1], [], [[2]]])` → `[1, [2]]` |
| `frequencies(strings)` | Count string occurrences, preserving first-key order | `frequencies(["b", "a", "b"])` → `{b: 2, a: 1}` |

`range` requires integers and a nonzero step. Its size is calculated before allocation and cannot exceed 10,000 items. A step facing away from the stop produces an empty list. Record/list/string results also obey the ordinary value limits, so `enumerate` can reach the value-node limit before the list-item limit.

`sorted` requires all numbers or all strings, including singleton lists; booleans are not numbers. Strings use Unicode code-point order, not a locale's dictionary order. `reverse` reverses Unicode code points, not visual grapheme clusters; a combining accent may move separately from its letter.

`unique` and list `contains` use language equality: `1` equals `1.0`, but `true` differs from `1`. Records compare by fields and nested values. The equality work consumes execution steps; a large list of distinct complex records can reach the step limit. String and record membership require a string search argument.

`take`, `drop`, and `chunk` accept lists only. Counts must be integers, excluding
booleans and floating-point values such as `2.0`. `take` and `drop` accept zero;
`chunk` requires a positive size, including for an empty list. Negative counts
fail. A count larger than the list length makes `take` return the whole list,
`drop` return `[]`, and `chunk` return one list containing all items (or `[]` if
the input is empty). These calls preserve order, retain mixed JSON values, and do
not modify the original list. Chunking adds a nesting level and container nodes,
which count toward the result limits.

`flatten` requires a list whose every item is itself a list. It does not split
strings or recursively flatten nested values. Empty input returns `[]` and empty
inner lists contribute no values. The combined list length is checked before
each extension. `frequencies` accepts only strings, without converting numeric
or boolean values to keys; empty input returns `{}`. Empty strings, Unicode text
and `"__proto__"` are ordinary keys. Both helpers preserve their inputs.

## Records

| Function | Meaning |
| --- | --- |
| `record_keys(record)` | List of keys in record insertion order |
| `record_values(record)` | Corresponding list of values |
| `record_entries(record)` | List of `{key: ..., value: ...}` records |
| `record_merge(left, right)` | New shallow record; right-hand fields replace matching left-hand fields |
| `record_pick(record, keys)` | New shallow record retaining fields named in the keys list |
| `record_omit(record, keys)` | New shallow record excluding fields named in the keys list |
| `record_from_entries(entries)` | Build a record from exact `[string_key, value]` pairs, rejecting duplicate keys |

These names have a `record_` prefix to keep common program bindings such as `values` available. Merging does not recursively combine nested records.

For `record_pick` and `record_omit`, keys must be a list of strings. All keys are
checked even when the record is empty. Missing keys and duplicate requests are
ignored; output fields retain their **original record order**, not the order of
the keys list. For example, `record_pick({z: 1, a: 2}, ["a", "z"])` retains
the key order `["z", "a"]`. An empty keys list returns `{}` for `record_pick`
and a shallow copy for `record_omit`. Nested values are preserved unchanged.

`record_from_entries` requires a list of lists, each containing exactly two
items: a string key followed by a JSON value. Duplicate keys fail with
`E_DUPLICATE`, even if their values agree; there is no silent overwrite. Field
order follows the input pairs, and an empty list produces `{}`. For example,
`record_from_entries([["b", false], ["a", 0]])` returns `{b: false, a: 0}`.
The older `record_entries` intentionally returns `{key, value}` records, so
convert those explicitly with `map(record_entries(record), fn (entry) =>
[entry.key, entry.value])` before passing them to `record_from_entries`.

## Functions over collections

Pass a function as a value. Callback functions retain the language's purity and execution limits.

```zensigil
fn double(x):
    return x * 2

fn positive(x):
    return x > 0

fn add(total, item):
    return total + item

say json_text(map([1, 2, 3], double))
say json_text(filter([-1, 0, 2], positive))
say text(fold([1, 2, 3], 0, add))
```

| Function | Callback | Result |
| --- | --- | --- |
| `map(items, transform)` | One item → new value | List in original order |
| `filter(items, predicate)` | One item → boolean | Original items whose predicate is true |
| `fold(items, initial, combine)` | Accumulator and item → new accumulator | Final accumulator; initial value for an empty list |
| `any(items, predicate)` | One item → boolean | True at first match; false for an empty list |
| `all(items, predicate)` | One item → boolean | False at first failure; true for an empty list |
| `sort_by(items, key)` | One item → number or string | Stable ascending order by key |
| `group_by(items, key)` | One item → string | Record of item lists grouped by key |
| `count_by(items, key)` | One item → string | Record of integer counts by key |
| `partition(items, predicate)` | One item → boolean | `{matched: [...], unmatched: [...]}` |
| `flat_map(items, transform)` | One item → list | Concatenation of returned lists, flattening exactly one level |
| `find(items, predicate, fallback)` | One item → boolean | First matching original item, or explicit fallback |
| `find_index(items, predicate)` | One item → boolean | First matching zero-based index, or `-1` |
| `scan(items, initial, combine)` | Accumulator and item → next JSON accumulator | List of successive results, excluding the initial value |
| `min_by(items, key)` | One item → number or string | Original item with the smallest key; first tie; `null` for empty input |
| `max_by(items, key)` | One item → number or string | Original item with the largest key; first tie; `null` for empty input |
| `sum_by(items, transform)` | One item → number | Numeric sum in input order; zero for empty input |
| `unique_by(items, key)` | One item → JSON value | First original item for each structurally equal key |

`filter`, `any`, `all`, `partition`, `find`, and `find_index` require actual boolean predicate results, without truthiness conversions. In particular, returning `0`, `1`, `null`, or an empty string from a predicate fails. `any`, `all`, `find`, and `find_index` short-circuit: later items may not be evaluated. `sort_by` calls its key function once per item and requires homogeneous numeric or string keys. Equal keys preserve original order. Every collection call checks that its callback is a function with the required arity, even if the list is empty. Function values cannot be serialized into JSON or stored inside JSON lists/records.

`group_by` and `count_by` call the key function once per input item, in input
order. Keys must be strings; numbers and booleans are not converted implicitly.
Empty strings, Unicode strings, and names such as `"__proto__"` are ordinary
record keys. Group fields appear in order of first occurrence, and grouped items
retain input order. Both return `{}` for an empty list. For example:

```zensigil
fn category(item):
    return item.category

let items = [{category: "b", n: 1}, {category: "a", n: 2}, {category: "b", n: 3}]
emit count_by(items, category)  # {b: 2, a: 1}
emit group_by([false, 0, true], type_of)
# {boolean: [false, true], number: [0]}
```

`partition` evaluates the predicate once per item and preserves order within
both lists. Its empty result is `{matched: [], unmatched: []}`. `flat_map`
also calls its function once per item; each return value must be a list. It
flattens only that list's outer level: flattening `[[], [1], [[2]]]` with an
identity function produces `[1, [2]]`. An empty input or exclusively empty
callback lists produces `[]`.

`find` returns the original matching item, including an explicit `null` or
`false` if the predicate selects it. Its fallback must be a JSON value and is
validated even when an item matches. As with other function arguments, the
fallback expression is evaluated **before** `find` begins; it is not a lazy
expression. An expensive or fallible fallback can instead be selected with a
`choose` expression around a `find_index` result. `find_index` returns `-1`
for an empty list or no match, and index `0` is a valid match.

`scan` calls its two-argument callback once per item, passing the previous
accumulator and current item. `scan([1, 2, 3], 10, fn (total, x) => total + x)`
returns `[11, 13, 16]`, with no extra element for `10`. Empty input returns `[]`.
The initial value must be JSON-compatible even when the input is empty; its
validation consumes steps. Every returned accumulator must also be JSON-compatible.
Collection accumulators remain immutable values: later iterations cannot change
earlier results. Retaining all intermediate results can reach the output node or
text limit sooner than a single `fold` result.

`min_by` and `max_by` evaluate their callback once for every item, including
items after a current best result. All keys must be numbers or all must be
strings; numeric keys may mix integers and floats, while booleans are rejected.
Strings use Unicode code-point order. Equal keys keep the first original item.
For empty input the result is `null`; a selected original item can itself be
`null` too. `sum_by` requires actual numeric callback results, excludes booleans
and strings, and checks the running sum against normal finite-number bounds.
Floating-point addition follows input order; exact decimal text remains separate.

`unique_by` accepts any JSON-compatible callback key, including nested lists and
records. It uses the language's structural equality: `1` and `1.0` share a key,
but `true` and `1` do not. Record field order does not affect equality. It keeps
the first item for each key and preserves input order, with no hash ordering or
implicit string conversion. Each key function is evaluated once per item.
Distinct retained keys share an additional bounded value budget: their combined
list representation must fit 20,000 nodes, 32 nesting levels and 1 MiB of text.
Comparisons consume steps, so a large set of distinct keys can reach the work
limit before the value limit. Function values cannot be keys.

All five new callback-based functions validate callback type and arity even on
empty input. Named functions, anonymous closures and namespace-qualified function
values use the ordinary callback interface and retain its purity restrictions.

The 0.5 and 0.6 collection builders charge execution steps for copied JSON nodes,
record/key scans, and callback traversal in addition to the callback's own
steps. They check growing output sizes before adding each result piece. Lists
and records remain limited to 10,000 items or fields; any complete result is
limited to 20,000 JSON nodes, 32 levels of nesting, and 1 MiB of total UTF-8
string/key content. Individual strings remain limited to 65,536 characters.
Repeated references count every time they would appear in JSON. For example,
`chunk(range(10000), 1)` exceeds the node limit because each small list adds a
container node. `flat_map` checks the combined list length before extending it;
flattening several valid lists cannot bypass the result limits. Any failure
discards the entire preview, including outputs created earlier in the program.

`type_of(value)` returns `"null"`, `"boolean"`, `"number"`, `"string"`, `"list"`, `"record"`, or `"function"`. Integers and floating-point numbers share the `"number"` result.

## Numeric bounds

`clamp(number, low, high)` returns `low` when the number is below it, `high`
when the number is above it, and the original number otherwise. The bounds are
inclusive and may be equal. All three arguments must be finite language numbers;
booleans and strings fail. A lower bound greater than the upper bound fails
instead of swapping them. Integer and floating-point arguments can be mixed;
the returned argument retains its numeric representation. For example,
`clamp(-3, 0, 10)` returns `0`, while `clamp(0.5, 0, 1)` returns `0.5`.

## Strings

| Function | Meaning |
| --- | --- |
| `lower(text)` / `upper(text)` | Unicode lowercase/uppercase conversion |
| `trim(text)` | Remove leading and trailing Unicode whitespace |
| `split(text, separator)` | Split on a literal nonempty separator; retain empty pieces |
| `join(strings, separator)` | Join a list of strings, without converting other types |
| `replace(text, old, new)` | Replace all nonoverlapping occurrences of nonempty old text |
| `starts_with(text, prefix)` | Boolean prefix check |
| `ends_with(text, suffix)` | Boolean suffix check |

Empty prefix/suffix checks return true. Splitting an empty string returns `[""]`; joining an empty list returns `""`. Split output cannot exceed 10,000 items; strings cannot exceed 65,536 characters. Join and replacement calculate result size before building an oversized result. Unicode case conversion can change string length, and its output is validated against the ordinary string limit.

## Explicit number and JSON conversion

`parse_number(text)` accepts a complete JSON-style number, such as `"-12.5e1"`. It rejects whitespace, leading `+`, leading zeros, partial parses, NaN, infinity, non-string arguments, and results outside the language's finite number bounds. Its input is limited to 256 characters. An integer spelling produces an integer; a decimal point or exponent produces ordinary floating-point arithmetic.

`parse_json(text)` parses JSON with duplicate fields and nonfinite numbers rejected. The resulting value must satisfy the language's nesting, node, collection, string, and numeric limits. JSON syntax failures produce an ordinary structured language diagnostic and discard the preview output.

`json_text(value)` serializes JSON values with sorted record keys, compact separators, and Unicode characters preserved. It produces a string subject to the normal string limit. These functions provide data conversion; they do not read or write files.

## Exact decimal text

The `dec` family performs decimal arithmetic on **strings**. It adds no new native numeric type or implicit conversions. Keep inputs as strings from the start when exact decimal arithmetic matters:

```zensigil
let subtotal = dec_add("0.1", "0.2")
let total = dec_mul(subtotal, "3")
say total  # "0.9"
```

| Function | Result |
| --- | --- |
| `dec(text)` | Canonical decimal string |
| `dec_add(a, b)` | Exact decimal sum as text |
| `dec_sub(a, b)` | Exact decimal difference as text |
| `dec_mul(a, b)` | Exact decimal product as text |
| `dec_div(a, b, places)` | Quotient rounded to the requested number of places |
| `dec_round(a, places)` | Decimal rounded to the requested number of places |
| `dec_compare(a, b)` | `-1`, `0`, or `1` |

Accepted decimal text follows `-?(0|[1-9][0-9]*)(\.[0-9]+)?`: no exponents, surrounding whitespace, leading plus, or unnecessary leading integer zeros. Inputs and canonical outputs contain at most 100 digits and magnitude at most `1e100`. Exceeding these limits raises a diagnostic. Canonical output removes trailing fractional zeros, removes a trailing decimal point, and turns negative zero into `"0"`; fixed-width monetary formatting is a separate concern.

`places` is an integer from 0 through 18. Division and rounding use **round half to even**: `dec_div("1", "8", 2)` returns `"0.12"`, while `dec_div("3", "8", 2)` returns `"0.38"`. Division by zero fails. Intermediate arithmetic uses an isolated 240-digit decimal context, so it does not change the host's global context. Addition, subtraction, and multiplication fit exactly within that precision for accepted inputs; division explicitly rounds to the selected scale.

Converting an already calculated floating-point value to text cannot repair earlier binary rounding. `dec_add("0.1", "0.2")` is the exact route; `text(0.1 + 0.2)` retains ordinary floating-point behavior.
