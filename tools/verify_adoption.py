"""Run the exact quickstart files with an installed wheel, outside the source tree.

Usage: /path/to/venv/python -I tools/verify_adoption.py
The JSON report records commands and expected results. No network is used here.
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import zensigil


def verify():
    root = Path(__file__).resolve().parents[1]
    installed = Path(zensigil.__file__).resolve()
    if installed.is_relative_to(root):
        raise RuntimeError("Run this check with the installed wheel in an isolated environment.")
    guide = (root / "docs" / "quickstart.md").read_text(encoding="utf-8")
    files = dict(re.findall(r"<!-- file:([^ >]+) -->\s*```[^\n]*\n(.*?)```", guide, re.S))
    expected_files = {"zensigil.json", "input.json", "input.contract.json", "main.zs",
                      "tests.zs", "lib/statistics.zs"}
    assert set(files) == expected_files, files.keys()
    commands = []
    with tempfile.TemporaryDirectory(prefix="zensigil-adoption-") as temporary:
        directory = Path(temporary)

        def cli(*args, expected_exit=0):
            result = subprocess.run([sys.executable, "-I", "-m", "zensigil", *args],
                                    cwd=directory, capture_output=True, text=True, timeout=15)
            commands.append({"arguments": list(args), "exit": result.returncode})
            assert result.returncode == expected_exit, (args, result.stdout, result.stderr)
            assert "Traceback" not in result.stderr, result.stderr
            return json.loads(result.stdout) if "--json" in args else result.stdout

        health = cli("doctor", "--json")
        assert health["ok"], health
        cli("init", "latency-review")
        starter = cli("run", "latency-review", "--json")
        assert starter["values"] == [{"greeting": "Hello from ZenSigil", "answer": 42}], starter
        starter_tests = cli("test", "latency-review", "--fail-if-empty", "--json")
        assert (starter_tests["total"], starter_tests["passed"]) == (2, 2), starter_tests
        project = directory / "latency-review"
        assert (project / "README.md").is_file()
        for name, content in files.items():
            target = project / name
            target.parent.mkdir(parents=True, exist_ok=True)
            # Use LF fixtures on Windows too; fmt --check intentionally rejects
            # CRLF source. Explicit newline also works with Python 3.9.
            with target.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
        assert cli("check", "latency-review", "--json")["ok"]
        result = cli("run", "latency-review", "--json")
        assert result["values"] == [{"count": 3, "total_ms": 300, "average_ms": 100}], result
        tested = cli("test", "latency-review", "--fail-if-empty", "--json")
        assert (tested["total"], tested["passed"], tested["failed"]) == (2, 2, 0), tested
        assert cli("lint", "latency-review", "--strict", "--json")["warnings"] == []
        cli("fmt", "latency-review", "--check")
        (project / "input.json").write_text('{"samples_ms": [20, 40]}', encoding="utf-8")
        changed = cli("run", "latency-review", "--json")
        assert changed["values"] == [{"count": 2, "total_ms": 60, "average_ms": 30}], changed
        (project / "input.json").write_text('{"samples_ms": [-1]}', encoding="utf-8")
        rejected = cli("run", "latency-review", "--json", expected_exit=1)
        assert rejected["diagnostics"][0]["code"] == "E_INPUT_DATA", rejected
        assert rejected["values"] == [], rejected
        (project / "input.json").write_text(files["input.json"], encoding="utf-8")
        cli("pack", "latency-review", "--name", "Latency review", "--output", "latency-review.sigil.json")
        project.rename(directory / "moved-source")
        portable = cli("run", "latency-review.sigil.json", "--json")
        for field in ("ok", "values", "proposals", "notes"):
            assert portable[field] == result[field], (field, portable, result)
        # Also prove that the installed console entry point is available outside
        # the source checkout. The isolated module commands above test semantics.
        executable = Path(sys.executable).parent / ("zensigil.exe" if sys.platform == "win32" else "zensigil")
        entry = subprocess.run([str(executable), "--version"], cwd=directory,
                               capture_output=True, text=True, timeout=15)
        assert entry.returncode == 0 and zensigil.__version__ in entry.stdout, entry.stderr
    report = {"ok": True, "version": zensigil.__version__, "installed_from": str(installed),
              "python": sys.version.split()[0], "platform": sys.platform,
              "source_import_excluded": True, "quickstart_files": sorted(files),
              "expected_summary": result["values"], "changed_summary": changed["values"],
              "invalid_input_rejected": True, "portable_without_source": True,
              "console_entry_point": True, "commands": commands}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    verify()
