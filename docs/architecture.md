# How ZenSigil runs a program

This document describes the current 0.6 architecture. The explicitly versioned
0.3 and 0.4 sections retain the history of those milestones; later additions
and changed boundaries are recorded in the 0.5 and 0.6 sections below.

```text
Source text + JSON input
    → lexer → tokens
    → parser → syntax tree → explicit pure-module resolution
    → optional input contract validation
    → binding checker
    → tree-walking interpreter
    → complete preview OR diagnostic with empty output
```

## Files and responsibilities

| File | Responsibility |
| --- | --- |
| `zensigil/syntax.py` | Tokenizes source, checks indentation, parses statements and expressions |
| `zensigil/contracts.py` | Validates generic input contracts and data before execution |
| `zensigil/checker.py` | Resolves names, verifies arity/scopes, enforces pure functions |
| `zensigil/runtime.py` | Evaluates values and blocks, enforces limits, collects proposals |
| `zensigil/typesys.py` | Represents opaque function values and checks primitive, nested and union runtime annotations |
| `zensigil/stdlib.py` | Provides 61 pure standard functions with shared runtime callback and resource limits |
| `zensigil/modules.py` | Resolves explicit pure source modules and preserves source identity |
| `zensigil/lint.py` | Reports conservative unused-binding, shadowing and unreachable-statement advisories without execution |
| `zensigil/project_tools.py` | Enumerates explicit project sources and preflights project formatting |
| `zensigil/lsp.py` | Hosts the bounded stdin/stdout editor protocol and workspace source service |
| `zensigil/errors.py` | Shared line/column diagnostic format |
| `zensigil/jsonio.py` | Strict JSON boundary parsing |
| `zensigil/__init__.py` | Public `check()`, `run()` and `test()` entry points |
| `zensigil/__main__.py` | Command-line interface and process exit codes |
| `zensigil/server.py` | Loopback HTTP API and bundled playground files |
| `playground/src/` | React editor, preview, guide and request state |
| `tests/` | Language semantics, golden examples, CLI and HTTP checks |

## Trace a tiny program

```text
let threshold = 14
say text(threshold + 1)
```

The lexer recognizes words, the assignment sign, number, parentheses, plus sign,
and newlines. The parser makes a `let` node and a `say` node; the latter contains
a call to `text` whose argument is an addition.

The checker confirms that `threshold` exists before it is read and `text` takes
one argument. The runtime stores 14 in a dictionary representing the current
scope, adds one, converts 15 to a string and appends a note.

ZenSigil never passes source code to `eval`, `exec`, Python's AST, a shell, or an LLM.
Its fields access JSON records, not Python object attributes.

## Why this design

- Python standard library: easy to read, run and inspect; no compiler toolchain.
- A custom parser: ZenSigil owns the syntax rather than inheriting Python's quirks.
- Immutable collection values, lexical scopes and explicit var/set rebinding.
- Pure functions: calculation stays separate from visible notes and proposals.
- Domain-neutral proposal envelopes: stock, shipment and support programs use the
  same evaluator. Connectors will need separate typed contracts before execution.
- Transactional preview: the public API catches a failure and returns empty output.
- Deterministic output: no clock, randomness, network or external filesystem access
  from language programs. Same source/data yields the same successful preview.

## Proposal identities

The runtime hashes sorted, compact JSON containing the rule label, action name and
fields. It collapses identical envelopes within one run. Hash input omits source
locations, so moving a proposal to another line does not change its identity.
Different rule labels produce different IDs. Numeric JSON forms such as `1` and
`1.0` remain distinct in proposal identity even though they compare equal in the
language; a future canonicalization policy should resolve this before execution.

No history is stored. A future executor must define business identity, persist
attempts and outcomes, verify approval, and reconcile uncertain external results.

## Limits and remaining gaps

Source is bounded at 64 KiB and 20,000 tokens; expression bracket nesting is limited
to 48. Input is a JSON object up to 1 MiB, with at most 20,000 value nodes and 32
levels. Lists and records have at most 10,000 entries, and strings at most 65,536
characters. Runtime defaults to 100,000 steps, 48 function calls deep, and 1,000
output entries/1 MiB of serialized entries. Metadata and response wrappers add bytes.

Some aggregate operations do work outside the step counter. The server has no
tenant isolation, authentication, concurrency quotas or process-level resource
budget. It binds loopback, checks Host/Origin, limits request sizes, serves only
the built UI directory and supplies a restrictive content policy. It is a local
development convenience, not a deployable untrusted-code hosting service.

The checker is not a type inferencer. Optional sidecar contracts validate input
structure and types before interpretation; unknown contracts are rejected rather
than silently ignored. Code can use `require` for cross-field relationships.
Missing fields and wrong types outside a declared contract can still fail at runtime. Commerce examples do not encode complete business
policies, taxes, returns, storage costs, order constraints or procurement approvals.

## API

```python
from zensigil import check, run

source = 'say "Hello, " + name'
check_result = check(source, {"name": "Gregory"})
preview = run(source, {"name": "Gregory"})
assert preview["ok"]
```

HTTP endpoints: `GET /api/examples`, `GET /api/language`, `POST /api/check`,
`POST /api/run`, `POST /api/test`, and `POST /api/format`.
POST JSON contains `source` and either a `data` object or a `data_text` string
containing standalone JSON. Optional `contract` or `contract_text` supplies a
sidecar contract. Contract failures return `ok: false`, with field paths and empty output. The text form preserves duplicate-key errors for
the editor. Language errors return HTTP 200 with `ok: false`; malformed requests
return 400, disallowed origin/host 403, oversized requests 413, unsupported content
type 415. There are no side-effecting action endpoints.

## Exact quantity helpers

The stock-review example uses `fraction(daily)` and integer `ceil_div` to make
threshold and quantity decisions exact for the decimal spelling of supplied rates.
Ordinary `/` is still floating point, used only to display approximate days of stock.
The helpers are general arithmetic built-ins; no inventory code lives in the runtime.
If a number is computed with floating point before calling fraction, fraction preserves
that resulting decimal spelling; it does not undo prior rounding.

## Portable programs and browser storage

`playground/src/programs.mjs` checks versioned `.sigil.json` files and browser-library
records. A program stores raw source, input text, optional contract text and module sources, allowing
invalid drafts to survive save/reload. Opening a file never executes it automatically.
Library storage is browser-local; changing origin/port or clearing browser data can
make saved entries unavailable. Export is the portable backup route. Storage failures
are reported visibly. Saved programs contain no execution history or approval state.

## 0.3 sharing and output validation

`programs.py` and the browser codec implement portable format 1, with shared
fixtures in `tests/fixtures/portable-cases.json`. They preserve unfinished raw text;
execution interfaces parse it only when checking or running. The CLI protects all
source/input paths from output replacement, including filesystem aliases.

`proposals.py` validates optional action contracts before execution, then checks
emitted fields with a per-run validation cache. Failure discards all proposals and
notes. There is no global schema cache and no business-specific action semantics.
The browser's request helper aborts stale requests and times out after 15 seconds;
this cancels the request, not Python work already running on the server.

## 0.4 language composition

`modules.py` resolves bounded explicit source maps and adds source identity to tokens;
only the CLI host reads local files, constrained by a project root. `typesys.py`
checks shallow optional runtime annotations. `stdlib.py` dispatches pure bounded
operations and callbacks through the same interpreter and step budget.
`testing.py` executes isolated test blocks without main effects.
`formatter.py` preserves comments and validates the formatted AST; `astio.py`
exposes a versioned parse document. `projects.py` loads strict project manifests.

The playground carries module source maps through its portable codec. API results
include a values array alongside notes and proposals. All three are empty on run
failure. Full static inference, lexical closures and namespace imports are future work.

## 0.5 closures, annotations and developer tools

Anonymous `fn (...) => expression` functions capture immutable snapshots of only
their referenced outer bindings. Later `set` operations do not alter those
captures. Named functions retain their isolation from root input and bindings;
closures created inside them can retain parameters and local values. Function
values remain opaque and cannot enter JSON lists, records or output. The runtime
charges free-name discovery, capture traversal and calls against its step budget,
with cumulative capture limits of 20,000 nodes and 1 MiB of text/scalar content.
See [the 0.5 syntax reference](syntax-v05.md) for snapshot and identity semantics.

`typesys.py` now checks nested `list<T>`, `record<T>` and `T | U` annotations at
binding initialization, reassignment, calls and returns. Traversal and union
attempts consume execution steps. These remain runtime checks; static inference,
named type aliases and module namespaces are future work.

`lint.py` uses the checked syntax tree for conservative lexical advisories. It
does not evaluate code or prove that all paths terminate. Test filtering and
listing operate on explicit test blocks; listed cases have zero execution steps
and are not counted as passed. Project formatting discovers only manifest entries,
test sources and reachable imports, checks every source before writing, and uses
atomic replacement per file. It is not a transaction across multiple files.

The editor source service also reads explicit local imports within a declared
workspace root, with unsaved buffers taking precedence. The public language API
continues to accept supplied module maps without host file reads. `zensigil lsp`
uses the same checker and formatter for diagnostics, completion, hover,
definitions, symbols and formatting, without executing programs. Its protocol,
workspace boundaries and unsupported features are detailed in
[the editor reference](editor-v05.md). The VS Code extension is a client for that
service; simulated-provider tests and a real-host validation run are distinct
forms of evidence.

## 0.6 module linking and interactive sessions

Compilation retains source tokens while assigning internal function identities and
per-source function/namespace tables. Checker, runtime and editor queries consume
those tables. Namespace references are immutable and remain outside JSON. See
[modules-v06.md](modules-v06.md). The [REPL](repl.md) validates accumulated source,
replays successful cells under cumulative budgets and commits a cell only on success.
[JUnit serialization](test-reports.md) consumes test results without executing source.
