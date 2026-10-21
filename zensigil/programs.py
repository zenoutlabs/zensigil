"""Versioned portable documents. Validation preserves unfinished editor text."""
import json
import os
import tempfile
from pathlib import Path

from .jsonio import loads
from .modules import validate_modules
from .errors import SigilError

# ECMAScript trim whitespace keeps browser and Python document names consistent.
NAME_WHITESPACE = "\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
FORMAT = "zensigil-program"
LANGUAGE_VERSION = "0.6.0"
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


def validate_program(value):
    if type(value) is not dict or value.get("format") != FORMAT:
        raise ValueError("Expected a ZenSigil portable program (.sigil.json).")
    missing = REQUIRED - value.keys()
    extra = value.keys() - REQUIRED - {"proposal_contract_text", "modules"}
    if missing:
        raise ValueError("Program is missing fields: " + ", ".join(sorted(missing)) + ".")
    if extra:
        raise ValueError("Unknown program fields: " + ", ".join(sorted(extra)) + ".")
    if type(value["format_version"]) not in (int, float) or value["format_version"] != 1:
        raise ValueError("Unsupported program format version. Expected format 1.")
    if value["language_version"] not in ("0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0"):
        raise ValueError("Unsupported language version. Expected ZenSigil 0.2.0, 0.3.0, 0.4.0, 0.5.0 or 0.6.0.")
    name = value["name"]
    if type(name) is not str or not name.strip(NAME_WHITESPACE):
        raise ValueError("Give your program a nonblank name before saving.")
    if len(name.encode("utf-16-le")) // 2 > 80:
        raise ValueError("Program name exceeds 80 characters (UTF-16 code units).")
    result = dict(value, format_version=1, language_version=LANGUAGE_VERSION)
    result.setdefault("proposal_contract_text", "")
    if "modules" in result and type(result["modules"]) is not dict:
        raise ValueError("Program modules must be an object of named source files.")
    try:
        result["modules"] = validate_modules(result.get("modules", {}))
    except SigilError as error:
        raise ValueError(error.message) from error
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
    return json.dumps(validate_program(program), indent=2, ensure_ascii=True) + "\n"


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
    paths = dict(program["modules"])
    def available(name):
        existing = [key.casefold() for key in paths]
        while any(name.casefold() == other or other.startswith(name.casefold() + "/") for other in existing):
            name = "_" + name
        return name
    paths[available("program.zs")] = program["source"]
    paths[available("input.json")] = program["data_text"]
    for field, filename in (("contract_text", "input.contract.json"),
                            ("proposal_contract_text", "proposal.contract.json")):
        if program[field]:
            paths[available(filename)] = program[field]
    directory.mkdir(parents=False, exist_ok=False)
    for filename, text in paths.items():
        target = directory / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        write_text(target, text)
    return list(paths)
