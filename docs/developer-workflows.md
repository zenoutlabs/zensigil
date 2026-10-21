# ZenSigil 0.6 developer workflows

Install the release wheel or use `python3 -m zensigil` from this source checkout.
The runtime is standard-library-only. The VS Code extension requires an installed
0.6 runtime because its subprocess runs in isolated Python mode.

```sh
zensigil init my-project
zensigil run my-project --json
zensigil test my-project --list
zensigil test my-project --filter Double --fail-if-empty --json
zensigil lint my-project
zensigil fmt my-project --check
```

`test --filter TEXT` selects case-sensitive substrings of test names. Declarations
and all source still pass binding/structure checks; excluded test bodies do not
execute. `--list` discovers selected names without running assertions, returning
zero steps and zero passed/failed tests. Listed cases have `ok: null`. By default
an empty suite succeeds; `--fail-if-empty` makes an empty selection fail with
E_TEST_EMPTY. The Python `test()` API accepts `name_filter=` and `list_only=`.

`lint` performs ordinary checks first, then reports conservative advisory warnings:
W_UNUSED for bindings never read (underscore-prefixed names opt out), W_SHADOW for
inner bindings hiding outer ones, and W_UNREACHABLE after unconditional control
transfer. Lambda reads count as uses of captured names. It does not prove program
correctness or perform whole-program type/control-flow inference. `--strict`
returns exit 1 on warnings. `--json` exposes structured diagnostics and warnings.
Projects lint their entry, listed test files and explicit imports, deduplicating
shared module warnings. Invalid source remains an error regardless of strict mode.

`fmt PROJECT --check` reports explicitly referenced files needing formatting.
`--write` formats those files after every source has parsed and formatted successfully.
It touches entry, declared tests and reachable imports, never unrelated `.zs` files.
Symlinks are rejected for project formatting. Changes are checked before writes;
replacement is atomic per file. A disk failure during replacement may leave a
partially formatted project; this is not a cross-file transaction. Formatting limits
projects to 256 explicit files. Existing uncommitted edits are the input, not discarded.

```sh
printf 'emit 6 * 7\n' | zensigil run - --json
printf 'emit   1+2\n' | zensigil fmt -
```

`run`, `check`, `test`, `lint`, `fmt` and `ast` accept `-` as UTF-8 source from stdin,
up to 64 KiB. Input data and contracts still use explicit file flags. Stdin imports
are only loaded when `--module-root DIR` is supplied. In-place formatting of stdin
is rejected. Output files never replace known source/input/contract/module files;
failed project discovery conservatively protects existing files inside that project.

`zensigil lsp` starts the standard editor protocol over stdin/stdout. See
[editor-v05.md](editor-v05.md). The library API, CLI, playground and editor share the
parser and checker; editor checking never executes programs.

## Interactive sessions and CI reports

Run `zensigil repl` to enter expressions or multiline declarations. Launch with
`--data input.json --modules modules.json` for explicit fixed session inputs.
See [REPL commands and bounds](repl.md). Run `zensigil test project --junit report.xml`
to write a new XML report; existing files are protected. See [test reports](test-reports.md).
