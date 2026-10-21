# Run a useful program

This guide is for developers who want a small working example.
It uses Python 3.9 or later. No AI account or API key is needed.
Use the source folder for this release, or clone the public source:

```sh
git clone https://github.com/zenoutlabs/zensigil.git
cd zensigil
```

## Install in a new environment

On macOS or Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m zensigil doctor --json
```

On Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install .
.venv\Scripts\python.exe -m zensigil doctor --json
```

`doctor` must report `"ok": true`.
If Python cannot create an environment, install the Python venv support for your system.
Source installation can download build tools. The runtime has no package dependencies.
To install a downloaded wheel without network access, use:

```sh
python -m pip install --no-index --no-deps path/to/zensigil-VERSION-py3-none-any.whl
```

Use the Python command from your new environment in place of `python` below.
There is no need to activate the environment or change a shell policy.
Do not install a package from the public package index by name yet.
This release does not claim a package-index publication.

## Create a project

```sh
python -m zensigil init latency-review
python -m zensigil run latency-review --json
python -m zensigil test latency-review --fail-if-empty --json
```

The first run returns `answer: 42`. Both tests must pass.
The new folder includes its own README and a small public library.
`init` does not replace an existing folder.

## Summarize measurements

Use the six files below in `latency-review`.
These sample measurements are in milliseconds.
They are synthetic data.

`zensigil.json` selects the program, tests, and input files:

<!-- file:zensigil.json -->
```json
{
  "format": "zensigil-project",
  "format_version": 1,
  "language_version": "0.7.0",
  "entry": "main.zs",
  "tests": ["tests.zs"],
  "data": "input.json",
  "contract": "input.contract.json"
}
```

`input.json` contains the measurements:

<!-- file:input.json -->
```json
{"samples_ms": [120, 80, 100]}
```

`input.contract.json` rejects empty input and invalid measurements:

<!-- file:input.contract.json -->
```json
{
  "type": "object",
  "properties": {
    "samples_ms": {
      "type": "array",
      "minItems": 1,
      "maxItems": 400,
      "items": {"type": "integer", "minimum": 0, "maximum": 60000}
    }
  },
  "required": ["samples_ms"],
  "additionalProperties": false
}
```

`lib/statistics.zs` defines a public function:

<!-- file:lib/statistics.zs -->
```text
export fn summarize(samples: list < integer >) -> record:
    require len(samples) > 0, "Provide at least one measurement."
    let total = sum(samples)
    return {count: len(samples), total_ms: total, average_ms: total / len(samples)}
```

`main.zs` uses the function:

<!-- file:main.zs -->
```text
use "lib/statistics.zs" as statistics

emit statistics.summarize(samples_ms)
```

`tests.zs` checks known results:

<!-- file:tests.zs -->
```text
use "lib/statistics.zs" as statistics

test "Summarize three measurements":
    let result = statistics.summarize([120, 80, 100])
    require result == {count: 3, total_ms: 300, average_ms: 100}, "Expected the known summary."

test "One zero measurement":
    require statistics.summarize([0]).average_ms == 0, "The average must be zero."
```

Run the checks from the parent folder:

```sh
python -m zensigil check latency-review --json
python -m zensigil run latency-review --json
python -m zensigil test latency-review --fail-if-empty --json
python -m zensigil lint latency-review --strict
python -m zensigil fmt latency-review --check
```

If the format check reports a change, run `python -m zensigil fmt latency-review --write`.
Then run the format check again. This also converts Windows line endings to the
formatter's LF line endings. It does not change the program result.

The run result must have `ok: true` and this `values` list:

```json
[{"count": 3, "total_ms": 300, "average_ms": 100}]
```

Both tests must pass. These tests check the function with their own data.
They do not run the main program or read the input values inside a test.

Change `input.json` to `{"samples_ms": [20, 40]}`.
The next run must return `count: 2`, `total_ms: 60`, and `average_ms: 30`.
Change one measurement to `-1`.
The run must fail with an input error and an empty `values` list.
Restore the original input before the next step.

## Share the program

```sh
python -m zensigil pack latency-review --name "Latency review" --output latency-review.sigil.json
python -m zensigil run latency-review.sigil.json --json
```

The portable file contains the entry source, its imported modules, input, and contracts.
It runs without the project folder. It does not include separate test files.
Share the source folder when another developer also needs the test suite.

Project paths start at the project root. They use `/` on all systems.
The optional `data`, `contract`, and `proposal_contract` paths must end in `.json`.
They cannot leave the root. The matching command flag overrides each default file.
An invalid or empty override fails; it does not fall back to the default.
Use `--proposal-contract` as the command flag for `proposal_contract`.
The `pack` command preserves unfinished text. Run `check` and `run` to validate it.

The [CLI reference](cli.md) lists the other commands.
The [language reference](language.md) describes the rules and limits.
The interpreter is experimental. Use the results as data to review.
