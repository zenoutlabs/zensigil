# Introducing ZenSigil

ZenSigil is an experimental programming language built around readable code,
explicit data checks, and instructions people can inspect. Its core includes
values, collection transformations, typed function signatures, local mutable state,
conditions, loops, pure modules and executable tests. The language includes anonymous
functions with immutable captured bindings, nested list/record and union runtime
annotations, namespaced imports with explicit exports, and 69 standard functions.
Programs can calculate results, write notes and describe proposed actions for review.

The aim is a language that anyone can learn, adopt and help improve. Stock review
is its first developed practical example. Reading lists, event capacity, project budgets, support triage and general programming
examples demonstrate that industry-specific concepts are not built into its grammar.

The implementation includes a standalone parser/interpreter, CLI, browser
playground, generic input and proposal contracts, portable CLI programs,
formatting and lint tools, a transactional interactive shell, JUnit test reports,
a language server with a VS Code client, and regression tests.
The core runs locally using Python's standard library and needs no AI service.
AI assistance is part of the project's development process.

## A short description you can use

> Creator of ZenSigil, an experimental programming language focused on readable
> programs and explicit intent. Building its interpreter, tooling and examples
> with AI assistance.

For a website project entry:

> **ZenSigil — a programming language I'm building.** A readable language with
> functions, closures, collections, input contracts and reviewable proposals. Includes a
> working interpreter, local playground, editor tooling and portable program files. Early examples
> span stock review, support triage and general programming. Released under MIT.

These descriptions distinguish current implementation from long-term ambition.
Claims of broad adoption, an established ecosystem, production readiness or proven
superiority need evidence that the project has not yet gathered.

## Public source

This source package includes the MIT license, contributor guidance, example
programs, reference documentation and GitHub CI configuration. The package is
available at the experimental public repository [zenoutlabs/zensigil](https://github.com/zenoutlabs/zensigil).
Third-party UI notices must remain included.

Source preparation does not itself establish publication. Check the current
release evidence for the verified repository and release status. Package-registry
publication, a website entry and social posts are separate distribution steps.

For a first announcement, link the repository, working examples and known limits.
Ask for a focused review of contracts, scoping or diagnostics. For language hubs,
check each hub's current submission criteria after the public repository exists.
No claim about name, domain, package-name or trademark availability is made here.

## Current adoption tools

Version 0.8 includes project tests in portable files and restores projects on
unpack. It adds editor reference search, refresh, and restart. Version 0.7 added
project input settings and advisory checks for known type errors. The editor and playground show these warnings.
The checks do not execute source or prove that a program will run correctly.
Use the [quickstart](quickstart.md) to run one useful task and share the result.
The [release evidence](release-evidence-v08.md) separates demonstrated behavior from open gaps.

## Where the project goes next

The next adoption milestone should let a developer outside this project install
ZenSigil, write one useful program, save/share it and report a specific problem.
Then prioritize the barriers they encounter: documentation, packaging, richer
type checking, parser recovery or deeper editor integration. The current
language server supports a declared subset of editor operations; see
[the editor reference](editor-v05.md). Static inference, mutable captured cells,
a stepping debugger and a package registry remain future designs. Keep business connectors in libraries
and execution services, with their own contracts and reliability guarantees.
