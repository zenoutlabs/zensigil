# Explicit source modules

Main source:

```text
use "lib/math.zs"
emit double(4)
```

Supplied module `lib/math.zs`:

```text
fn double(n: number) -> number:
    return n * 2
```

The result contains `values: [8]`. Imported modules contain only pure functions,
test blocks and further use declarations. Bare imports bring public functions into
the importing file's function scope; distinct functions with the same visible name
collide. Repeated or diamond imports of the same function are deduplicated. Cycles
fail. Nested use declarations are rejected; use belongs at the top level.

In 0.6, `use "lib/math.zs" as math` provides an immutable namespace, so callers use
`math.double(4)` and different libraries can keep the same helper names. A module
with no export markers exposes its own functions and functions obtained through
bare imports. Once it declares any `export fn`, only its own marked functions are
public; unmarked helpers remain private. Functions resolve dependencies in their
defining source, and aliased imports do not re-export a namespace's members. See
[namespaces, exports and compatibility](modules-v06.md) for the complete rules.

Paths are case-sensitive, root-relative logical `.zs` names, including when used
inside another module. For example, `lib/math.zs` imports `lib/shared.zs` by that
full name. Parent traversal, absolute paths, backslashes, remote URLs and names
that differ only by case are rejected. A module path cannot simultaneously be a
file and another module's directory.

The Python API receives explicit source text:

```python
from zensigil import run, test
modules = {"lib/math.zs": "fn double(n):\n    return n * 2\n"}
result = run('use "lib/math.zs"\nemit double(4)', {}, modules=modules)
assert result["values"] == [8]
```

The API never reads files implicitly. The CLI's host convenience loader reads
explicitly referenced files inside the source directory or `--module-root`.
Resolved symlink targets must stay inside that root. Use `zensigil init DIR` for
an example project, then `zensigil run DIR` and `zensigil test DIR`.

The playground's Source modules panel edits the same explicit source map.
Portable exports carry a `modules` object alongside source, raw input and contracts.
Opening a file does not execute it. An imported failure identifies its logical
filename, source line and call chain; the playground can focus the module editor.

Limits: 32 supplied modules, 64 KiB per module, 256 KiB total module text, and eight
levels of imports. Each file has the ordinary parser limits. Runtime execution
shares the same step/call/output guardrails as the entry program. Even unused
supplied module names and sizes are validated; source syntax is parsed for the
reachable import graph.

Unpack preserves module names. If a module conflicts with the normal `program.zs`
or input-sidecar output path, the entry/sidecar gets a leading underscore until
its path is available. The command reports the filenames it created.
