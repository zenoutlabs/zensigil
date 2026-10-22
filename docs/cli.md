# Command-line guide

The command line runs the same ZenSigil interpreter as the playground. It works
with local files and never sends proposals to an external service. Python 3.9 or
newer is required. The runtime needs no third-party Python libraries.

From the project directory, use `python3 -m zensigil`. After installing the project
with `python3 -m pip install .`, you can also use `zensigil`.

## Start with a working example

```sh
python3 -m zensigil doctor
python3 -m zensigil examples
python3 -m zensigil example stock-review --output my-stock-review
python3 -m zensigil run my-stock-review/program.zs \
  --data my-stock-review/input.json \
  --contract my-stock-review/input.contract.json
```

`examples` lists the examples bundled with your installation. Add `--json` for an
array of names. `example NAME --output DIRECTORY` creates a new directory with
`program.zs`, `input.json`, and any available `input.contract.json` and
`proposal.contract.json`. It rejects an existing directory and unknown names;
example names cannot refer to arbitrary paths. Some examples intentionally show
language errors, so a successful copy does not promise a successful preview.

`doctor` checks the installed version, a basic interpreter run, the built
playground page, and bundled source/input example pairs. `doctor --json` includes
`ok`, `version`, `python`, individual `checks`, and `example_count`. It is a basic
installation check, not a full test suite.

## Check and preview

```sh
python3 -m zensigil check program.zs --data input.json --contract input.contract.json
python3 -m zensigil run program.zs --data input.json --json
python3 -m zensigil run program.zs --data input.json \
  --proposal-contract proposal.contract.json --output preview.json
```

`check` parses and checks bindings, validates supplied input, and checks supplied
contract definitions. It does not execute `require` statements or generate
proposals. Checking a plain `.zs` file without `--data` leaves possible input names
unverified and says so. `run` uses `{}` when a plain source file has no input.

`--contract` accepts the input contract described in [contracts.md](contracts.md).
`--proposal-contract` accepts a direct action-to-schema mapping, for example:

```json
{"review": {"type": "object", "required": ["reason"], "properties": {"reason": {"type": "string"}}}}
```

Every action schema must declare `type: "object"`. Actions absent from the mapping
are rejected; an empty `{}` mapping permits no proposals. Omit the option for
unrestricted action names. The interpreter validates proposal fields against
their action's contract before returning a successful preview. A proposal validation error discards every proposal and note in that run.

`--json` prints the complete result to standard output. Without it, previews show
notes and proposals, and diagnostics go to standard error. Diagnostics include
source locations and, when relevant, data paths. Commands exit **0 on success**
and **1 on an error**, including malformed command options.

For `run`, `--output FILE` writes the complete result as JSON, including a failed
run's diagnostics and empty proposal/note lists. It also prints the normal result
(or JSON with `--json`). The destination must be a new file unless `--force` is
supplied. A failed output write makes the command fail with `E_OUTPUT`; existing
files are not changed without `--force`. Even with `--force`, the destination
cannot be any input file. `--force` requires `--output`. Parent directories must
already exist. This is a saved preview, not execution or approval history.

## Share a program in one file

A `.sigil.json` portable program carries the source, input, and optional contracts.
The playground can import and export this same format.

```sh
python3 -m zensigil pack program.zs --data input.json \
  --contract input.contract.json --proposal-contract proposal.contract.json \
  --name "My review program" --output my-review.sigil.json
python3 -m zensigil check my-review.sigil.json
python3 -m zensigil run my-review.sigil.json --json
python3 -m zensigil unpack my-review.sigil.json --output reopened-program
```

`pack` requires `--name` and `--output`. It defaults input text to `{}` and contract
text to empty when those files are omitted. It does **not** validate or run source,
input JSON, or contracts: unfinished drafts can be saved without losing text.
Use `check` and `run` to validate before sharing a working example. The output is
created exclusively; `--force` allows replacement, but never of an input file.

`unpack` creates a **new** directory containing `program.zs` and `input.json`.
It writes `input.contract.json` and `proposal.contract.json` only when their raw
text is nonempty. All extracted text is preserved exactly, including invalid JSON,
spacing, and line endings. The name stays in the portable document; it is not
added to the extracted source. There is no `--force` for unpack or example creation.

Portable documents are detected by the `.sigil.json` filename suffix. Other input
filenames are read as plain source. For portable `check` and `run`, the embedded
input is supplied, so input names are checked. Explicit `--data`, `--contract`,
and `--proposal-contract` replace the corresponding embedded texts independently.
This also lets an override repair invalid embedded JSON. An explicit empty
contract file is invalid JSON; use `{}` as an unconstrained input contract.
Whitespace-only embedded contract text means no contract.

## Portable format 1

```json
{
  "format": "zensigil-program",
  "format_version": 1,
  "language_version": "0.6.0",
  "name": "Hello",
  "source": "say text(name)\n",
  "data_text": "{\"name\":\"Nikko\"}",
  "contract_text": "",
  "proposal_contract_text": "",
  "modules": {}
}
```

Format 1 accepts language versions `0.2.0` through `0.6.0`. Reading normalizes the
in-memory version to `0.6.0`; it does not rewrite the original file or source.
New packages use `0.6.0`. For older documents, `proposal_contract_text` defaults
to empty and `modules` defaults to an empty object. Other fields are required. Unknown
fields, duplicate JSON keys, format versions other than the JSON number 1, and unsupported language versions
are rejected. No metadata is silently dropped.

Names must be nonblank and at most 80 UTF-16 code units (the same limit as the
browser). Source is limited to 64 KiB of UTF-8 text, input to 1 MiB, and each
contract to 256 KiB. The encoded document has a 10 MiB limit, allowing JSON escapes
within the individual text limits. Source and data have the interpreter's usual
additional validation and resource limits when checked or run.

Envelope errors use `E_PROGRAM`. Invalid input JSON uses `E_INPUT`; malformed
input and proposal contracts use `E_CONTRACT` and `E_PROPOSAL_CONTRACT`.
Contract validation may produce more specific field diagnostics. Duplicate keys
are rejected in embedded input and contracts too; they are never silently replaced.

To open the local editor, use `python3 -m zensigil serve --port 8766`, then visit
`http://127.0.0.1:8766/`. To inspect the runtime version, use
`python3 -m zensigil --version`.

## Interactive exploration and JUnit

`zensigil repl [--data input.json] [--modules modules.json]` starts an interactive
session with explicit input objects and source modules. Use `:help` for commands.
`zensigil test project --junit results.xml` writes CI-compatible test results to
a new file. `--list` cannot be combined with `--junit`. Full details: [REPL](repl.md)
and [test reports](test-reports.md).

## Version 0.7 project inputs and warnings

`run`, `check`, `test`, and `lint` read the project's optional input and contract paths.
Explicit flags take precedence. `pack` also accepts a project directory and uses its settings.
Existing input files, including declared defaults, cannot be used as forced output paths.

`lint` can produce `W_TYPE` advice. Use `--strict` to treat warnings as a failed check.
The pass does not execute source or prove correctness. The playground's **Find warnings**
button uses the same advice. See [type diagnostics](type-diagnostics-v07.md).

## Version 0.8 shared tests

`pack PROJECT` includes separate test files and modules used only by tests.
`test FILE.sigil.json` supports filtering, listing, and JUnit reports.
`unpack` restores a project manifest with input, contracts, and test entries.
Shared module tests run once. All roots share a work limit and a test-result size
limit. A result limit reports `E_TEST_LIMIT` and `stopped_early: true`. Reported
counts describe retained results, not a complete run of every selected test.
See [the portable test reference](portable-tests-v08.md) for examples and limits.
