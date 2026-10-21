# Input contracts

An input contract describes the data a ZenSigil program expects. It checks the
whole input before the program starts and explains what needs fixing. It can be
used for inventory, support tickets, classroom examples, or any other JSON data.
Contracts are optional and separate from the language's syntax.

A typical project has three files:

- `review.zs`: the instructions.
- `review.json`: the input data.
- `review.contract.json`: the data's expected shape and permitted values.

The names are a convention. The CLI uses a contract only when `--contract` is
provided. The playground includes a contract with examples that provide one.

## A small example

Given this input:

```json
{"tickets": [{"id": "T-101", "priority": "urgent", "age_hours": 5}]}
```

This contract requires a unique ticket ID, a recognized priority, and a
nonnegative number of hours:

```json
{
  "title": "Support queue input",
  "type": "object",
  "required": ["tickets"],
  "additionalProperties": false,
  "properties": {
    "tickets": {
      "type": "array",
      "uniqueBy": "id",
      "items": {
        "type": "object",
        "required": ["id", "priority", "age_hours"],
        "additionalProperties": false,
        "properties": {
          "id": {"type": "string", "minLength": 1},
          "priority": {"type": "string", "enum": ["normal", "urgent"]},
          "age_hours": {"type": "number", "minimum": 0}
        }
      }
    }
  }
}
```

A negative age produces an `E_INPUT_DATA` diagnostic at
`$.tickets[0].age_hours`, mentioning ticket ID `T-101`. Missing fields, invalid
types, and duplicates are reported together, up to 50 diagnostics. No notes or
proposals are returned when validation fails. Fix the reported values and run
again to reveal any errors beyond that limit.

## Run with a contract

```sh
python3 -m zensigil check review.zs --data review.json --contract review.contract.json
python3 -m zensigil run review.zs --data review.json --contract review.contract.json --json
```

The Python API accepts a decoded contract dictionary:

```python
from zensigil import check, run

result = run(source, data, contract=contract)
checked = check(source, data, contract=contract)
```

`check` with a contract but without data checks the contract and the program;
it cannot verify input values until data is supplied. `run` without data uses
an empty object. Omitting `contract`, or passing Python `None`, preserves the
original behavior. Neither contracts nor inputs are modified.

## Supported contract format

This is a deliberately small, schema-shaped ZenSigil format. **It is not full
JSON Schema.** Unknown keywords are errors, including `$schema`, `$ref`,
`format`, `pattern`, `default`, `oneOf`, and `uniqueItems`. Do not pass a full
JSON Schema document and expect unsupported parts to be ignored.

Every contract is an object. An empty object `{}` adds no constraints.

| Keyword | Meaning |
| --- | --- |
| `type` | One supported type, or a nonempty list of distinct supported types. |
| `properties` | Map of object field names to contracts. Fields are optional unless required. |
| `required` | List of distinct required object field names. |
| `additionalProperties` | Boolean; `false` rejects fields absent from `properties`. Defaults to `true`. |
| `items` | One contract applied to every array item. |
| `minItems`, `maxItems` | Inclusive array length bounds; nonnegative integers. |
| `minLength`, `maxLength` | Inclusive string length bounds; nonnegative integers counting Unicode code points. |
| `minimum`, `maximum` | Inclusive numeric bounds. |
| `enum` | Nonempty list of permitted JSON values, compared structurally. |
| `title`, `description` | Text documentation; no effect on validation. |
| `uniqueBy` | ZenSigil extension: array records must have distinct values for this named field. |

Supported types are `object`, `array`, `string`, `number`, `integer`, `boolean`,
and `null`. `number` accepts integer and decimal JSON values. `integer` accepts
integer JSON values such as `3`; `3.0` is a decimal and is rejected. Booleans do
not count as numbers. Strings such as `"3"` are never converted to numbers.

`{"type": ["number", "null"], "minimum": 0}` accepts a nonnegative number or
explicit `null`. A missing field is different from `null`: `required` governs
presence and `type` governs the supplied value.

If `type` is omitted, each constraint applies only to values of its appropriate
type. For example, `minimum` alone does not require a number. Include `type`
when you want to require a particular kind of value. If `type` is supplied,
keywords must have a compatible type: `{"type":"string","minimum":0}` is a
malformed contract. All property and item contracts are checked even when the
input does not use them. Minimum bounds must not exceed maximum bounds.

`uniqueBy` names one direct field, such as `"sku"` or `"id"`; it is not a path.
Every item must be an object with a non-null string, number, or boolean for that
field. Numeric `1` and `1.0` are equal for uniqueness and enums; `true` and `1`
are different. Duplicate messages identify the first matching record's path.
Use a string type and `minLength: 1` on IDs to disallow empty IDs.

For relationships between fields, use program conditions and `require`.
Contracts describe individual fields and records; they do not calculate business
rules or choose actions.

## Diagnostics and limits

Malformed contracts use `E_CONTRACT`. Input values that violate a valid contract
use `E_INPUT_DATA`. Their diagnostic objects contain `data_path`, `message`,
`line: 1`, `column: 1`, and `source_line: ""`. These paths describe input data
(or, for `E_CONTRACT`, locations in the contract), rather than `.zs` source lines.
Unusual field names use bracket notation, such as `$["part.number"]`.
Object-level checks include the record's `sku` or `id` when available; nested
field errors retain that context.

Contracts are limited to 256 KiB of JSON, 10,000 nodes including keys and values,
and 32 levels of nesting. The same 256 KiB cap applies to encoded contract text
and the parsed contract's JSON representation. Validation returns at most 50
diagnostics. Input data keeps the language's existing JSON size, depth, and
numeric limits. Duplicate JSON keys and non-finite JSON constants remain errors
at the file and HTTP boundary.

## Local HTTP API

`POST /api/run` and `POST /api/check` accept either `contract` (an object) or
`contract_text` (JSON text), alongside `source` and either `data` or `data_text`.
Providing both contract fields is an error. Omit both to skip validation. An
explicit JSON `null` contract is rejected; use `{}` for an unconstrained contract.

Well-formed requests return HTTP 200 with `ok: false` and diagnostics for invalid
contract text, malformed contracts, or invalid input values. Malformed JSON
request envelopes, duplicate envelope/data keys, and invalid data envelopes
retain HTTP 400. All validation failures have empty `proposals` and `notes`.

`GET /api/examples` includes a `contract` object from each example's adjacent
`.contract.json` file when present; otherwise it returns `contract: null`.
