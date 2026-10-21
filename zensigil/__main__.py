"""Small command-line interface for local programs and portable documents."""
import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit
from . import __version__, check, run
from .jsonio import loads
from .errors import SigilError
from .contracts import MAX_CONTRACT_BYTES
from .programs import (FORMAT, LANGUAGE_VERSION, MAX_PROGRAM_BYTES, decode_program,
                       encode_program, read_text, unpack_program, write_text)

DEMO = Path(__file__).parent / "demo"
WEB = Path(__file__).parent / "web"


class CLIParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def separate_output(output, inputs):
    output_path = Path(output)
    for path in inputs:
        if not path:
            continue
        input_path = Path(path)
        same_spelling = input_path.resolve() == output_path.resolve()
        # Case aliases on macOS and hard links can share a file despite spelling.
        same_file = input_path.exists() and output_path.exists() and input_path.samefile(output_path)
        if same_spelling or same_file:
            raise ValueError("Output must be different from every input file.")


def read_stdin():
    stream = getattr(sys.stdin, "buffer", sys.stdin)
    value = stream.read(65537)
    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    if len(raw) > 65536:
        raise ValueError("Standard input source exceeds 64 KiB.")
    return raw.decode("utf-8")


def failure(code, error):
    entry = {"code": code, "message": str(error), "line": 1, "column": 1, "source_line": ""}
    if code == "E_CONTRACT":
        entry["data_path"] = "$"
    elif code == "E_PROPOSAL_CONTRACT":
        entry["output_path"] = "$"
    return {"ok": False, "version": __version__, "proposals": [], "notes": [], "values": [], "diagnostics": [entry]}


def json_object(text, label):
    value = loads(text)
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object.")
    return value


def example_names():
    return sorted(path.stem for path in DEMO.glob("*.zs"))


def example_program(name):
    if name not in example_names():
        raise ValueError(f"Unknown example {name!r}. Use 'zensigil examples' to list names.")
    data_path = DEMO / (name + ".json")
    contract_path = DEMO / (name + ".contract.json")
    proposal_path = DEMO / (name + ".proposal.json")
    modules_path = DEMO / (name + ".modules.json")
    program = {"format": FORMAT, "format_version": 1, "language_version": LANGUAGE_VERSION,
            "name": name, "source": read_text(DEMO / (name + ".zs"), 65536),
            "data_text": read_text(data_path, 1048576),
            "contract_text": read_text(contract_path, MAX_CONTRACT_BYTES) if contract_path.exists() else "",
            "proposal_contract_text": read_text(proposal_path, MAX_CONTRACT_BYTES) if proposal_path.exists() else ""}
    if modules_path.exists():
        program["modules"] = json_object(read_text(modules_path, MAX_PROGRAM_BYTES), "Example modules")
    return program


class _BundledAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []
        self.has_script = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script" and "src" in attributes:
            self.has_script = True
            self.paths.append(attributes["src"])
        elif tag == "link" and "stylesheet" in (attributes.get("rel") or "").lower().split():
            self.paths.append(attributes.get("href"))


def playground_resources_valid(web):
    """Check entry-point dependencies, including containment after symlink resolution."""
    try:
        root = Path(web).resolve()
        parser = _BundledAssets()
        parser.feed(read_text(root / "index.html", 1048576))
        parser.close()
        if not parser.has_script:
            return False
        for reference in parser.paths:
            if not reference:
                return False
            url = urlsplit(reference)
            if url.scheme or url.netloc or not url.path:
                return False
            path = (root / unquote(url.path).lstrip("/")).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                return False
        return True
    except (OSError, ValueError, RecursionError):
        return False


def doctor():
    from .server import CATALOG
    preview = run('say "ZenSigil is ready"\n', {})
    names = example_names()
    expected_names = {entry[0] for entry in CATALOG} | set(names)
    checks = {"interpreter": bool(preview.get("ok") and preview.get("notes") and preview["notes"][0].get("message") == "ZenSigil is ready"),
              "playground": playground_resources_valid(WEB),
              "examples": bool(expected_names) and all(
                  (DEMO / (name + ".zs")).is_file() and (DEMO / (name + ".json")).is_file()
                  for name in expected_names)}
    return {"ok": all(checks.values()), "version": __version__, "python": sys.version.split()[0],
            "checks": checks, "example_count": len(names)}


def add_inputs(command):
    command.add_argument("--data", help="Input JSON object; overrides a portable program's input")
    command.add_argument("--contract", help="Input contract JSON; overrides an embedded input contract")
    command.add_argument("--proposal-contract", help="Proposal contract JSON; overrides an embedded proposal contract")


def parser_for_cli():
    parser = CLIParser(prog="zensigil", description="Check, preview, and share ZenSigil programs locally.")
    parser.add_argument("--version", action="version", version=f"ZenSigil {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "run", "test", "lint"):
        command = commands.add_parser(name)
        command.add_argument("source", help="A .zs source, .sigil.json program, or project directory")
        command.add_argument("--module-root", help="Explicit root for relative source module imports")
        add_inputs(command)
        command.add_argument("--json", action="store_true", help="Print machine-readable output")
        if name == "lint":
            command.add_argument("--strict", action="store_true", help="Return failure for advisory warnings")
        if name == "test":
            command.add_argument("--filter", help="Run test names containing this case-sensitive text")
            command.add_argument("--list", action="store_true", help="List selected tests without executing")
            command.add_argument("--fail-if-empty", action="store_true", help="Fail when no tests are selected")
            command.add_argument("--junit", help="Write a JUnit XML report to a new file; never replaces an existing file")
        if name == "run":
            command.add_argument("--output", help="Save the complete result JSON to a new file")
            command.add_argument("--force", action="store_true", help="Allow replacing --output")
    formatting = commands.add_parser("fmt", help="Format valid .zs source, preserving comments")
    formatting.add_argument("source")
    formatting_mode = formatting.add_mutually_exclusive_group()
    formatting_mode.add_argument("--check", action="store_true", help="Exit 1 if formatting would change the file")
    formatting_mode.add_argument("--write", action="store_true", help="Atomically replace the source file")
    ast_command = commands.add_parser("ast", help="Print a versioned JSON syntax tree without executing")
    ast_command.add_argument("source")
    ast_command.add_argument("--json", action="store_true", help="Print machine-readable output (the default)")
    initialize = commands.add_parser("init", help="Create a new project directory with a module and tests")
    initialize.add_argument("directory")
    pack = commands.add_parser("pack", help="Bundle source and raw input into a portable program")
    pack.add_argument("source", help="Path to a .zs source")
    add_inputs(pack)
    pack.add_argument("--module-root", help="Explicit root for bundling relative source module imports")
    pack.add_argument("--name", required=True)
    pack.add_argument("--output", required=True)
    pack.add_argument("--force", action="store_true")
    unpack = commands.add_parser("unpack", help="Extract a portable program to a new directory")
    unpack.add_argument("source")
    unpack.add_argument("--output", required=True, help="A directory that does not exist yet")
    examples = commands.add_parser("examples", help="List bundled examples")
    examples.add_argument("--json", action="store_true")
    example = commands.add_parser("example", help="Copy a bundled example into a new directory")
    example.add_argument("name")
    example.add_argument("--output", required=True)
    health = commands.add_parser("doctor", help="Verify the interpreter and bundled resources")
    health.add_argument("--json", action="store_true")
    commands.add_parser("lsp", help="Serve the editor protocol over standard input/output")
    repl = commands.add_parser("repl", help="Explore programs in a bounded transactional session")
    repl.add_argument("--data", help="Explicit input JSON object for this session")
    repl.add_argument("--modules", help="Explicit JSON object mapping module paths to source text")
    serve = commands.add_parser("serve", help="Open the local playground server")
    serve.add_argument("--port", type=int, default=8765)
    return parser


def render(result, args, data=None):
    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, ensure_ascii=True))
    elif not result["ok"]:
        for error in result["diagnostics"]:
            path = error.get("data_path", error.get("output_path"))
            location = f" {path}" if path else ""
            filename = error.get("source_file", error.get("source_name"))
            if filename in (None, "", "<program>"):
                filename = error.get("project_source", getattr(args, "source", args.command))
            print(f"{filename}:{error['line']}:{error['column']} {error['code']}{location}: {error['message']}", file=sys.stderr)
            if error.get("source_line"):
                print(f"  {error['source_line']}\n  {' ' * (error['column'] - 1)}^", file=sys.stderr)
            for frame in error.get("call_trace", []):
                print(f"  called {frame['function']} at {frame.get('source_file', frame.get('source_name', '<program>'))}:{frame['line']}:{frame['column']}", file=sys.stderr)
        if args.command == "test":
            print(f"Test check failed · {result.get('passed', 0)} passed · {result.get('failed', 0)} failed.", file=sys.stderr)
        else:
            print("No proposals produced.", file=sys.stderr)
    elif args.command == "lint":
        for warning in result.get("warnings", []):
            print(f"{warning.get('source_name', args.source)}:{warning['line']}:{warning['column']} {warning['code']}: {warning['message']}")
        print(f"Lint complete: {len(result.get('warnings', []))} advisory warning(s).")
    elif args.command == "check":
        print("Check passed: syntax and bindings are valid.")
        if data is None:
            print("Input names were not verified. Add --data to check them.")
            if result["possible_inputs"]:
                print("Possible inputs: " + ", ".join(result["possible_inputs"]))
    elif args.command == "test":
        if getattr(args, "list", False):
            for case in result.get("tests", []):
                print(case["name"])
            return 0 if result["ok"] else 1
        print(f"ZenSigil tests · {result.get('passed', 0)} passed · {result.get('failed', 0)} failed · {result.get('total', 0)} total")
    elif args.command == "run":
        for value in result.get("values", []):
            print("  VALUE  " + json.dumps(value, ensure_ascii=True))
        print(f"ZenSigil preview · {len(result['proposals'])} proposal(s) · {len(result['notes'])} note(s)")
        for proposal in result["proposals"]:
            print(f"  REVIEW {proposal['action']} {json.dumps(proposal['fields'], sort_keys=True)}")
        for note in result["notes"]:
            print(f"  NOTE   {note['message']}")
        if result["stats"]["duplicates_collapsed"]:
            print(f"  Collapsed {result['stats']['duplicates_collapsed']} duplicate proposal(s) in this preview.")
        print("Nothing was sent or purchased.")
    return 0 if result["ok"] else 1


def main(argv=None):
    parser = parser_for_cli()
    args = parser.parse_args(argv)
    if getattr(args, "force", False) and not getattr(args, "output", None):
        parser.error("--force requires --output")
    if args.command == "test" and args.list and args.junit:
        parser.error("--junit requires execution; it cannot be combined with --list")
    if args.command == "repl":
        from .repl import main as repl_main
        from .modules import validate_modules
        try:
            data = json_object(read_text(args.data, 1048576), "Input data") if args.data else None
            modules = validate_modules(json_object(read_text(args.modules, MAX_PROGRAM_BYTES), "Modules")) if args.modules else None
            return repl_main(data=data, modules=modules)
        except (OSError, ValueError, SigilError, RecursionError) as error:
            print(f"Cannot start REPL: {error}", file=sys.stderr)
            return 1
    if args.command == "lsp":
        from .lsp import main as lsp_main
        return lsp_main()
    if args.command == "serve":
        from .server import serve as serve_app
        try:
            serve_app(args.port)
        except (OSError, ValueError) as error:
            print(f"Cannot start playground: {error}", file=sys.stderr)
            return 1
        return 0
    if args.command == "examples":
        names = example_names()
        print(json.dumps(names) if args.json else "Bundled examples:\n" + "\n".join("  " + name for name in names))
        return 0
    if args.command == "doctor":
        result = doctor()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"ZenSigil {result['version']} · Python {result['python']}")
            for label, ok in result["checks"].items():
                print(f"  {'PASS' if ok else 'FAIL'} {label}")
        return 0 if result["ok"] else 1
    if args.command in {"fmt", "ast", "init"}:
        source = ""
        try:
            if args.command == "init":
                from .projects import init_project
                files = init_project(args.directory)
                print(f"Created {args.directory} with " + ", ".join(files) + ".")
                return 0
            if args.command == "fmt" and Path(args.source).is_dir():
                if not (args.check or args.write):
                    raise ValueError("Project formatting requires --check or --write.")
                from .project_tools import format_project
                report = format_project(args.source, write=args.write)
                for name in report["changed"]:
                    print(name)
                print(f"Checked {report['files']} files; {len(report['changed'])} {'formatted' if args.write else 'need formatting'}.")
                return 1 if args.check and report["changed"] else 0
            if args.source == "-":
                if args.command == "fmt" and args.write:
                    raise ValueError("Cannot format standard input in place.")
                source = read_stdin()
            elif Path(args.source).suffix != ".zs":
                raise ValueError(f"{args.command} accepts a .zs source file.")
            else:
                source = read_text(args.source, 65536)
            if args.command == "ast":
                from .astio import ast_document
                print(json.dumps(ast_document(source), indent=2, ensure_ascii=True))
                return 0
            from .formatter import format_source, write_formatted
            formatted = format_source(source)
            if args.check:
                if source != formatted:
                    print(f"{args.source}: formatting would change this file.", file=sys.stderr)
                    return 1
                return 0
            if args.write:
                write_formatted(args.source, formatted)
            else:
                print(formatted, end="")
            return 0
        except SigilError as error:
            result = failure(error.code, error.message)
            result["diagnostics"] = [error.as_dict(source)]
        except (OSError, ValueError, RecursionError) as error:
            result = failure("E_PROJECT" if args.command == "init" else "E_FORMAT" if args.command == "fmt" else "E_INPUT", error)
        return render(result, args)
    error_code = "E_PROGRAM" if args.command in ("pack", "unpack", "example") else "E_INPUT"
    data = None
    module_paths = []
    discovering_modules = False
    project = None
    project_root_candidate = None
    portable = False
    source = ""
    try:
        if args.command == "pack":
            source = read_text(args.source, 65536)
            # Ordinary unfinished drafts remain packable. Imports require a valid
            # syntax tree to discover their explicit dependency graph safely.
            modules = {}
            if re.search(r"(?m)^[ \t]*use(?:[ \t]|$)", source):
                from .modules import file_modules
                module_root = Path(args.module_root).resolve() if args.module_root else Path(args.source).parent.resolve()
                modules = file_modules(source, args.source, root=module_root)
                module_paths = [module_root / name for name in modules]
            program = {"format": FORMAT, "format_version": 1, "language_version": LANGUAGE_VERSION,
                       "name": args.name, "source": source,
                       "data_text": read_text(args.data, 1048576) if args.data else "{}",
                       "contract_text": read_text(args.contract, MAX_CONTRACT_BYTES) if args.contract else "",
                       "proposal_contract_text": read_text(args.proposal_contract, MAX_CONTRACT_BYTES) if args.proposal_contract else ""}
            if modules:
                program["modules"] = modules
            text = encode_program(program)
            error_code = "E_OUTPUT"
            separate_output(args.output, [args.source, args.data, args.contract, args.proposal_contract] + module_paths)
            write_text(args.output, text, args.force)
            print(f"Saved portable program: {args.output}\nDraft text preserved. Run 'zensigil check' to validate it.")
            return 0
        if args.command in ("unpack", "example"):
            program = (example_program(args.name) if args.command == "example" else
                       decode_program(read_text(args.source, MAX_PROGRAM_BYTES)))
            error_code = "E_OUTPUT"
            files = unpack_program(program, args.output)
            print(f"Created {args.output} with " + ", ".join(files) + ".")
            return 0
        project = None
        source_path = Path(args.source)
        if source_path.is_dir():
            project_root_candidate = source_path.resolve()
            error_code = "E_PROJECT"
            from .projects import load_project
            project = load_project(source_path)
            source_path = project["entry"]
        portable = str(source_path).endswith(".sigil.json")
        if portable:
            error_code = "E_PROGRAM"
            program = decode_program(read_text(source_path, MAX_PROGRAM_BYTES))
            source = program["source"]
        else:
            source = read_stdin() if args.source == "-" else read_text(source_path, 65536)
            program = {}
        error_code = "E_INPUT"
        data_text = read_text(args.data, 1048576) if args.data else program.get("data_text")
        if data_text is not None:
            data = json_object(data_text, "Input data")
        contracts = {}
        for flag, field, code, label in (
            ("contract", "contract_text", "E_CONTRACT", "Input contract"),
            ("proposal_contract", "proposal_contract_text", "E_PROPOSAL_CONTRACT", "Proposal contract")):
            error_code = code
            path = getattr(args, flag)
            text = read_text(path, MAX_CONTRACT_BYTES) if path else program.get(field, "")
            # An explicit empty file is an invalid override, not an absent contract.
            contracts[flag] = json_object(text, label) if path or text.strip() else None
        from .modules import file_modules
        module_root = Path(args.module_root).resolve() if args.module_root else project["root"] if project else source_path.parent.resolve()
        discovering_modules = not portable
        if args.source == "-" and not args.module_root:
            modules = {}  # stdin never discovers files without an explicit module root
        else:
            if args.source == "-":
                source_path = module_root / "stdin.zs"
            modules = program.get("modules", {}) if portable else file_modules(source, source_path, root=module_root)
        discovering_modules = False
        if not portable:
            module_paths = [module_root / name for name in modules]
        if args.command in {"test", "lint"}:
            from . import test as test_program
            from .lint import lint
            sources = [(source_path, source, modules)]
            if project:
                sources += [(path, read_text(path, 65536), None) for path in project["tests"] if path != source_path]
            results = []
            for path, text, provided_modules in sources:
                loaded = provided_modules if provided_modules is not None else file_modules(text, path, root=module_root)
                tested = (lint(text, data, modules=loaded, **contracts) if args.command == "lint" else
                          test_program(text, data, modules=loaded, name_filter=args.filter,
                                       list_only=args.list, **contracts))
                results.append(tested)
            result = {"ok": all(item["ok"] for item in results), "version": __version__,
                      "total": sum(item.get("total", 0) for item in results),
                      "passed": sum(item.get("passed", 0) for item in results),
                      "failed": sum(item.get("failed", 0) for item in results),
                      "tests": [dict(case, source_file=str(path)) for (path, _, _), item in zip(sources, results) for case in item.get("tests", [])],
                      "stats": {"steps": sum(item.get("stats", {}).get("steps", 0) for item in results),
                                "passed": sum(item.get("passed", 0) for item in results),
                                "failed": sum(item.get("failed", 0) for item in results)},
                      "diagnostics": [dict(entry, project_source=str(path)) for (path, _, _), item in zip(sources, results) for entry in item.get("diagnostics", [])],
                      "proposals": [], "notes": [], "values": [], "mode": "test"}
            if args.command == "lint":
                advisories = [dict(warning, source_name=(str(path) if warning.get("source_name") == "<program>" else warning.get("source_name")))
                              for (path, _, _), item in zip(sources, results) for warning in item.get("warnings", [])]
                unique = {(w["source_name"], w["line"], w["column"], w["code"]): w for w in advisories}
                result.update(mode="lint", warnings=list(unique.values()))
                if args.strict and result["warnings"]:
                    result["ok"] = False
                    result["diagnostics"] += result["warnings"]
            elif args.fail_if_empty and result["ok"] and result["total"] == 0:
                result["ok"] = False
                result["diagnostics"] = failure("E_TEST_EMPTY", "No tests match the selection.")["diagnostics"]
            if args.command == "test" and args.list:
                result["listed"] = True
        else:
            result = (check if args.command == "check" else run)(source, data, modules=modules, **contracts)
    except SigilError as error:
        result = failure(error.code, error.message)
        error_source = source
        name = getattr(error, "source_name", "")
        if name and name != "<program>" and 'module_root' in locals():
            try:
                from .modules import module_name
                module_name(name)
                path = (module_root / name).resolve()
                if path.is_relative_to(module_root):
                    error_source = read_text(path, 65536)
            except (OSError, ValueError, SigilError):
                error_source = ""
        result["diagnostics"] = [error.as_dict(error_source)]
    except (OSError, ValueError, RecursionError) as error:
        result = failure(error_code, error)
    if args.command == "run" and args.output:
        try:
            # Input/contract decoding may have failed before discovering imports.
            # Protect dependencies even when writing a diagnostic result.
            if (project_root_candidate is not None and project is None and Path(args.output).exists()
                    and Path(args.output).resolve().is_relative_to(project_root_candidate)):
                raise ValueError("Cannot replace an existing file in a project whose manifest could not be loaded.")
            if (args.source == "-" and not args.module_root and Path(args.output).exists()
                    and re.search(r"(?m)^[ \t]*use(?:[ \t]|$)", source)
                    and Path(args.output).resolve().is_relative_to(Path.cwd())):
                raise ValueError("Provide --module-root before replacing existing output for stdin with imports.")
            if (Path(args.output).exists() and source and not portable
                    and not (args.source == "-" and not args.module_root)
                    and not module_paths and re.search(r"(?m)^[ \t]*use(?:[ \t]|$)", source)):
                from .modules import file_modules
                module_root = Path(args.module_root).resolve() if args.module_root else project["root"] if project else source_path.parent.resolve()
                discovering_modules = True
                try:
                    protected_modules = file_modules(source, source_path, root=module_root)
                    module_paths = [module_root / name for name in protected_modules]
                    discovering_modules = False
                except (SigilError, OSError, ValueError):
                    pass
            if discovering_modules and Path(args.output).exists() and Path(args.output).resolve().is_relative_to(module_root):
                raise ValueError("Cannot replace an existing file inside the module root after module discovery failed.")
            source_paths = [args.source, args.data, args.contract, args.proposal_contract] + module_paths
            if project:
                source_paths += [project["entry"], project["root"] / "zensigil.json"] + project["tests"]
            separate_output(args.output, source_paths)
            write_text(args.output, json.dumps(result, indent=2, ensure_ascii=True) + "\n", args.force)
        except (OSError, ValueError) as error:
            result = failure("E_OUTPUT", error)
    if args.command == "test" and args.junit:
        try:
            from .reports import junit_xml
            protected = [args.source, args.data, args.contract, args.proposal_contract] + module_paths
            if project:
                protected += [project["entry"], project["root"] / "zensigil.json"] + project["tests"]
            separate_output(args.junit, protected)
            write_text(args.junit, junit_xml(result), False)
        except (OSError, ValueError, RecursionError, RuntimeError) as error:
            result = failure("E_OUTPUT", error)
    return render(result, args, data)


if __name__ == "__main__":
    raise SystemExit(main())
