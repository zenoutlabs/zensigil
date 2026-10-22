# ZenSigil

A small programming language for working with data and reviewing what should happen next.

I started ZenSigil because I wanted to build a language of my own. The goal is
simple: code that is easy to read, with results you can inspect. The first examples
came from stock review. The language itself is useful for other data tasks too.

```text
fn with_tax(price: number) -> number:
    return price * 1.08

let prices = [10, 25, 50]
emit map(prices, with_tax)

test "Tax on ten":
    require with_tax(10) == 10.8, "Expected 10.8."
```

This returns `[10.8, 27.0, 54.0]`. ZenSigil also has records, loops, closures,
modules, type annotations, and tests. For a workflow, `propose` creates an action
description for a person to review. It does not carry out that action.

The interpreter is written in Python. ZenSigil has its own syntax and execution
rules. Programs run on your computer without an AI service or an API key.

## Try it

You need Python 3.9 or later. No extra Python packages are needed to run the source.

```sh
git clone https://github.com/zenoutlabs/zensigil.git
cd zensigil
python3 -m zensigil serve --port 8766
```

Open [the local playground](http://127.0.0.1:8766). Choose an example and select
**Run preview**. Select **Run tests** to check its tests. You can edit, save, and
export programs from that page. Keep the terminal open while you use it.

Prefer a terminal? Start with a small project:

```sh
python3 -m zensigil init my-project
python3 -m zensigil run my-project
python3 -m zensigil test my-project --fail-if-empty
```

The [quickstart](docs/quickstart.md) walks through a useful data task. It includes
the files, commands, and expected result. It is a short reference, not a course.

## Where it stands

ZenSigil is a real language, and it is still experimental. Version 0.8 focuses on
sharing projects with their tests, clearer errors, and more reliable editor tools.
The [release notes](CHANGELOG.md) cover each change.

I am building this with AI assistance. The code and tests are public so other
people can inspect the work. Automated tests are useful evidence. They do not
replace feedback from developers who use the language on their own projects.

Before calling it stable, I want a clear compatibility promise and successful
outside use. The [stability plan](docs/stability.md) gives the conditions for that
change. Until then, syntax and behavior can change between releases.

A few limits matter now:

- Type annotations check values at runtime. Editor warnings catch some errors in advance.
- The interpreter limits program work and output size. It is not a security sandbox for untrusted tenants.
- Ordinary decimal numbers use floating-point arithmetic. Exact decimal-text helpers are available.
- There is no network access, action executor, package registry, or native compiler in the language.

## Use it and help improve it

Start with one small task. If setup fails, an error is unclear, or a result looks
wrong, [open an issue](https://github.com/zenoutlabs/zensigil/issues/new/choose).
Include a small program and the result you expected. That is more useful than a
large feature wish list.

- [Language reference](docs/language.md) and [standard functions](docs/stdlib.md)
- [Examples](examples) and [Python embedding example](examples/embed.py)
- [VS Code extension](editors/vscode/README.md)
- [Modules](docs/modules-v06.md), [portable projects and tests](docs/portable-tests-v08.md), and [command-line tools](docs/cli.md)
- [Compatibility](docs/compatibility.md) and [release evidence](docs/release-evidence-v08.md)
- [Contributing](CONTRIBUTING.md) and [MIT license](LICENSE)

Download source, a Python wheel, and the local VS Code package from
[GitHub releases](https://github.com/zenoutlabs/zensigil/releases).
They are not published to PyPI or the VS Code Marketplace.

## Work on ZenSigil

Run the interpreter tests from the project folder:

```sh
python3 -m unittest discover -s tests -v
```

To change the playground:

```sh
cd playground
npm ci
npm test
npm run build
```

The build updates the browser files included with the Python package.
See [the release guide](docs/releasing.md) for package and installation checks.
