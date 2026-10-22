"""Versioned portable documents. Validation preserves unfinished editor text."""
import json
import os
import tempfile
from pathlib import Path

from .jsonio import loads
from .modules import module_name, validate_modules
from .errors import SigilError

# ECMAScript trim whitespace keeps browser and Python document names consistent.
NAME_WHITESPACE = "\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
FORMAT = "zensigil-program"
LANGUAGE_VERSION = "0.8.0"
MAX_PROGRAM_BYTES = 10 * 1024 * 1024
TEXT_LIMITS = {"source": 65536, "data_text": 1048576,
               "contract_text": 262144, "proposal_contract_text": 262144}
REQUIRED = {"format", "format_version", "language_version", "name", "source",
            "data_text", "contract_text"}


def read_text(path, limit):
    with Path(path).open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"{path} exceeds the {limit}-byte file limit.")
    return raw.decode("utf-8")


def validate_source_maps(modules=None, tests=None):
    """Validate two source maps that share one root without combining their caps."""
    result = {}
    for field, value in (("modules", modules), ("tests", tests)):
        if value is not None and type(value) is not dict:
            raise ValueError(f"Program {field} must be an object of named source files.")
        try:
            result[field] = validate_modules({} if value is None else value)
        except SigilError as error:
            raise ValueError(f"Program {field}: {error.message}") from error
    for name, source in result["tests"].items():
        for module, body in result["modules"].items():
            left, right = name.casefold(), module.casefold()
            if name == module:
                if source != body:
                    raise ValueError("A shared module and test path must contain identical source text.")
            elif left == right or left.startswith(right + "/") or right.startswith(left + "/"):
                raise ValueError("Module and test paths must not conflict, including when ignoring letter case.")
    return result["modules"], result["tests"]


def validate_program(value):
    if type(value) is not dict or value.get("format") != FORMAT:
        raise ValueError("Expected a ZenSigil portable program (.sigil.json).")
    missing = REQUIRED - value.keys()
    extra = value.keys() - REQUIRED - {"proposal_contract_text", "modules", "tests", "entry_path"}
    if missing:
        raise ValueError("Program is missing fields: " + ", ".join(sorted(missing)) + ".")
    if extra:
        raise ValueError("Unknown program fields: " + ", ".join(sorted(extra)) + ".")
    if type(value["format_version"]) not in (int, float) or value["format_version"] != 1:
        raise ValueError("Unsupported program format version. Expected format 1.")
    if value["language_version"] not in ("0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0", LANGUAGE_VERSION):
        raise ValueError("Unsupported language version. Expected ZenSigil 0.2.0 through 0.8.0.")
    name = value["name"]
    if type(name) is not str or not name.strip(NAME_WHITESPACE):
        raise ValueError("Give your program a nonblank name before saving.")
    if len(name.encode("utf-16-le")) // 2 > 80:
        raise ValueError("Program name exceeds 80 characters (UTF-16 code units).")
    result = dict(value, format_version=1, language_version=LANGUAGE_VERSION)
    result.setdefault("proposal_contract_text", "")
    for field in ("modules", "tests"):
        if field in result and type(result[field]) is not dict:
            raise ValueError(f"Program {field} must be an object of named source files.")
    # Both maps share one project root when extracted. Exact duplicate files are
    # useful when an imported module is also an explicit project test entry.
    result["modules"], result["tests"] = validate_source_maps(result.get("modules"), result.get("tests"))
    if "entry_path" in result:
        try:
            entry = module_name(result["entry_path"])
        except SigilError as error:
            raise ValueError("Program entry_path: " + error.message) from error
        for name, body in {**result["modules"], **result["tests"]}.items():
            left, right = entry.casefold(), name.casefold()
            if entry == name:
                if value["source"] != body:
                    raise ValueError("The entry path must contain the same source text in all source maps.")
            elif left == right or left.startswith(right + "/") or right.startswith(left + "/"):
                raise ValueError("The entry path must not conflict with module or test paths.")
    for field, limit in TEXT_LIMITS.items():
        text = result[field]
        if type(text) is not str:
            raise ValueError(f"Program field {field} must be text.")
        if len(text.encode("utf-8")) > limit:
            raise ValueError(f"Program field {field} exceeds {limit} UTF-8 bytes.")
    return result


def decode_program(text):
    if len(text.encode("utf-8")) > MAX_PROGRAM_BYTES:
        raise ValueError("Portable program exceeds the 10 MiB file limit.")
    return validate_program(loads(text))


def encode_program(program):
    text = json.dumps(validate_program(program), indent=2, ensure_ascii=True) + "\n"
    if len(text.encode("utf-8")) > MAX_PROGRAM_BYTES:
        raise ValueError("Portable program exceeds the 10 MiB file limit after JSON encoding.")
    return text


def write_text(path, text, force=False):
    """Create by default; explicit force permits replacing a file."""
    path = Path(path)
    if not force:
        with path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(text)
        return
    # Finish a replacement before replacing the previous document.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                         dir=path.parent, prefix=".zensigil-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def unpack_program(program, directory):
    """A new directory prevents accidental replacement of an existing project."""
    program = validate_program(program)
    directory = Path(directory)
    paths = dict(program["modules"], **program["tests"])
    if any(name.casefold().startswith("zensigil.json/") for name in [*paths, program.get("entry_path", "")]):
        raise ValueError("Cannot unpack a source directory named zensigil.json; that name is reserved for the project manifest.")
    def available(name):
        existing = [key.casefold() for key in paths]
        while any(name.casefold() == other or other.startswith(name.casefold() + "/") for other in existing):
            name = "_" + name
        return name
    entry = program.get("entry_path") or available("program.zs")
    paths[entry] = program["source"]
    data = available("input.json")
    paths[data] = program["data_text"]
    manifest = {"format": "zensigil-project", "format_version": 1,
                "language_version": LANGUAGE_VERSION, "entry": entry,
                "tests": list(program["tests"]), "data": data}
    for field, filename, manifest_field in (("contract_text", "input.contract.json", "contract"),
                                            ("proposal_contract_text", "proposal.contract.json", "proposal_contract")):
        if program[field]:
            filename = available(filename)
            paths[filename] = program[field]
            # A blank embedded contract means no contract. Preserve its draft
            # text, but do not turn it into an invalid explicit file override.
            if program[field].strip():
                manifest[manifest_field] = filename
    paths["zensigil.json"] = json.dumps(manifest, indent=2) + "\n"
    directory.mkdir(parents=False, exist_ok=False)
    created_files, created_directories = [], [directory]
    try:
        for filename, text in paths.items():
            target = directory / filename
            for parent in reversed(target.parents):
                if parent != directory and parent.is_relative_to(directory) and not parent.exists():
                    parent.mkdir()
                    created_directories.append(parent)
            with target.open("x", encoding="utf-8", newline="") as handle:
                created_files.append(target)
                handle.write(text)
    except BaseException:
        # Remove only files created by this extraction, never unrelated contents.
        for target in reversed(created_files):
            try:
                target.unlink()
            except OSError:
                pass
        for folder in reversed(created_directories):
            try:
                folder.rmdir()
            except OSError:
                pass
        raise
    return list(paths)
