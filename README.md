# ZenSigil

**A readable experimental programming language with a general core and reviewable intent.**

ZenSigil 0.7.0 is a working interpreter, command-line tool, and local browser
playground. It takes JSON data and produces structured values, proposed actions and notes. The core
knows nothing about Amazon, inventory, or support tickets; those are example programs.

```text
fn double(value):
    return value * 2

say "Twice 21 is " + text(double(21))
```

Use the same language for collections, reusable calculations, data checks, and
reviewable workflow proposals. Stock review is one example, alongside support
triage and general programming examples. The core has no industry-specific syntax.

This runs without an AI model or API key. Python executes the interpreter; the
browser playground sends code to that same local interpreter. Proposals are previews:
there is no purchasing, messaging, network connector, or action executor.

## Try it

Requires Python 3.9 or newer. The Python runtime uses only the standard library.
The included browser build needs no npm installation to run.

Get the public source, then start the playground:

```sh
git clone https://github.com/zenoutlabs/zensigil.git
cd zensigil
```

From this project's folder:

```sh
python3 -m zensigil serve --port 8766
```

Open **http://127.0.0.1:8766** in your browser. Keep the terminal running; Ctrl+C stops
the server. If that port is occupied, choose another with `--port` and use its URL.
The server listens only on your own computer. To share a demo, share the source
bundle so the other person can run their own copy.

In the playground, select **Closures & function factories** and click **Run preview**.
The program filters and transforms its input into `[21, 30]`. Click **Run tests**
to verify its capture and function-factory behavior. Try **Stock review** for an
example of explained proposals, or **Grouping & collection analysis** for structured
data transformations. Code, input, and optional input contracts are editable. Edits clear the old result.
Use **Save program** to keep a named copy in this browser, then **Open saved** to
reopen it. Latest drafts recover after reload, including unfinished code or JSON.
Use **Export program** and **Import program** for portable `.sigil.json` files
containing source, input, both optional contracts and source modules. Browser storage is specific to this browser
and local address; portable files are the backup/sharing route. Opening another
program with unsaved edits offers Save & open, Discard & open, or Cancel.

## New in 0.7

Start with the [short developer quickstart](docs/quickstart.md). No course is required.
A project can now name its input and contract files. Commands use those defaults.
Explicit flags can override them. You can export the runnable project:

```sh
python3 -m zensigil init my-project
python3 -m zensigil run my-project
python3 -m zensigil lint my-project
python3 -m zensigil test my-project --fail-if-empty
python3 -m zensigil pack my-project --name "My project" --output my-project.sigil.json
python3 -m zensigil run my-project.sigil.json
```

Lint now warns about some known type errors before execution. The editor shows
warnings separately from errors. The playground has a **Find warnings** button.
These checks do not execute source or prove runtime success. Unknown values remain
unknown. Read [type advice and its limits](docs/type-diagnostics-v07.md).

This release also fixes malformed project-version and output-path failures.
See the [45-needs audit](docs/adoption-audit-v07.md), [24-outcome plan](docs/next-v07.md),
[current claim check](docs/reality-check-v07.md), and [release evidence](docs/release-evidence-v07.md).
External developer trials remain future evidence. The [trial brief](docs/developer-trial.md)
is a proposed plan, not an active reward offer.

## Foundation from 0.6

Give reusable libraries clear names and public APIs:

```text
# main.zs
use "lib/math.zs" as math
emit map([1, 2, 3], math.double)

# lib/math.zs
export fn double(value: number) -> number:
    return value * 2
```

Once a module uses `export fn`, its unmarked functions become private helpers.
Two modules can use the same helper names independently. Existing bare imports
remain available; each library now resolves dependencies from its own imports.
See the [migration notes](docs/compatibility.md) before upgrading larger programs.

Explore expressions in a transactional interactive shell, or produce CI test reports:

```sh
python3 -m zensigil repl
python3 -m zensigil test my-project --junit results.xml
```

The REPL supports multiline cells, undo/reset, explicit input/module files and
portable saves. It replays bounded successful source and shows only new output.
JUnit reports use a new output file and distinguish assertion failures from errors.
The standard library has **69 functions**, adding scan, min_by, max_by, sum_by,
unique_by, frequencies, flatten and record_from_entries. Try **Namespaced libraries**
and **Running totals & summaries** in the playground.

Read the [module specification](docs/modules-v06.md), [REPL guide](docs/repl.md),
[test-report guide](docs/test-reports.md), and [45-outcome ledger](docs/next-45-v06.md).
Editor completion and navigation understand directly imported namespace members;
they do not infer every runtime value's type.

## Foundation from 0.5

Anonymous functions capture immutable snapshots of the values around them. Use
nested collection annotations and unions to check data precisely at runtime:

```text
fn multiplier(factor: number) -> function:
    return fn (value: number) -> number => value * factor

let values_to_scale: list<integer> = [1, 2, 3]
emit map(values_to_scale, multiplier(3))
```

This emits `[3, 6, 9]`. The 0.5 standard library had 61 functions, including stable
grouping, counting, partitioning, flattening, searching and record projections.
Try **Closures & function factories**, **Nested types & optional values**, or
**Grouping & collection analysis** in the playground.

Developer tools now include a stdio language server, a VS Code client, advisory
linting, whole-project formatting, bounded stdin source, and test filtering/listing.

```sh
python3 -m zensigil lint my-project
python3 -m zensigil fmt my-project --check
python3 -m zensigil test my-project --filter Double --fail-if-empty --json
python3 -m zensigil test my-project --list
```

Read [developer workflows](docs/developer-workflows.md), [0.5 syntax](docs/syntax-v05.md),
[editor integration](docs/editor-v05.md), the [45-step release ledger](docs/next-45-v05.md),
and the [30 additional capabilities](docs/additional-capabilities.md).

## Foundation from 0.4

Write richer programs with typed local state, while loops, named function values,
lazy expressions and structured emit results. Compose collections using map,
filter and fold, import explicit pure source modules, and write executable test
blocks. The runtime adds 37 standard functions, including exact decimal-text helpers.

```text
fn double(n: number) -> number:
    return n * 2

emit map(range(1, 4), double)

test "Double":
    require double(5) == 10, "Expected 10."
```

Run preview returns the structured value [2, 4, 6]. Run tests executes the isolated
expectation and skips the main program. Check performs structural/binding checks;
optional type annotations are enforced during execution. Functions receive their
data explicitly and cannot emit effects.

Try Algorithms & typed state, Collection transformations, Modules & executable tests,
or Exact decimal text in the playground. Use Source modules to edit reusable code,
Format source for consistent layout, and the guide to search the running function
reference. The local VS Code extension adds diagnostics, completion, hover, definitions, symbols,
formatting, highlighting and snippets; see editors/vscode/README.md.

```sh
python3 -m zensigil init my-project
python3 -m zensigil run my-project
python3 -m zensigil test my-project --json
python3 -m zensigil fmt examples/algorithms.zs --check
python3 -m zensigil ast examples/algorithms.zs --json
python3 -m zensigil test conformance/language.zs --json
```

See [the 45-capability assessment](docs/language-capabilities.md),
[the linguistic rationale](docs/linguistic-design.md), and
[the 45-step implementation ledger](docs/next-45-v04.md).

## Portable programs

Export a program in the playground and run the same file from a terminal:

```sh
python3 -m zensigil run my-program.sigil.json --json
python3 -m zensigil examples
python3 -m zensigil example reading-list --output my-reading-list
python3 -m zensigil doctor --json
```

Optional proposal contracts describe permitted actions and their fields. If any
proposal fails, the entire preview is discarded. In the playground you can also
check without running, download source, inspect proposal origins, and use
Ctrl/Cmd+Enter to run or Ctrl/Cmd+S to save. Existing 0.2–0.6 portable files and saved
browser drafts open in 0.7. See the compatibility guide for limits.

## Command line

```sh
python3 -m zensigil check examples/restock.zs --data examples/restock.json
python3 -m zensigil run examples/restock.zs --data examples/restock.json
python3 -m zensigil run examples/restock.zs --data examples/restock.json --json
python3 -m zensigil run examples/stock-review.zs --data examples/stock-review.json --contract examples/stock-review.contract.json --proposal-contract examples/stock-review.proposal.json
python3 -m unittest discover -s tests -v
```

Failures exit with status 1 and point to a source line. `check` verifies syntax and
bindings, not all runtime types or data fields. With no `--data`, it lists possible
input names rather than verifying them.

Optional installation in a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/zensigil --version
```

## Twenty-three examples

| File | What it demonstrates |
| --- | --- |
| `examples/namespace-lab.zs` | Independent libraries, exports and private helpers |
| `examples/sequence-lab.zs` | Running totals, extrema and record construction |
| `examples/algorithms.zs` | Typed iterative algorithms and executable tests |
| `examples/transformations.zs` | First-class callbacks, filtering, sorting and folding |
| `examples/module-lab.zs` | Pure modules, structured output and tests |
| `examples/closure-lab.zs` | Captured values and returned functions |
| `examples/typed-data.zs` | Nested collection types and optional values |
| `examples/collection-lab.zs` | Stable grouping, partitioning and flattening |
| `examples/decimal-lab.zs` | Exact decimal-text arithmetic and rounding |
| `examples/reading-list.zs` | Choose an unread book within a page limit |
| `examples/event-capacity.zs` | Review overbooked community events |
| `examples/project-budget.zs` | Compare project budgets using integer cents |
| `examples/stock-review.zs` | Validated input, configurable policy, exact quantities and explanations |
| `examples/restock.zs` | Restock review, optional sales data, discontinued products |
| `examples/shipments.zs` | Missing or extra received units |
| `examples/margins.zs` | Simplified contribution-margin review using integer cents |
| `examples/hello.zs` | Named values and strings |
| `examples/functions.zs` | A pure recursive function |
| `examples/records.zs` | Records, lists, field access and indexing |
| `examples/optional.zs` | Optional fields and short-circuit conditions |
| `examples/support.zs` | A non-commerce application |
| `examples/duplicates.zs` | Collapsing duplicate proposals within a preview |
| `examples/error.zs` | An intentional failure that discards earlier proposals |

Every example has a matching `.json` input file. Stock review, support, reading list, event capacity and project budget also
have `.contract.json` input and `.proposal.json` output contracts. All data is synthetic. The stock example supports
up to 400 products per preview; larger collections must be split into batches.

## Learn and review

- [Developer quickstart](docs/quickstart.md)
- [Current audit and claims](docs/reality-check-v07.md)
- [Developer workflows and automation](docs/developer-workflows.md)
- [0.6 release evidence](docs/release-evidence-v06.md)
- [0.5 release evidence](docs/release-evidence-v05.md)
- [Learn in six small programs](docs/learn.md)
- [Start here: a guided first session](docs/start-here.md)
- [Command-line tools and portable programs](docs/cli.md)
- [0.4 syntax and meaning](docs/syntax-v04.md)
- [Standard functions](docs/stdlib.md)
- [Modules](docs/modules.md)
- [Formatter, AST and projects](docs/tooling.md)
- [Proposal contracts](docs/proposal-contracts.md)
- [Fix common errors](docs/troubleshooting.md)
- [Compatibility and migration](docs/compatibility.md)
- [Release notes](CHANGELOG.md)
- [Static project introduction](docs/index.html)
- [Build and release checklist](docs/releasing.md)
- [Python embedding example](examples/embed.py)
- [0.4 release evidence and limitations](docs/release-evidence-v04.md)
- [Historical 0.3 release plan](docs/next-50.md)
- [Language rules and current limits](docs/language.md)
- [Input contracts](docs/contracts.md)
- [Project introduction and public release notes](docs/project-introduction.md)
- [How the interpreter works](docs/architecture.md)
- [Give another AI the language reference](docs/ai-reference.md)
- [Next milestones and review questions](docs/roadmap.md)
- [Contributing and focused review](CONTRIBUTING.md)

## Develop the playground

The committed browser bundle is ready to use. To change the React UI:

```sh
cd playground
npm ci
npm test
npm run build
```

The build refreshes `zensigil/web/` and the packaged example copies in `zensigil/demo/`.
Reload the browser after a build. For Vite hot reload, keep the Python server on 8766,
run `npm run dev`, then open the URL Vite prints. No external fonts, analytics,
AI endpoints, or CDN assets are required by the delivered playground.

## Status and limits

This is a local, AI-assisted experimental prototype, not a production workflow
platform. The Python suite covers language behavior, contracts, exact quantity boundaries,
CLI and HTTP; Node tests cover portable files and draft recovery. Those
tests provide evidence of the behaviors they exercise, not a proof of correctness.

There is no persistent execution history, connector schema, durable approval system,
or persistent idempotency. Stable proposal IDs and within-preview duplicate collapse
do **not** promise exactly-once delivery. A future executor needs its own durable
state and retry design. The interpreter's limits are prototype guardrails, not a
multi-tenant security boundary. Ordinary decimal numeric calculations use floating point; exact decimal-text helpers are explicit.

The language reference is the design contract for this version. Syntax may change
before 1.0. The name is a working project name; availability has not been established.
The source is available under the [MIT license](LICENSE). Source publication is tracked at [zenoutlabs/zensigil](https://github.com/zenoutlabs/zensigil).
Package-registry and editor-marketplace publication are separate future steps. Third-party
UI notices are included. See the project introduction for accurate public copy and
the next publication steps.
