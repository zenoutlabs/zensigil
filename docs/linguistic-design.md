# ZenSigil as a language: vocabulary, grammar and meaning

ZenSigil 0.6 is designed around explicit reference and compositional meaning. A
small expression should keep the same meaning when it is placed inside a larger
program, subject to the same lexical scope and evaluation rules. Complexity comes
from combining useful constructs under consistent rules.

The historical [45-capability assessment](language-capabilities.md) distinguishes retained
features from strengthened and new ones in 0.4. The [45-step implementation ledger](next-45-v04.md)
records that delivery evidence. These lists describe the same language milestone from
design and implementation perspectives; they do not claim 90 unrelated new features.

## The linguistic layers

| Linguistic idea | Programming counterpart | ZenSigil decision |
|---|---|---|
| Vocabulary | Keywords and standard names | Keywords indicate stable roles; record helpers use a consistent record_ prefix. |
| Word formation | Lexical rules | Case-sensitive ASCII identifiers; Unicode text and quoted record keys. |
| Phrase structure | Expressions and nested syntax | Calls, records, collections, choices, anonymous functions and operators form explicit syntax trees. |
| Reference | Bindings and scope | A name denotes the nearest visible binding; closures retain snapshots of referenced bindings. |
| Meaning | Evaluation semantics | Evaluation order, types, laziness and errors are specified. |
| Communicative effect | Observable output | emit, say and propose have distinct purposes. Functions calculate. |
| Context | Explicit input and modules | Programs receive named JSON data and supplied pure source modules. |
| Dialect change | Language versions | New reserved names and portable migration are documented. |

Natural-language terminology provides useful design questions. Executable programs
also need a precise interpretation when the machine reaches a statement. ZenSigil
does not infer an action from arbitrary English, and its spelling conventions do
not establish that it is easier for people than another language. That usability
claim needs evidence beyond interpreter tests.

## A deliberate lexicon

`let` declares a fixed binding. `var` declares a binding which `set` may update.
The grammatical distinction makes change visible without altering the meaning of
existing let declarations. This follows the broader design principle of opting
into mutation explicitly, illustrated by the Rust book's discussion of
[variables and mutability](https://rust-lang.github.io/book/ch03-01-variables-and-mutability.html).

`when` introduces a statement branch; `otherwise` introduces its alternative.
`choose condition then yes otherwise no` is an expression that returns one value.
Only its selected branch evaluates. `??` has a narrow meaning: evaluate a fallback
only when the left value is null. It does not conceal a missing field.

`emit` produces structured JSON values. `say` produces a textual note. `propose`
records a reviewable action description. Reusable functions cannot perform these
effects. This makes the effectful parts of a program visible in its source.

`require` states an invariant. `test` collects isolated executable expectations.
Tests do not run the main program, and their fixtures live in their own lexical
blocks. Tests can exercise pure imported functions without supplying unrelated
main-program input data.

`fn name(...):` declares a named function with a statement body. `fn (...) =>
expression` produces a function value with one expression body. Keeping the same
word connects the two forms; the name and body delimiter identify their distinct
grammatical roles. Parameters are local names, while referenced outer bindings
are captured when the function value is created.

## Composition and ambiguity

Operator precedence and associativity determine how an unparenthesized expression
is read. ZenSigil documents that table and rejects chained comparisons. Explicit
parentheses remain available. Python's reference provides an example of a language
publishing [evaluation order and operator precedence](https://docs.python.org/3/reference/expressions.html).
ZenSigil's own rules, including its choice expression and null fallback, are in
[syntax-v04.md](syntax-v04.md), with anonymous functions and compositional
annotations added in [syntax-v05.md](syntax-v05.md). These are not a claim of
Python compatibility.

Named function references and anonymous closures compose through ordinary calls
and collection operations such as `map`, `filter`, `fold` and `group_by`. Both
can be passed and returned. Closures preserve an immutable snapshot of referenced
bindings at creation time: later rebinding does not change their meaning. Named
functions keep their existing isolation and get data through parameters, local
bindings, other declared functions and the standard library.

The anonymous function body extends through its full expression until an enclosing
delimiter. Parentheses identify the whole function value when calling or comparing
it immediately. In annotations, `list<T>` and `record<T>` describe contained
values, while `T | U` explicitly names alternatives. Brackets distinguish
`list<number | null>` from `list<number> | null`; both have one specified reading.

Imported modules use explicit root-relative source names and have a flat function
namespace. A function-name collision is an error. Imports never implicitly fetch
packages or execute module-level effects. Namespaces and selective exports remain
future designs rather than partially implemented syntax.

## A grammar with observable consequences

The parser constructs a custom syntax tree. The checker validates binding,
structural rules and purity. Runtime annotations check values when execution
reaches them; this is not a full static inference system. Diagnostics identify the
actual source and preserve bounded call frames.

Robert Nystrom's [Crafting Interpreters introduction](https://craftinginterpreters.com/introduction.html)
explains the importance of precise syntax and semantics; its
[collected grammar](https://craftinginterpreters.com/appendix-i.html) illustrates
making grammar explicit. Those are design references, not performance or adoption
claims about ZenSigil.

The [executable conformance corpus](../conformance/language.zs) checks representative
rules: grouping, strict equality, lazy branches, local state, function arguments,
Unicode slices, structural membership and exact decimal-text operations. Python
regressions cover failures, resource limits, module boundaries and transactional
output. A failed run discards values, notes and proposals together.

## Scope of this release

ZenSigil has dynamic JSON-compatible values, opaque function values, and optional
primitive, nested-container and union runtime annotations. Functions cannot be
serialized into JSON. Decimal helpers use canonical decimal strings and explicit operations;
there is no native decimal value type or implicit decimal coercion. Resource limits
are prototype guardrails, not a multi-tenant isolation boundary.

Mutable captured cells, module namespaces, generic static types, asynchronous I/O, threads,
network connectors, a package registry, an optimizing compiler and durable action
execution are future work. A good language needs coherent choices about these
areas; it does not need every possible paradigm in its first releases.

## Reference and visibility in 0.6

`use "path.zs" as name` gives a library a local name; the dot explicitly selects
a member. `export fn` marks the module's public vocabulary. A private helper's name
has meaning inside its defining source, so unrelated libraries can choose the
same word without ambiguity. Core grammar remains indentation-based and ASCII
identifiers remain case-sensitive; no natural-language inference changes meaning.
