# ZenSigil 0.5 editor protocol

`zensigil lsp` runs a standard-library-only language server over stdin/stdout.
Other editors can start that command and use its advertised capabilities. It
opens no socket, performs no network request and does not execute user programs.
The VS Code extension is a small client for this same server.

## Supported operations

| Operation | Behavior |
| --- | --- |
| `initialize` | Declares UTF-16 positions, full-document synchronization and the capabilities below |
| `shutdown`, `exit` | Clean lifecycle; exit before shutdown has status 1 |
| `textDocument/didOpen`, `didChange`, `didClose` | Full source buffers, monotonically increasing versions, clear diagnostics on close |
| `textDocument/publishDiagnostics` | Syntax, import and binding diagnostics through the public `check()` API; no execution |
| `textDocument/completion` | Keywords, standard function signatures and visible parsed declarations |
| `textDocument/hover` | Function signatures and binding declarations, returned as plain text |
| `textDocument/definition` | Lexical locals, parameters and top-level functions, including explicit imported modules |
| `textDocument/documentSymbol` | Functions, bindings, parameters, rules and tests in the requested document |
| `textDocument/formatting` | Whole-document edit verified by the formatter; invalid source is preserved |

Anonymous functions participate in local navigation. Typed function hover supports
unions and nested list/record annotations. No static type inference is implied.
A malformed program keeps keyword and built-in completion; semantic navigation
and local completion require a valid parse. A reference to an input key has no
source declaration to navigate to.

The wire format follows [Microsoft's LSP 3.17 base protocol](https://github.com/microsoft/language-server-protocol/blob/gh-pages/_specifications/lsp/3.17/specification.md):
ASCII CRLF headers, a required byte-counted `Content-Length`, and UTF-8 JSON-RPC.
Position fields and full-text change notifications follow the advertised LSP
capabilities. The client uses the corresponding [VS Code language providers](https://code.visualstudio.com/api/language-extensions/programmatic-language-features)
to display results. These are a declared subset of LSP features; rename, references,
semantic tokens, signature-help popups, incremental edits and dynamic workspace
changes are not implemented.

## Source boundaries and limits

Initialization declares up to 32 workspace folder URIs. Module paths start at the
most specific containing workspace folder, use ZenSigil's existing root-relative
path rules, and must remain inside that root after resolving symbolic links.
Only explicitly reachable imports are read. There is no project scan, upward
manifest search, global search path or arbitrary file-URI read. Non-file buffers
can be checked as standalone source; imports require a declared containing root.

Open source overlays disk modules, including unsaved new modules. A changed module
causes open importers to be checked again. Module diagnostics retain the target
file URI and code-point locations are converted to UTF-16 editor positions.
The source service never saves the buffers. Versioned diagnostics allow the client
to discard stale results. Imports changed outside the editor are refreshed by
**ZenSigil: Check Program**, or by another source edit; there is no file watcher.

Bounds are 64 open buffers, 64 KiB per source, 32 modules, 256 KiB per module graph,
eight import levels, 8 KiB of framing headers and 1 MiB per JSON message. Oversize
headers/bodies are rejected before reading an oversized body. EOF in a partial
frame is an error, not a parser loop. Ordinary stdio waits for a client to complete
a valid announced frame; the client has a five-second request timeout. Invalid
JSON receives a framed parse error and the next valid frame can proceed. Fatal
framing errors exit with a bounded stderr message; stdout remains protocol-only.

## VS Code setup

Install the matching wheel into a chosen Python environment. Install the VSIX,
set `zensigil.pythonPath` to that environment's executable, and open the project
root as a workspace. The extension invokes isolated Python (`-I`) so workspace
Python files cannot shadow the installed ZenSigil package. It passes arguments
without a shell. No additional Node package or Python package is required at run
time beyond the ZenSigil wheel.

Both the extension manifest and the activation code enforce a trusted workspace.
This follows [VS Code's workspace-trust model](https://code.visualstudio.com/api/extension-guides/workspace-trust).
The machine-scoped interpreter setting cannot be supplied by repository workspace
configuration. Change the interpreter or workspace folders and reload the window.
The built-in Python service remains independently usable by other LSP clients.

## Verification and real-host recipe

Automated verification includes bounded framing, malformed JSON recovery, lifecycle,
real stdio subprocess traffic, stale changes, UTF-16 emoji locations, pure checking
of infinite/unsafe-to-run source, lexical shadowing and closed-block completion,
module overlays and source identity, symlink escape/cycle rejection and document
limits. The Node tests use both a fake subprocess transport and a simulated VS Code
host to exercise every provider and the untrusted-workspace process gate.

A real VS Code host harness is prepared in `editors/vscode/test/host.js`. Its outcome
must be recorded separately from these tests; preparation alone does not establish
that it ran successfully. Use an isolated synthetic workspace, user profile and
extension directory under `work/v05/editor-host` (outside the release source), and
an installed candidate wheel. Set these environment variables for the launch:

- `ZENSIGIL_TEST_WORKSPACE`: absolute synthetic workspace directory.
- `ZENSIGIL_TEST_PYTHON`: absolute Python executable containing the candidate wheel.
- `ZENSIGIL_TEST_EVIDENCE`: absolute JSON result path.

The workspace must contain `main.zs` exactly as follows (final newline included):

```zensigil
use "lib/math.zs"
let amount=3
emit ["🌱",double(amount)]
```

And `lib/math.zs`:

```zensigil
fn double(value: number) -> number:
    return value * 2
```

Launch the installed `code` CLI with `--new-window`, isolated `--user-data-dir` and
`--extensions-dir`, `--extensionDevelopmentPath` pointing at `editors/vscode`,
`--extensionTestsPath` pointing at `editors/vscode/test/host.js`, and the synthetic
workspace directory as its final argument. Do not disable workspace trust. Accept
the trust prompt for this synthetic directory in the isolated profile. The harness
waits up to 60 seconds for trust, configures Python only in that isolated profile,
then exercises the actual completion, hover, definition, symbol and formatting
providers plus unsaved module diagnostics and repair. It writes evidence whether
it succeeds or fails. No existing user workspace or VS Code profile is changed.


Recorded 0.5 release attempt: the harness launched in VS Code 1.141.0, but both
isolated runs timed out waiting for the synthetic workspace to become trusted.
No actual provider assertions ran in that host. The available native UI control
selected a different running VS Code instance, so this release records the host
check as unverified. No trust protection was disabled. Protocol and simulated-client
results remain valid; see `release-evidence-v05.md` for their exact scope.
Use `--verbose` and `--extensionEnvironment` containing the three variables as a
JSON object if a graphical launch does not preserve the launching environment.
