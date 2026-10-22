# Editor changes in 0.8

The editor can find references, refresh imports after disk changes, and restart its
language server. These operations check source. They do not run a ZenSigil program.

## Find References

Place the cursor on a declaration or a use of a name. Select **Find All References**
in VS Code. Other clients can send `textDocument/references` to `zensigil lsp`.
The `context.includeDeclaration` field controls whether results include declarations.

The search covers open programs and the modules that they explicitly import. It
uses the current unsaved text of open files. It does not scan unopened programs.
A closed module can appear in results if an open program imports it.

Results distinguish the following cases:

- A local binding and a shadowed binding with the same name.
- A function parameter and a binding outside that function.
- A captured binding in an anonymous function.
- A direct namespace alias and its exported function members.
- Two module functions with the same name.

Repeated locations appear once. An unresolved input name or a built-in function
has no source declaration. The editor returns no references for those names.
The editor does not infer references through a computed namespace or a function
value. For example, `let library = math` does not make `library.double` a direct
reference to `math.double`.

A program with invalid syntax or an unresolved import can be omitted from the
search. Repair it before using the result to assess all affected source.
This operation is not a workspace-wide rename tool.

A result can contain at most 1,000 locations and 512 KiB of encoded JSON. A larger
result returns an explicit error. The server does not silently truncate the list.
Use a smaller set of open programs and try again. Invalid cursor positions return
no result. A cursor cannot split a UTF-16 surrogate pair, which encodes characters
such as an emoji.

## Workspace changes

Add or remove a workspace folder in VS Code. The extension updates the server and
checks open programs again. A window reload is not required. Other clients can use
`workspace/didChangeWorkspaceFolders` with `event.added` and `event.removed` lists.

The server supports at most 32 roots. Imports use the most specific containing
root. A removed root no longer permits reads. If a containing parent root remains,
that parent becomes the root. Existing path, symlink, and explicit-import limits
still apply. The root change is atomic if it exceeds the limit.

The extension watches `.zs` files in the workspace. Create, change, and delete
events refresh open programs and their import diagnostics. Events are combined
for 100 milliseconds, with at most 256 distinct files in each notification. Only
explicitly imported source is read. A watcher event does not authorize a read of
an unrelated file. Unsaved editor text continues to take priority over disk text.

Other clients can send `workspace/didChangeWatchedFiles`. The server accepts at
most 256 events per notification. It ignores events outside declared roots and
unsupported event types. VS Code can exclude paths from its file watcher. Use
**ZenSigil: Check Program** if diagnostics do not reflect a disk change.

## Server recovery

Use **ZenSigil: Restart Language Server** after a server failure. The extension
clears old diagnostics, starts a fresh server, and sends all open source again.
Changing the user-level `zensigil.pythonPath` setting also restarts the server.
The selected interpreter still runs with isolated Python and without a shell.
Workspace trust remains required.

Replies from an old server cannot replace replies from its replacement. An editor
request also checks the document version before it returns a result. Process and
pipe failures clear pending requests. The extension stops a process that can no
longer communicate. Normal shutdown has a one-second fallback stop timer.

## Verification scope

`tests/test_editor_v08.py` checks reference identity, shadowing, module imports,
result limits, cursor validation, dynamic roots, watcher events, unsaved text, and
protocol responses. Earlier editor and protocol tests remain part of the suite.
`editors/vscode/test/*.test.js` checks transport cleanup and provider behavior in a
simulated VS Code host. It includes restart races, old replies, configuration
changes, watcher batches, and the workspace trust gate.

The real-host harnesses also contain reference and restart checks. Harness code
alone is not evidence that these checks passed. The release report must state
which harness ran, which wheel it used, and the result. A real workspace-import
check remains separate from a standalone-file check. Do not disable workspace
trust to make a test pass.

These additions follow the [Language Server Protocol 3.17 specification](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/).
