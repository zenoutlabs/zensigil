"""Small explicit project manifests and non-overwriting project scaffolding."""
from pathlib import Path, PurePosixPath
from .jsonio import loads
from .programs import read_text

PROJECT_VERSION = "0.7.0"
MAX_MANIFEST_BYTES = 16384
INPUT_FIELDS = ("data", "contract", "proposal_contract")


def project_path(root, value, suffix=".zs"):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError(f"Project paths must be nonempty relative {suffix} paths using '/'.")
    logical = PurePosixPath(value)
    if logical.is_absolute() or any(part in {".", "..", ""} for part in value.split("/")) or logical.suffix != suffix or ":" in value:
        raise ValueError(f"Project paths must stay inside the project and end in {suffix}.")
    try:
        root = Path(root).resolve()
        path = (root / value).resolve()
    except (OSError, RuntimeError) as error:
        raise ValueError("Project paths must resolve without symbolic link loops.") from error
    if not path.is_relative_to(root):
        raise ValueError("Project source escapes its root directory.")
    return path


def load_project(directory):
    try:
        root = Path(directory).resolve()
        manifest = root / "zensigil.json"
        resolved_manifest = manifest.resolve()
    except (OSError, RuntimeError) as error:
        raise ValueError("The project and its manifest must resolve without symbolic link loops.") from error
    if not root.is_dir():
        raise ValueError("A ZenSigil project must be a directory.")
    if not resolved_manifest.is_relative_to(root):
        raise ValueError("Project manifest escapes its root directory.")
    value = loads(read_text(manifest, MAX_MANIFEST_BYTES))
    required = {"format", "format_version", "language_version", "entry"}
    if type(value) is not dict or not required <= value.keys() or set(value) - required - {"tests", *INPUT_FIELDS}:
        raise ValueError("Project manifest needs format, format_version, language_version and entry; tests, data, contract and proposal_contract are optional.")
    if value["format"] != "zensigil-project" or type(value["format_version"]) is not int or value["format_version"] != 1:
        raise ValueError("Unsupported ZenSigil project format or format_version.")
    if type(value["language_version"]) is not str or value["language_version"] not in {"0.4.0", "0.5.0", "0.6.0", PROJECT_VERSION}:
        raise ValueError(f"Project language_version must be 0.4.0, 0.5.0, 0.6.0 or {PROJECT_VERSION}.")
    entry = project_path(root, value["entry"])
    tests = value.get("tests", [])
    if type(tests) is not list or len(tests) > 32 or any(type(item) is not str for item in tests) or len(set(tests)) != len(tests):
        raise ValueError("Project tests must be a unique list of at most 32 relative .zs paths.")
    inputs = {field: project_path(root, value[field], ".json") if field in value else None
              for field in INPUT_FIELDS}
    return {"root": root, "entry": entry, "tests": [project_path(root, item) for item in tests], **inputs}


def init_project(directory):
    """Create a new directory exclusively; never adopt or overwrite existing files."""
    import json
    root = Path(directory)
    root.mkdir(parents=False, exist_ok=False)
    files = {
        "zensigil.json": json.dumps({"format": "zensigil-project", "format_version": 1,
                                   "language_version": PROJECT_VERSION, "entry": "main.zs", "tests": ["tests.zs"]}, indent=2) + "\n",
        "main.zs": 'use "lib/math.zs" as math\n\n# A project can compute and emit ordinary values.\nemit {greeting: "Hello from ZenSigil", answer: math.double(21)}\n',
        "lib/math.zs": 'export fn double(value: number) -> number:\n    return value * 2\n',
        "tests.zs": 'use "lib/math.zs" as math\n\ntest "Double a number":\n    require math.double(21) == 42, "Expected 42."\n\ntest "Double zero":\n    require math.double(0) == 0, "Zero stays zero."\n',
        ".gitignore": ".venv/\n__pycache__/\n*.py[cod]\n",
        "README.md": '''# Your ZenSigil project

Run these commands from this folder with the Python that has ZenSigil installed:

```sh
python -m zensigil check . --json
python -m zensigil run . --json
python -m zensigil test . --fail-if-empty --json
python -m zensigil lint . --strict
python -m zensigil fmt . --check
python -m zensigil pack . --name "My project" --output ../my-project.sigil.json
```

Use `python3` if that is the name of your Python command.
On Windows, you can use `py` instead.
The run result has `ok: true`. Its `values` list contains:

```json
[{"greeting": "Hello from ZenSigil", "answer": 42}]
```

The two tests must pass. Change `21` to `10` in `main.zs`.
The next run must show `answer: 20`.
`lib/math.zs` defines the public `double` function.
`tests.zs` checks that function. Tests do not run the main program.

To use input data, save a JSON object as `input.json`.
Add `"data": "input.json"` to `zensigil.json`.
Use `contract` and `proposal_contract` for optional JSON contract files.
These paths start at this folder. Command flags override each chosen file.
`pack .` includes the chosen input, contracts, and imported modules.
It does not include separate test files.

Keep real secrets out of files that you share.
ZenSigil is experimental. Proposed actions are data; they do not run outside actions.
''',
    }
    created = []
    try:
        (root / "lib").mkdir()
        for name, text in files.items():
            with (root / name).open("x", encoding="utf-8", newline="\n") as stream:
                created.append(root / name)
                stream.write(text)
    except BaseException:
        # Remove only names this initializer owns; do not recurse into other data.
        for path in reversed(created):
            if path.is_file() and not path.is_symlink():
                path.unlink()
        try:
            (root / "lib").rmdir()
            root.rmdir()
        except OSError:
            pass
        raise
    return list(files)
