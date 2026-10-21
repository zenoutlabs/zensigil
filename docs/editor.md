# Editor support

ZenSigil's language server provides diagnostics, completion, hover, definitions,
document symbols and formatting. It checks source without executing programs.
The bundled VS Code extension uses the same `zensigil lsp` command available to
other LSP clients. Both the Python server and JavaScript client use only their
standard libraries; no network service or socket listener is involved.

## Set up VS Code

1. Install the ZenSigil wheel in your chosen Python environment.
2. Install the matching VSIX from the release assets.
3. Set the user-level `zensigil.pythonPath` setting to that Python executable.
4. Open the module root as a workspace and reload the window.

The extension runs only in a trusted workspace. Its machine-scoped interpreter
setting cannot be supplied by a repository's workspace configuration. It starts
`python -I -m zensigil lsp` without a shell; isolated Python prevents a workspace
file from replacing the installed interpreter package. Trust remains a user
decision, as described in [VS Code's workspace-trust documentation](https://code.visualstudio.com/api/extension-guides/workspace-trust).

## Namespaced modules

```text
# lib/math.zs
fn helper(value):
    return value * 2

export fn double(value: number) -> number:
    return helper(value)
```

```text
# main.zs
use "lib/math.zs" as math
emit math.double(21)
```

Typing `math.` suggests `double` and its signature. `helper` is private to its
module and does not appear in that list. Hover over `double` to see its annotated
signature, or use Go to Definition to open its actual declaration in
`lib/math.zs`. Hovering over `math` shows its imported path; Go to Definition on
the alias returns to its `use` declaration. Aliases appear as namespace symbols.

Functions and aliases resolve in their defining source file. Two imported
libraries can each declare `double` or use an alias called `math`; navigation
keeps their canonical source identities distinct. Ordinary completion shows only
the requested source's visible functions, aliases and lexical bindings. Private
helpers remain available while editing their own module. Existing bare imports
and their public re-exports keep working.

The snippets `useas` and `exportfn` insert a namespaced import and exported
function. Highlighting includes `as`, `export`, the `namespace` annotation,
anonymous functions, unions and generic annotations.

## Unsaved changes and incomplete code

Open buffers overlay disk files, including new unsaved modules. Changing a
module's exports immediately changes its importers' completion and definition
results. Import diagnostics are republished for open programs, and older document
versions cannot replace newer source. Closing a module restores the disk version;
the language server never saves files.

Completion supports unfinished direct aliases such as `math.`, `emit math.d`
and `return math.`. It recovers the current line for this query only and then uses
the normal parser, compiler and explicit module loader. It never repairs or
executes the user's buffer. An incomplete expression spanning several lines or
another syntax error can still prevent semantic completion. Keywords and built-in
functions remain available in ordinary non-member completion.

Only direct declared aliases receive namespace-member completion and navigation.
The language accepts computed namespace values such as `let library = math`, but
the editor does not infer the value of `library`, record fields, function return
values or namespace parameters. It does not offer rename, find references,
signature-help popups, semantic tokens or static type inference.

## Filesystem boundaries and protocol

Imports are resolved relative to the most specific containing workspace root.
Only explicitly reachable imports are read, and resolved paths must stay inside
that root. No directory scan, package download or implicit project search occurs.
Symlink escapes and cycles are rejected. Non-file buffers work as standalone
documents but cannot load filesystem imports without a containing declared root.

Source and module limits remain 64 open documents, 64 KiB per source, 32 modules,
256 KiB combined module source and eight import levels. The stdio server accepts
full-text versioned changes, uses UTF-16 positions, and returns whole-document
format edits. Invalid source is preserved. Wire limits are 8 KiB of headers and
1 MiB per JSON message. Protocol errors go to stderr; stdout contains framed
JSON-RPC messages only.

Changes made by another application are picked up by a subsequent editor query;
use **ZenSigil: Check Program** or edit a source buffer to refresh diagnostics.
There is no file watcher. Reload the window after changing workspace folders or
the interpreter setting.

The transport and capability subset follow [Microsoft's LSP 3.17 specification](https://github.com/microsoft/language-server-protocol/blob/gh-pages/_specifications/lsp/3.17/specification.md).
VS Code integration uses its documented [language providers](https://code.visualstudio.com/api/language-extensions/programmatic-language-features),
including a dot completion trigger. See [the protocol notes](editor-v05.md) for
framing, lifecycle and the isolated real-host test recipe.

## Verification status

Automated evidence includes the real Python parser/compiler/checker, a stdio
subprocess, JSON-RPC lifecycle and framing, UTF-16 positions, source-aware module
navigation, private-member exclusion, incomplete dot completion, stale versions,
unsaved module exports and filesystem boundaries. JavaScript tests cover client
transport, provider routing, the dot trigger and no interpreter startup in an
untrusted fake host. Tests are in `tests/test_editor_v06.py`,
`tests/test_lsp_v05.py` and `editors/vscode/test/*.test.js`.

The actual VS Code extension-host harness exists, but its previous local launch
stalled at workspace trust and did not complete assertions. These automated
results therefore do not claim successful validation inside the real VS Code UI.

## Advisory warnings in 0.7

The server uses lint, which first performs the existing syntax and binding checks.
A failed check is an Error (LSP severity 1). Advisory findings are Warnings (severity 2).
Warnings can describe unused code, shadowed names, unreachable code, or known type
misuse. They keep their source file and location. Editing a file updates the warning.
See [type advice](type-diagnostics-v07.md) for what the checks cannot prove.

### Large diagnostic results

Each editor message has at most 200 diagnostic items and 512 KiB of encoded JSON.
Errors have priority when the full result does not fit. `W_EDITOR_LIMIT` or
`E_EDITOR_LIMIT` states that some results were omitted. Run the command-line
checker or linter to inspect a larger result. This limit keeps the editor connected.
