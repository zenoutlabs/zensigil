"""Verify release hashes, ZIP integrity and bundled portable program behavior."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zensigil import __version__, run
from zensigil.programs import decode_program


def verify(directory):
    directory = Path(directory)
    manifest = directory / f"zensigil-{__version__}-SHA256SUMS.txt"
    entries = manifest.read_text(encoding="ascii").splitlines()
    for entry in entries:
        digest, name = entry.split("  ", 1)
        if Path(name).name != name:
            raise ValueError("Manifest filenames must not contain directories.")
        path = directory / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"Checksum mismatch: {name}")
        if name.endswith(".zip"):
            with zipfile.ZipFile(path) as archive:
                assert archive.testzip() is None
                names = archive.namelist()
                assert "zensigil/LICENSE" in names
                assert "zensigil/zensigil/web/index.html" in names
                assert not any("/node_modules/" in n or "/.git/" in n or "/__pycache__/" in n for n in names)
        if name.endswith(".sigil.json"):
            program = decode_program(path.read_text(encoding="utf-8"))
            result = run(program["source"], json.loads(program["data_text"]),
                         contract=json.loads(program["contract_text"]) if program["contract_text"] else None,
                         proposal_contract=json.loads(program["proposal_contract_text"]) if program["proposal_contract_text"] else None,
                         modules=program["modules"])
            assert result["ok"], result
            key = name.removesuffix(".sigil.json")
            fixture = json.loads((Path(__file__).resolve().parents[1] / "tests/fixtures/examples-expected.json").read_text())
            expected = fixture[key]
            assert result["values"] == expected.get("values", []), (key, result)
        if name.endswith(".vsix"):
            with zipfile.ZipFile(path) as archive:
                assert archive.testzip() is None
                metadata = json.loads(archive.read("extension/package.json"))
                assert metadata["publisher"] == "zenoutlabs"
                assert metadata["version"] == __version__
                assert "extension/extension.js" in archive.namelist()
                assert "extension/client.js" in archive.namelist()
    print(f"Verified {len(entries)} release checksums, ZIP contents and portable example runs.")


if __name__ == "__main__":
    verify(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2])
