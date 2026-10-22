# ZenSigil for Visual Studio Code

The extension adds an editor language server to `.zs` highlighting, snippets,
indentation and bracket support. It checks unsaved source, offers completion and
hover signatures, navigates to local or imported function definitions, lists
symbols, finds references, and formats a document without changing its syntax tree. It never runs
the ZenSigil program to produce editor diagnostics.

The Problems panel separates errors from advice. A syntax or binding failure has
Error severity. An unused binding, a shadowed name, or a known type conflict has
Warning severity. These warnings use the same checks as `zensigil lint`. Type
advice is conservative. It does not infer unknown input values and does not replace
the runtime type checks.

Directly imported namespace aliases support exported-member completion after a dot,
qualified hover and definitions. Private helpers stay out of unrelated source scopes.
This is direct alias resolution, not general static type inference. See
[the editor reference](https://github.com/zenoutlabs/zensigil/blob/main/docs/editor.md).

Install the release VSIX through **Extensions: Install from VSIX**. Install the
matching ZenSigil wheel in a Python 3.9+ environment, then set `zensigil.pythonPath`
to that environment's Python executable. Changing the interpreter restarts the
server. Workspace folder changes update imports without a window reload. The path is a machine setting and must identify
one executable, without shell arguments. The extension starts it as
`python -I -m zensigil lsp`; isolated Python loads the installed package, rather
than a similarly named module inside the workspace.

Open the project directory as a **trusted workspace**. Import paths start at the
most specific containing workspace folder. Choose the folder containing your
project's `zensigil.json` when opening a project. Only explicitly reachable `use`
modules are read. Unsaved module buffers override their disk copies, including
new files. The extension does not download dependencies or open a network port.
It never starts a process in an untrusted workspace.

The extension watches workspace `.zs` files and refreshes import diagnostics after
a disk change. Use **ZenSigil: Check Program** if a path is excluded from watching.
Use **ZenSigil: Restart Language Server** after a server failure. It resends open
source and clears old diagnostics. Find References searches open programs and
their explicit imports. It does not scan unopened programs. Results are limited
to 1,000 locations and 512 KiB; larger results return an error. Completion/hover/navigation use valid
parsed source; incomplete syntax retains keyword and standard function completion.
Input JSON and runtime-only type checks are not inferred by the editor.

Snippets include `fn`, `test`, `while`, `use`, `when`, `propose`, `lambda`, and
`typedlist`. Four spaces are the language's block indentation. The grammar
recognizes anonymous-function arrows, union annotations and generic annotations.

Run `npm test` here for the transport and simulated VS Code host tests. Protocol
and source-service tests live in `tests/test_lsp_v05.py`. A real extension-host
harness is supplied in the source checkout at `editors/vscode/test/host.js`;
its isolated launch recipe and validation status are in `docs/editor-v05.md`.
The standalone harness in `test/host-standalone.js` tests the actual providers in
an empty trusted window. Its setup and evidence rules are in `test/README.md`.
Treat workspace import testing as a separate result.

To package a VSIX using Microsoft's separately installed `vsce`, run
`vsce package --allow-missing-repository`. Packaging needs Node.js and `vsce`;
the Python language server has no third-party dependencies. This source is not
an assertion of Marketplace publication.
