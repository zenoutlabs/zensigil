# Namespaced modules and exports in ZenSigil 0.6

Modules remain explicit source files supplied by the host. The language itself
never scans directories, fetches packages, or reads arbitrary files. Version 0.6
adds source-local import aliases, isolated function identities, and explicit
public exports.

```text
# lib/math.zs
fn helper(value: number) -> number:
    return value * 2

export fn double(value: number) -> number:
    return helper(value)
```

```text
# main.zs
use "lib/math.zs" as math

emit math.double(3)
emit map([1, 2, 3], math.double)
let double_later = fn (value) => math.double(value)
emit double_later(4)
```

This emits `6`, `[2, 4, 6]`, and `8`. `math.helper` is not accessible: the module's
explicit export marker makes only `double` public.

## Import syntax and lexical scope

`use "path.zs" as alias` binds an immutable namespace alias in the importing
source file. An alias is visible to that file's root code, named functions,
tests, and lambdas. Aliases and function declarations are known throughout their
source file, including before the textual `use` statement. Imports are top-level
only, and alias names must be ordinary, nonreserved identifiers.

An alias cannot collide with a built-in, another alias, or any function visible
in its importing source. Local declarations, parameters, and input keys cannot
shadow that source's import aliases. The same alias spelling is allowed in
*different* modules and can refer to different libraries there. Importing a module
does not expose the aliases that module uses internally.

Two files can declare functions with the same spelling without colliding when
accessed through aliases. Each module function has a canonical identity formed
from its root-relative source path and declared name. Calls inside a function
resolve names in its defining source, even when another module or the root
program calls it. A caller's input data, functions, and aliases do not become
ambient bindings in the called module.

Named functions keep their purity rules: parameters, local variables, built-ins,
and explicitly visible module functions/namespaces are available; root input
values are not implicitly captured. A function can accept data or a namespace
explicitly as an argument. Lambdas retain the immutable lexical snapshot rules
specified in [syntax-v05.md](syntax-v05.md).

## Public exports and private helpers

`export fn name(parameters):` marks a top-level named function as public. It has
the same annotations, body, recursion, and purity rules as an ordinary function.
Other statements, anonymous functions, nested functions, and import declarations
cannot be exported.

A module with **no export markers** exposes its own named functions and functions
it imports with bare `use`. This preserves the existing flat-import convention.
Once a module contains **any export marker**, only its own marked functions are
public. Its unmarked helpers and bare imported functions remain available inside
the module but are absent from its public surface. To expose an imported function
under an explicit export policy, write an exported wrapper function.

Exports are visibility rules, not a security boundary. Source remains inspectable.
An exported function may deliberately return a reference to a private helper;
that function value is callable because the module explicitly provided it.
There is no `export *`, import renaming of individual members, selective import
list, namespace re-export, or module initialization code in this release.

A source file containing export markers may also be used as the root program.
Its functions execute normally; the markers matter when another source imports
that file. Imported source may contain only named functions, test blocks, and
imports. It may not initialize top-level data or perform effects.

## Legacy bare imports and transitive composition

```text
use "lib/math.zs"
emit double(3)
```

Bare `use` brings the imported module's public functions directly into the
importer's function scope. Importing distinct functions with the same public name
is an error; use aliases to disambiguate them. Repeated or diamond imports of the
same canonical function are deduplicated. Importing the same file both directly
and through an alias yields equal references to the same exported function.

An unmarked module transitively exposes functions obtained through its bare
imports. An explicitly exporting module exposes only its own marked declarations.
Aliased imports never flatten their members into a surrounding scope.

Compatibility is intentionally precise: existing bare-import syntax and ordinary
flat composition continue working. Libraries must explicitly import functions
they use from other files. Code that previously relied on the old global
flattening to see a caller's functions or unrelated sibling imports must add the
missing `use`. This prevents a library's meaning from changing with the caller's
other dependencies. New keywords `as` and `export`, plus new standard-library
names in this release, require conflicting identifiers to be renamed.

All paths remain relative to the selected project/module root, including paths
inside imported files. They are not relative to the importing file's directory.
Aliases do not change path resolution. The API still receives an explicit
`modules={"path.zs": "source text"}` map; CLI and editor hosts resolve explicitly
named files within their declared module root.

## Namespace values, callbacks, and closures

A namespace is an opaque immutable value with type `namespace`:

```text
use "lib/math.zs" as math
let library: namespace = math

fn apply_double(library: namespace, value: number) -> number:
    return library.double(value)

emit type_of(library)  # "namespace"
emit apply_double(library, 5)
```

Dot access selects an exported function and returns a normal function reference.
References can be bound, called, passed to collection callbacks, returned from
functions, or captured by closures. Direct alias member calls receive normal
static arity checks; computed namespace values and function aliases check arity
at runtime. Selecting a missing or private member reports `E_IMPORT`.

A namespace is not a record. `has`, `get`, `record_keys`, `len`, indexed access
such as `library["double"]`, arithmetic, ordering, and calling the namespace
itself are invalid. A namespace cannot appear in lists or records, be emitted,
be serialized as JSON, or be converted to text. The `record` and `function`
annotations reject namespaces; `namespace` accepts them, and `any` accepts any
standalone language value. These are runtime checks, not static type inference.

Namespaces with the same module path compare equal within a program. Namespace
members do not have mutable cells or writable fields. `set` cannot change an
import alias. A separately declared `var` holding a namespace follows ordinary
binding reassignment rules; replacing that variable does not mutate the namespace
or an earlier closure's captured binding.

## Tests and source-aware diagnostics

Every reachable module is loaded and checked once. Its tests run once when the
host runs the test suite; ordinary program execution skips test bodies. A module's
tests can use its private helpers and explicit imports while remaining isolated
from root input values.

Test labels must be unique within their own source file. Different modules can
use the same label, such as `"round trip"`. Test result entries include
`source_name` to distinguish them. Existing name filters can select all matching
labels across files.

Unknown/private direct namespace members are checked even in untaken branches.
Computed namespace member selections are checked when evaluated. Diagnostics keep
the offending logical source filename, line, column, and source excerpt. Imported
named-function frames use `path.zs::function` to distinguish identically named
helpers; each frame also retains its call-site location. Closure frames retain
their existing definition-based names and source locations. A runtime error still
discards all accumulated values, notes, and proposals.

## Resource and filesystem limits

Existing limits remain: at most 32 supplied modules, 64 KiB per source file,
256 KiB combined module source, and at most eight import edges from the root.
The depth check accounts for cached/shared dependency paths, so a shorter earlier
import cannot hide a later over-deep dependency chain. Cyclic imports are rejected.
Module names remain at most 160 characters and must be plain root-relative `.zs`
paths, with no traversal, URL, absolute path, backslash, case-fold duplicate, or
file/directory collision.

Imported functions and namespace lookups share the ordinary execution step,
48-call-depth, value-size, closure-capture, and output budgets. Namespace member
lookup uses a shared immutable index; importing one file under many aliases does
not copy its export table for every alias. The compiler and checker retain source-
size/module-count bounds rather than introducing an unbounded dependency loader.

Host file loading reads only named reachable imports, verifies each resolved path
stays inside the selected root, rejects symlink escapes and symlink loops, and
limits each file read before decoding it. The language API performs no implicit
filesystem access. These prototype limits are not a multi-tenant sandbox claim.

## AST and integration contract

The public parser preserves existing raw AST shapes when no new syntax is used:

- Bare `use` stays `(path_string,)`; aliased `use` adds an alias `Token` at index 1.
- Unmarked `fn` keeps its five 0.5 fields; `export fn` appends `True` at index 5.
- The original function-name token and source locations remain unchanged.

`compile_program` removes imports, emits each reachable function/test once, and
adds internal `module_scope` nodes. Their parts are
`(source_label, visible_function_pairs, namespace_triples)`, where a function pair
is `(visible_name, canonical_identity)` and a namespace triple is
`(alias, module_path, exported_function_pairs)`.

Compiled `fn` nodes retain the first five fields, put the explicit-export boolean
at index 5, and the canonical identity at index 6. Root functions keep their bare
identity; imported functions use `path.zs::name`. Use `function_identity(node)`
instead of assuming source spelling is globally unique.

`module_scopes(program)` converts the metadata to a mapping from source label to
`{"functions": {visible_name: identity}, "namespaces": {alias: NamespaceRef}}`.
A `NamespaceRef` exposes internal host fields `.path`, `.members` (immutable
name/identity pairs), and `.member(name)` (lookup or `None`). These host helpers
are not accessible as ZenSigil object attributes. Editor and lint integrations
must use source-local metadata and ignore `module_scope` as an executable source
statement. Raw AST export remains JSON-compatible; the formatter preserves
aliases, export markers, annotations, comments, and expression semantics.

Behavioral regression evidence: `tests/test_modules_v06.py`.
