# Version and compatibility policy

ZenSigil is experimental. Before 1.0, releases may change syntax or behavior, but
changes should be listed in the changelog with a migration path. A passing version
check means the file format is supported; it is not a promise that every business
policy will remain appropriate.

## 0.5 to 0.6

Portable format 1 accepts language versions 0.2.0 through 0.6.0 and normalizes to
0.6.0. Project manifests accept 0.4.0, 0.5.0 and 0.6.0. This preserves raw source;
it does not rewrite programs to repair semantic changes.

`as` and `export` are new reserved words. New standard names are scan, min_by,
max_by, sum_by, unique_by, frequencies, flatten and record_from_entries. Rename
existing bindings/input fields that use these names. `namespace` is a new runtime
annotation for opaque module references, distinct from JSON records.

Bare `use` still exposes functions from unmarked modules. `use "path.zs" as name`
creates a namespace; after a module declares any `export fn`, only its explicitly
exported functions are public. Libraries resolve names in their own source scope.
A library that previously relied on a caller's or sibling's function must now import
that dependency itself. A module without export markers still re-exports functions
obtained through bare imports, including transitive dependencies. Aliased imports
keep their members inside their namespace, and a module with export markers exposes
only its own marked functions. Under that explicit export policy, use an exported
wrapper to expose another library's behavior. See [modules-v06.md](modules-v06.md).

The REPL, JUnit report option and new editor features are additive. The local VSIX
publisher identifier is now `zenoutlabs.zensigil`; this is a bundled extension,
not a claim of Visual Studio Marketplace publication. Use an installed 0.6 runtime.

## Historical: 0.4 to 0.5

Portable format 1 accepts 0.2.0, 0.3.0, 0.4.0 and 0.5.0, normalizing opened files
to 0.5.0. Project manifests accept 0.4.0 or 0.5.0; new projects use 0.5.0.
Older runtimes cannot execute the new syntax. Plain source has no embedded version.

`=>` introduces an anonymous function expression. `|` separates type alternatives;
`list<T>` and `record<T>` recursively check collection elements. These annotations
and captured environments consume execution steps, so programs at a resource limit
may require smaller workloads. Captures preserve bindings at creation time.

New reserved standard names are group_by, count_by, partition, flat_map, find,
find_index, take, drop, chunk, record_pick, record_omit and clamp. Rename existing
input keys/bindings using these names. Original example behavior remains covered.

CLI additions are opt-in: lint warnings fail only with --strict; empty test selections
fail only with --fail-if-empty. Listing tests is discovery, not a passing test run.
The VS Code extension now needs an installed 0.5 interpreter, selected using its
machine-scoped pythonPath setting. It runs Python with -I and never executes .zs
programs for diagnostics.

## 0.2 and 0.3 to 0.4

Portable format 1 now accepts language versions 0.2.0, 0.3.0 and 0.4.0 and
normalizes opened files to 0.4.0. The optional modules object defaults to {}.
Source modules and the entry source retain their raw text, including unfinished syntax.
New exports require a 0.4 reader. Older releases reject the new version.

New reserved words: var, set, while, break, continue, choose, then, emit, test and use.
New standard-function names are listed in stdlib.md. Earlier programs that use these
names as bindings or input keys must rename them. The original bundled examples
remain covered by expected-result regressions. Record helper names use a record_
prefix to preserve common input names such as values.

Annotations are optional runtime checks. User function values do not capture lexical
environments. Modules use a flat namespace. emit adds structured values to results;
failed results now explicitly include an empty values array.

The following section records the previous upgrade behavior.

## Historical: 0.2 to 0.3

The language syntax and built-ins are unchanged. Existing `.zs` programs continue
to run. Proposal validation is opt-in: programs without a proposal contract retain
their prior behavior.

Portable program **format 1** accepts `language_version` equal to `0.2.0` or
`0.3.0`. Opening a 0.2 program normalizes its version to 0.3.0. The new optional
`proposal_contract_text` field defaults to an empty string. New exports include
this field. Older 0.2 applications do not accept 0.3 exports; keep the earlier
source bundle if you need to reproduce that older environment.

Source, input and contract text are preserved verbatim, including unfinished drafts.
A draft can be opened or unpacked even when its inner JSON or source is invalid.
Running or checking it then reports the problem. Saved/exported programs need a
nonblank name; recovery of an unfinished browser draft permits a blank name.

Unknown envelope fields and unsupported versions are rejected rather than silently
discarded. Both readers limit envelope size to 10 MiB and each raw field separately.
The browser and Python reader share compatibility fixtures and reject duplicate
JSON envelope keys and unpaired Unicode surrogates. For unambiguous sharing,
export through ZenSigil rather than hand-editing the envelope.

## Keep reproducible copies

Keep the program, data, both contracts and the ZenSigil version together. The
portable file records the language version but does not embed the interpreter.
Save release checksums alongside downloaded release files.

Proposal IDs identify equivalent action/fields/rule content within the current
implementation. They are not business idempotency keys or a stable public protocol
for a future executor. Browser storage is local convenience storage, not a database
or account synchronization service.

## Future changes

Changes to evaluation semantics require a specification update and regression
tests. Changes to the portable envelope require a deliberate format/version policy.
Native exact decimal values, static type inference, asynchronous I/O and a package registry remain
future design work. Closures, namespaces, the REPL and a language server are implemented with documented limits.

## Version 0.7

The source grammar and runtime rules are unchanged. Portable files from 0.2 through
0.6 open as 0.7 files. Project manifests from 0.4 through 0.6 remain supported.
Projects may now declare `data`, `contract`, and `proposal_contract` JSON paths.
Paths must stay inside the project. An explicit CLI flag overrides the matching
setting, including an invalid override, which reports an error.

`lint --strict` can now fail on new `W_TYPE` warnings. Plain lint remains advisory.
Check and run keep their existing meanings. The type pass does not infer all types;
see [its limits](type-diagnostics-v07.md). This is a pre-1.0 release.

## Version 0.8

Portable format 1 adds an optional `tests` source map. Older files get an empty
map. The 0.8 reader accepts 0.2–0.7 files. Project manifests accept 0.4–0.7.
The optional `entry_path` preserves the entry source identity when another test
imports it. Older files keep their anonymous entry identity. New files use 0.8.0.
Older readers reject the new version. Keep the older release
if you need to reproduce its behavior.

`unpack` and `example` now create a project manifest. It restores inputs, contracts,
and test entries. Test commands run shared module tests once, under a shared
100,000-step limit. A previous count could include the same module test more than
once. Test reports share a 1 MiB compact JSON limit. A report that reaches this
limit fails with `E_TEST_LIMIT` and sets `stopped_early`. Its counts cover the
retained results. Read [portable projects and tests](portable-tests-v08.md).

Collection builders validate each result before continuing. Retained sort keys
must fit the value budget. Copying collection values consumes execution steps.
These corrections can change which error appears first or make large programs
reach their limit earlier. `max_steps` in Python run/test accepts integers from
1 to 1,000,000. Invalid values return `E_INPUT`. Read the
[runtime change details](runtime-stability-v08.md).

The grammar and reserved words are unchanged. Error text and delimiter locations
are more precise. Unexpected indentation now reports `E_INDENT`. Find References
and editor restart are additive. Reference searches cover open programs and their
explicit imports; they do not scan every source file in a workspace.
