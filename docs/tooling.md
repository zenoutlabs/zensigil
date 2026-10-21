# ZenSigil 0.6 tooling

The interpreter and command-line tools require Python 3.9 or newer and use the
standard library. Examples below assume the `zensigil` command is installed;
`python3 -m zensigil` is equivalent from the source release.

## Format source

```sh
zensigil fmt main.zs
zensigil fmt main.zs --check
zensigil fmt main.zs --write
```

The default prints formatted source without changing the file. `--check` prints
nothing and exits 0 when the file is already formatted; it exits 1 and explains
when a change is needed. `--write` explicitly replaces that file atomically and
retains its permission bits. Symbolic links are rejected for in-place writes.
These modes are mutually exclusive. Source files must have the `.zs` extension;
standard input and explicit project formatting are described below.

The formatter normalizes operator, comma and colon spacing and uses four spaces
for expression continuations. It preserves comments, blank lines inside the
program, and the original spelling of strings and numeric literals. It removes
trailing whitespace and extra blank lines at the end, and ends nonempty programs
with a newline. Valid block indentation already uses four spaces in ZenSigil.
Comment-only indentation is retained. It does not reorder declarations, change
quotes, split long expressions, or try to repair invalid programs.

Both original and formatted source must parse. Their position-free syntax trees
must match before a result is returned. Formatting an already formatted result
has no further effect. A syntax error leaves the file untouched. Extremely deep
syntax trees can exceed the formatter's recursion guard and are rejected.

```sh
zensigil fmt my-project --check
zensigil fmt my-project --write
```

Project formatting requires `--check` or `--write`. It reads only the manifest's
entry, listed test sources and their explicitly reachable imports, with at most
256 distinct source files. Unlisted source files are untouched. Symbolic links
in source paths beneath the project root are rejected. Every source is parsed and formatted
before any writes, so a syntax failure leaves the project unchanged. Changed
files are rechecked against their original text before replacement. Replacement
is atomic per file; a disk failure during the write phase can still leave a
partly formatted project. `--check` lists files that need formatting and exits 1
if any differ; `--write` lists replaced files and reports the source count.

## Inspect the syntax tree

```sh
zensigil ast main.zs --json
```

This emits a JSON document with `format: "zensigil-ast"`, `format_version: 1`,
and `body`. Statements and expressions have `kind`, `line`, `column`, and `parts`;
identifier tokens have `kind`, `value`, `line`, and `column`. Coordinates start
at 1. Tuple-shaped grammar data becomes JSON arrays. This is a syntactic tree,
not inferred types or executable bytecode. No code runs, and `use` declarations
are shown without reading their module files. JSON is also the default without
`--json`. Invalid source returns a diagnostic result and exit status 1.

## Start a project

```sh
zensigil init my-project
zensigil check my-project --json
zensigil run my-project --json
zensigil test my-project --json
```

`init` creates a new directory containing `main.zs`, `lib/math.zs`, `tests.zs`, and
this manifest:

```json
{
  "format": "zensigil-project",
  "format_version": 1,
  "language_version": "0.6.0",
  "entry": "main.zs",
  "tests": ["tests.zs"]
}
```

Existing destinations are rejected. The parent directory must already exist.
Manifest text is limited to 16 KiB; unknown keys, unsupported versions, absolute
paths, parent traversal, backslashes, non-`.zs` paths, and paths escaping through
symbolic links are rejected. `tests` is optional and accepts up to 32 distinct
relative source paths. There is no automatic dependency installation or directory
scan. Paths use `/` on every operating system.
Version 0.6 also accepts existing project manifests marked `0.4.0` or `0.5.0`; current
reserved names and language behavior apply to their source.

`run` and `check` select `entry`. `test` checks the entry and listed test sources
as separate suites, then aggregates their explicit test blocks. Ordinary top-level
statements are checked but not executed by `test`. Tests can call pure module
functions; each test gets a fresh local scope. Use `--data` to validate fixture input bindings. When no fixture is supplied,
ordinary top-level input names remain unverified, while isolated tests can only
use their own locals and pure functions. Each source suite has a bounded
execution budget; the aggregate command can use one budget per listed source.
A failed assertion or invalid source produces exit status 1. JSON includes
`tests`, `total`, `passed`, `failed`, `stats`, and `diagnostics`. Test case source
files identify their suite; diagnostic module filenames identify imported code.

## Select and list tests

```sh
zensigil test my-project --filter "Double" --json
zensigil test my-project --list --json
zensigil test my-project --filter "Double" --fail-if-empty
```

`--filter` selects test names containing the supplied case-sensitive text. It
does not execute excluded tests, but all source still undergoes syntax and
binding checks. `--list` performs those checks and reports selected test names
without executing their bodies. Its JSON marks `listed: true`, gives each case
`ok: null`, and reports zero passed/failed tests and execution steps. The `total`
is the number listed. `--fail-if-empty` returns `E_TEST_EMPTY` and exit status 1
when no tests are selected; otherwise an empty selection is successful. These
options also work with individual source files and portable programs.

The Python `test()` API accepts `name_filter=` and `list_only=` for selection and
listing. Listed cases likewise have `ok: None` and do not count as passed. The
empty-selection exit policy is a CLI option.

## Advisory lint checks

```sh
zensigil lint main.zs --json
zensigil lint my-project --strict
```

Lint first performs the ordinary syntax, import and binding checks. On valid
source it reports `W_UNUSED` for bindings never read, `W_SHADOW` for local
bindings hiding outer bindings, and `W_UNREACHABLE` after unconditional control
transfer, including a branch whose two alternatives both transfer control.
Closure references count as reads of captured bindings. Prefixing a binding
with `_` suppresses unused/shadow warnings for intentional placeholders.

Warnings are advisory and do not normally change the exit status. `--strict`
returns status 1 when warnings are present. Project lint covers the entry,
listed test sources and explicitly imported modules, deduplicating repeated
module warnings. It never executes code. Its lexical analysis does not infer
types, evaluate constant conditions, prove termination, detect every unused
function, or establish that the program is correct.

## Standard input

Use `-` as the source for `run`, `check`, `test`, `lint`, `fmt` or `ast`:

```sh
printf 'emit 6 * 7\n' | zensigil run - --json
printf 'emit  1+2\n' | zensigil fmt -
```

Standard input is UTF-8 source limited to 64 KiB. `fmt - --write` is rejected.
Imports supplied through stdin do not read the working directory implicitly;
provide `--module-root PATH` explicitly to resolve them. Without that root,
stdin containing imports cannot replace an existing output inside the working
directory with `--force`. This protection does not discover or read module files.

## Modules and portable programs

```sh
zensigil run src/main.zs --module-root . --json
zensigil pack main.zs --name "My project" --output my-project.sigil.json
zensigil run my-project.sigil.json --json
```

Module `use` paths always start at the selected root, including imports made by
other modules. The default root is a source file's directory or a project's
manifest directory. `--module-root` explicitly selects another root containing
the entry source. The API itself only accepts supplied module source maps and
never reads host files. CLI module reads are bounded to the root and explicit
import graph; see the language reference for limits and module purity rules.

`pack` embeds the explicit import graph as a `modules` source map, so the portable
program can run after its original source files are removed. It also accepts
`--module-root`. Plain unfinished drafts without imports remain packable. A draft
with `use` declarations must parse to discover its imports; imported files must
exist and pass the module loading bounds. Packing preserves raw source, input,
and contract text; it does not promise that execution will succeed.

Output protection covers source, input and contract files, loaded modules, and
project manifests and test paths. `--force` permits replacing a separate output;
it does not permit replacing one of those inputs.
If a project manifest cannot be loaded, replacing existing output within that
unresolved project is rejected rather than risking its source or manifest.

## Visual Studio Code

Install the matching release's VSIX using **Extensions: Install from VSIX** and
install the same ZenSigil wheel into the Python environment selected by
`zensigil.pythonPath`. `editors/vscode` contains the extension source, syntax
grammar, snippets and language-server client; its README covers rebuilding.
The 0.4 artifact and its verification remain documented in that release's evidence.

Version 0.5 uses `zensigil lsp`, a bounded stdin/stdout service, for syntax/import/
binding diagnostics, completion, hover, definitions, symbols and formatting.
The same service is available to other editors. Unsaved module buffers override
disk modules within declared workspace roots. Checks do not run source or
pretend to validate absent input data. The VS Code client requires workspace
trust and starts isolated Python without a shell.

See [the editor protocol reference](editor-v05.md) for supported operations,
source boundaries, limits and the real-host validation recipe. Automated
protocol/provider tests and actual VS Code host validation are distinct; consult
the release evidence for the recorded outcome. Rename, references, semantic
tokens, signature-help popups, incremental document edits and dynamic workspace
changes remain unsupported. A packaged VSIX does not establish Marketplace
publication.

## Project input settings in 0.7

A manifest can include `data`, `contract`, and `proposal_contract` paths.
Each path is a relative `.json` file inside the project root. All systems use `/`.
Run, check, test, and lint use those defaults. The matching command flag overrides
one default. A blank path or invalid file produces an error; it cannot disable a check.

Use `pack PROJECT --name NAME --output FILE.sigil.json` to share a runnable project.
The portable file contains entry source, imported modules, input, and contracts.
Separate project test files are not included. Share the source folder for those tests.
See the [quickstart](quickstart.md) for a complete measured-result example.
