# Share a project with its tests

ZenSigil 0.8 includes project tests in portable `.sigil.json` files.
The file contains the program, input, contracts, modules, and declared test files.
It works after you move the original project folder.

```sh
python -m zensigil pack my-project --name "My project" --output my-project.sigil.json
python -m zensigil run my-project.sigil.json --json
python -m zensigil test my-project.sigil.json --fail-if-empty --json
python -m zensigil test my-project.sigil.json --filter "Expected" --list --json
python -m zensigil test my-project.sigil.json --junit results.xml
python -m zensigil unpack my-project.sigil.json --output reopened-project
python -m zensigil run reopened-project --json
python -m zensigil test reopened-project --fail-if-empty --json
```

`unpack` creates `zensigil.json`. The manifest selects the entry file, tests,
input, and contracts. `example` also creates a project manifest.
The output folder must not exist. An existing folder is never replaced.
An input or test file cannot be the output of `pack`, even with `--force`.

## Test behavior

The test command checks all source files before it runs tests.
It then runs each test once. The test identity is its source path and name.
Two tests can have the same name when they are in different files.
A shared module test runs once, even when several test files import that module.
In 0.7, the project command could run that module test more than once.
Counts can decrease in 0.8 because that duplicate work is removed.

Each test file keeps its own function scope.
The main program does not run during tests. Test execution produces no proposals,
notes, or emitted values. `run` and `check` do not execute separate test files.
`lint` checks the entry file and the separate test files.

Project and portable test commands share one limit of 100,000 execution steps.
Execution stops when that limit is reached. The result includes `E_LIMIT`.
A test list uses no execution steps. It still checks syntax and bindings.
The bundle permits at most 10,000 selected tests.
Test results also share a 1 MiB compact JSON limit. This includes source paths,
failure messages, and call traces. An excess result ends with `E_TEST_LIMIT` and
sets `stopped_early` to `true`. No oversized result is reported as a pass.
The JSON result and JUnit report retain each test's source path.
Project paths are relative to the module root. This keeps test identities stable
when a project is moved, packed, or extracted.

## Portable format

The portable format version stays `1`. New files use language version `0.8.0`.
Files from versions 0.2 through 0.7 still open. They get an empty `tests` map.
Unknown fields are errors. This prevents silent loss of unsupported information.

The optional `entry_path` field records the entry file's root-relative `.zs` path.
Packing records this path. Older files without it use the `<program>` identity.
Source filenames that cannot be imported, such as names with spaces, also keep
the `<program>` identity. Their source text still packs and runs.
This explicit identity prevents duplicate tests when another file imports the
entry module. Identical text in two different files does not merge their tests.
If the entry path also occurs in a source map, the source text must match exactly.

The optional `tests` field is an object. Its keys are root-relative `.zs` paths.
Its values are raw source text. For example:

```json
{"tests": {"tests/math.zs": "test \"Two plus two\":\n    require 2 + 2 == 4, \"Expected four.\"\n"}}
```

Both `tests` and `modules` permit 32 files each.
Each file can contain at most 64 KiB of UTF-8 source.
Each map can contain at most 256 KiB of UTF-8 source in total.
The final JSON file must be at most 10 MiB, including escaped characters.

Paths cannot escape the project. Paths must not conflict when letter case is
ignored. A path cannot be both a file and a directory.
The same exact path can occur in both maps only when its source text is identical.
Test files can import only modules in the `modules` map. Packing a project adds
imports used only by its test files to that map.

Packing preserves unfinished source and raw input text. A file with import
declarations must have valid syntax so that its dependencies can be found.
Packing does not mean the program or tests passed. Run the checks shown above.

## Extraction limits

Extraction preserves `entry_path` when it is supplied.
Without it, extraction chooses a different entry filename if needed.
It also avoids input filename conflicts. The manifest records the chosen names.
A bundled directory named `zensigil.json` cannot be extracted because this name
is required for the project manifest. This error occurs before output is created.

If a write fails, extraction removes the files it created when possible.
It does not remove unrelated files. A disk failure can prevent cleanup.
This is not a filesystem transaction.

Blank embedded contract text means no contract. Extraction preserves that text
without enabling it as a required contract file.
These rules preserve the behavior of the portable program after extraction.

## Verification

`tests/test_portable_v08.py` covers the format, limits, source identities,
shared execution limit, failed extraction cleanup, and project round trips.
`tools/verify_install.py` checks installed project packing and reopening.
`tools/verify_adoption.py` tests the quickstart from an isolated installation.
It moves the original project, then runs and tests the shared file and reopened folder.
