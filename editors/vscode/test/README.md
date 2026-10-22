# Test the extension in VS Code

`npm test` runs the transport and simulated provider tests. These tests do not
start VS Code.

The two host scripts run inside the installed VS Code application. Use a separate
user profile and extension directory for each run. Use a Python environment with
the candidate ZenSigil wheel installed. The scripts change the Python setting only
in the isolated profile. They do not save source files or disable workspace trust.

## Standalone source

Use `host-standalone.js` to test an empty window. An empty window is trusted by
default. Do not pass a workspace folder as a launch argument.

1. Make a short temporary directory outside the repository, such as `/tmp/zs-host`.
2. Make a `fixture` directory inside it.
3. Save this exact source as `fixture/standalone.zs`, with a final newline:

```zensigil
fn double(value: number) -> number:
    return value * 2
let amount=3
emit ["🌱",double(amount)]
```

4. Set these environment variables to absolute paths:

| Variable | Path |
| --- | --- |
| `ZENSIGIL_TEST_WORKSPACE` | The `fixture` directory |
| `ZENSIGIL_TEST_PYTHON` | The Python executable with the installed candidate wheel |
| `ZENSIGIL_TEST_EVIDENCE` | A new JSON file for the result |

5. Start the installed `code` CLI with these arguments. Replace the paths first.

```text
code --new-window
  --user-data-dir /tmp/zs-host/user
  --extensions-dir /tmp/zs-host/extensions
  --extensionDevelopmentPath /absolute/source/zensigil/editors/vscode
  --extensionTestsPath /absolute/source/zensigil/editors/vscode/test/host-standalone.js
  --skip-welcome --skip-release-notes --verbose
```

Enter the command on one line. If the graphical launch does not keep environment
variables, pass the same three variables as a JSON object with
`--extensionEnvironment`. Keep the user-data path short. On macOS, an IPC socket
path longer than 103 characters can stop VS Code before the tests start.

6. Read the JSON evidence file. It must be new and contain `"ok": true`. The CLI
   exit status alone is not proof of a successful test.

The script checks completion, hover, definition, references, server restart,
symbols, formatting, warning severity, error severity, and diagnostic repair. It applies the formatting edits
before checking their result. VS Code can split a provider's whole-document edit
into several small edits.

This test does not prove workspace imports or namespace completion in the real
application. The Python and simulated provider tests cover those features.

## Workspace imports

Use `host.js` with the workspace fixture and launch steps in
[`docs/editor-v05.md`](../../../docs/editor-v05.md). This script requires trust for
the synthetic workspace. Keep trust enabled. Accept trust only for the prepared
test directory. Record a trust timeout as an unverified result. Do not count it
as a provider failure or a successful host test.
