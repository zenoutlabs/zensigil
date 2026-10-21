"""Small explicit project manifests and non-overwriting project scaffolding."""
from pathlib import Path, PurePosixPath
from .jsonio import loads
from .programs import read_text

PROJECT_VERSION = "0.6.0"
MAX_MANIFEST_BYTES = 16384


def project_path(root, value):
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("Project paths must be nonempty relative .zs paths using '/'.")
    logical = PurePosixPath(value)
    if logical.is_absolute() or any(part in {".", "..", ""} for part in value.split("/")) or logical.suffix != ".zs" or ":" in value:
        raise ValueError("Project paths must stay inside the project and end in .zs.")
    root = Path(root).resolve()
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Project source escapes its root directory.")
    return path


def load_project(directory):
    root = Path(directory).resolve()
    if not root.is_dir():
        raise ValueError("A ZenSigil project must be a directory.")
    manifest = root / "zensigil.json"
    if not manifest.resolve().is_relative_to(root):
        raise ValueError("Project manifest escapes its root directory.")
    value = loads(read_text(manifest, MAX_MANIFEST_BYTES))
    required = {"format", "format_version", "language_version", "entry"}
    if type(value) is not dict or not required <= value.keys() or set(value) - required - {"tests"}:
        raise ValueError("Project manifest needs format, format_version, language_version and entry; only tests is optional.")
    if value["format"] != "zensigil-project" or type(value["format_version"]) is not int or value["format_version"] != 1:
        raise ValueError("Unsupported ZenSigil project format or format_version.")
    if value["language_version"] not in {"0.4.0", "0.5.0", PROJECT_VERSION}:
        raise ValueError(f"Project language_version must be 0.4.0, 0.5.0 or {PROJECT_VERSION}.")
    entry = project_path(root, value["entry"])
    tests = value.get("tests", [])
    if type(tests) is not list or len(tests) > 32 or any(type(item) is not str for item in tests) or len(set(tests)) != len(tests):
        raise ValueError("Project tests must be a unique list of at most 32 relative .zs paths.")
    return {"root": root, "entry": entry, "tests": [project_path(root, item) for item in tests]}


def init_project(directory):
    """Create a new directory exclusively; never adopt or overwrite existing files."""
    import json
    root = Path(directory)
    root.mkdir(parents=False, exist_ok=False)
    files = {
        "zensigil.json": json.dumps({"format": "zensigil-project", "format_version": 1,
                                   "language_version": PROJECT_VERSION, "entry": "main.zs", "tests": ["tests.zs"]}, indent=2) + "\n",
        "main.zs": 'use "lib/math.zs"\n\n# A project can compute and emit ordinary values.\nemit {greeting: "Hello from ZenSigil", answer: double(21)}\n',
        "lib/math.zs": 'fn double(value: number) -> number:\n    return value * 2\n',
        "tests.zs": 'use "lib/math.zs"\n\ntest "Double a number":\n    require double(21) == 42, "Expected 42."\n\ntest "Double zero":\n    require double(0) == 0, "Zero stays zero."\n',
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
