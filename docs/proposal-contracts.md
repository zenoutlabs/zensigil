# Proposal contracts

A proposal contract describes the actions a program may suggest and the fields each
suggestion needs. This makes programs easier to share: a misspelled action or a
quantity with the wrong type becomes an explained failure. It does not connect to
another service or execute the suggestion.

This optional feature was added in ZenSigil 0.3. Existing programs can keep running
without one. The language syntax is unchanged.

## A small example

Program:

```text
propose reserve_seats(count: 2, explanation: "Two seats remain.")
```

Save this alongside it as `seats.proposal.json`:

```json
{
  "reserve_seats": {
    "type": "object",
    "required": ["count", "explanation"],
    "additionalProperties": false,
    "properties": {
      "count": {"type": "integer", "minimum": 1},
      "explanation": {"type": "string", "minLength": 1}
    }
  }
}
```

Every key is an allowed action name. Every value is an ordinary
[ZenSigil contract](contracts.md) describing the proposal's `fields` object. The
root of each action contract must explicitly declare `"type": "object"` (or
`["object"]`). Names must be identifiers such as `reserve_seats`, without spaces,
hyphens, or reserved language words. Nested field contracts support the same
subset as input contracts, including required fields, ranges, enums and lists.
There is no automatic conversion: `true` is not `1`, and `"2"` is not `2`.

A supplied mapping is a closed allowed-action list: any undeclared action fails.
An empty mapping `{}` permits no proposals, though a program may still produce
notes. Omitting the contract disables proposal validation. Object fields remain
open by default; choose `"additionalProperties": false` when extra fields should
be rejected. `explanation` and `evidence` remain ordinary fields you can require
or leave optional.

## Running and checking

```sh
python3 -m zensigil run seats.zs --proposal-contract seats.proposal.json --json
python3 -m zensigil check seats.zs --proposal-contract seats.proposal.json
```

The Python API accepts an optional keyword on both functions:

```python
from zensigil import run, check

result = run(source, data, contract=input_contract,
             proposal_contract=action_contracts)
checked = check(source, data, proposal_contract=action_contracts)
```

`run` validates **all contract definitions before execution**, including unused
actions and unused property branches. After execution it validates every emitted,
deduplicated proposal. If any proposal fails, **all proposals and all notes are
discarded**. Successful proposal fields, IDs, source locations and deduplication
stay unchanged. No external action is executed in either case.

`check` validates contract definitions and program bindings, but does not execute
the program or verify its output. Its response explicitly reports
`proposal_contract_checked` and `proposals_checked: false`. A successful check
can still fail when run, for example because it emits an undeclared action.
Use known inputs and inspect successful runs before sharing a program.

## Errors and limits

Malformed definitions use `E_PROPOSAL_CONTRACT` and a definition `output_path`
such as `$.reserve_seats.properties.count.type`. Output failures use `E_PROPOSAL`
and paths such as `$.proposals[0].fields.count` or `$.proposals[0].action`. Output
errors include the action and the source line/column of the `propose` statement.
Definition errors use line 1/column 1 with an empty source line, because they are
in sidecar data. These paths refer to JSON structures, not source files.

At most 50 proposal diagnostics are returned across all actions or proposals.
The whole mapping is limited to 256 KiB of ASCII-escaped JSON serialization,
10,000 JSON entries and 33 nesting levels. Each individual action schema also
obeys the existing contract limits (256 KiB, 10,000 entries, 32 nesting levels).
Only finite JSON values are accepted. There is no full JSON Schema support.

## Playground HTTP interface

`POST /api/run` and `POST /api/check` accept either `proposal_contract` as a JSON
object or `proposal_contract_text` as a JSON string, never both. Omit both when
disabled; explicit `null` is invalid. Text must be valid JSON without duplicate
keys or nonfinite numbers, and at most 256 KiB before parsing. Contract errors
return HTTP 200 with `ok: false`, diagnostics, and empty notes/proposals, just as
input contract failures do. Invalid request envelopes still return HTTP 400.

`GET /api/examples` includes `proposal_contract` from each example's optional
`.proposal.json` sidecar, or `null` when absent. The loopback server also offers
`GET /api/health`, returning only `{"status":"ok","version":"0.3.0"}`; the
same local Host restriction applies. This endpoint confirms the process version,
not whether a particular program has passed validation.
