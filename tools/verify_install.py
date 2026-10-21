"""Run with the fresh environment's Python: python -I tools/verify_install.py."""
import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import xml.etree.ElementTree as ET

import zensigil
from zensigil.server import Handler, CATALOG, EXAMPLES


def verify_adoption(directory, cli_command):
    """Smoke the selected package; cli_command also permits a source-only probe."""
    modules = {
        "left.zs": 'fn factor():\n    return 2\n\nexport fn scale(value):\n    return value * factor()\n\ntest "Module smoke":\n    require scale(3) == 6, "left factor"\n',
        "right.zs": 'fn factor():\n    return 3\n\nexport fn scale(value):\n    return value * factor()\n\ntest "Module smoke":\n    require scale(3) == 9, "right factor"\n',
    }
    source = ('use "left.zs" as left\nuse "right.zs" as right\n'
              'emit map([1, 2], left.scale)\nemit map([1, 2], right.scale)\n'
              'let later = fn (n) => left.scale(n) + right.scale(n)\nemit later(4)\n')
    result = zensigil.run(source, modules=modules)
    assert result["ok"] and result["values"] == [[2, 4], [3, 6], 20], result
    private = zensigil.run(source + 'emit left.factor()\n', modules=modules)
    assert not private["ok"] and private["diagnostics"][0]["code"] == "E_IMPORT", private
    assert private["values"] == [] and private["notes"] == [] and private["proposals"] == [], private

    # An intentional failed multiline cell must not retain its mutation or output.
    repl = subprocess.run([*cli_command, "repl"], cwd=directory, capture_output=True,
                          text=True, timeout=10,
                          input=('say "once"\nvar total = 3\n'
                                 'when true:\n    set total = 999\n    emit total\n'
                                 '    require false, "rollback smoke"\n\n'
                                 'total\nset total = total + 2\ntotal\n:quit\n'))
    assert repl.returncode == 1, (repl.returncode, repl.stdout, repl.stderr)
    assert repl.stdout.splitlines() == ["NOTE once", "VALUE 3", "VALUE 5"], repl.stdout
    assert repl.stderr.count("E_REQUIRE") == 1 and "rollback smoke" in repl.stderr, repl.stderr

    folder = Path(directory) / "namespace-report"
    folder.mkdir()
    for name, module_source in modules.items():
        (folder / name).write_text(module_source, encoding="utf-8")
    program = folder / "main.zs"
    program.write_text(source + 'test "Public APIs":\n'
                       '    require left.scale(3) + right.scale(3) == 15, "independent helpers"\n'
                       'test "Assertion smoke":\n    require false, "expected assertion"\n'
                       'test "Runtime smoke":\n    require 1 / 0 == 1, "expected runtime error"\n',
                       encoding="utf-8")
    report_path = folder / "results.xml"
    reported = subprocess.run([*cli_command, "test", str(program), "--json", "--junit", str(report_path)],
                              cwd=directory, capture_output=True, text=True, timeout=10)
    assert reported.returncode == 1, (reported.returncode, reported.stdout, reported.stderr)
    summary = json.loads(reported.stdout)
    assert summary["total"] == 5 and summary["passed"] == 3 and summary["failed"] == 2, summary
    xml = ET.parse(report_path).getroot()
    suite = xml.find("testsuite")
    assert suite is not None and xml.get("tests") == "5", ET.tostring(xml)
    assert suite.get("tests") == "5" and suite.get("failures") == "1" and suite.get("errors") == "1", suite.attrib
    cases = suite.findall("testcase")
    module_cases = [case for case in cases if case.get("name") == "Module smoke"]
    assert {case.get("file") for case in module_cases} == {"left.zs", "right.zs"}, [case.attrib for case in module_cases]
    assert len({(case.get("classname"), case.get("name")) for case in cases}) == 5, [case.attrib for case in cases]
    assert len(suite.findall("testcase/failure")) == 1 and len(suite.findall("testcase/error")) == 1
    assert all("time" not in element.attrib and "timestamp" not in element.attrib for element in xml.iter())


def verify():
    root = Path(__file__).resolve().parents[1]
    package = Path(zensigil.__file__).resolve().parent
    assert not package.is_relative_to(root), "This check must use the installed package."
    assert (package / "web/index.html").is_file()
    assert (package / "THIRD_PARTY_NOTICES.md").is_file()
    assert len(CATALOG) == 23
    assert EXAMPLES == package / "demo", "Installed examples must come from the wheel."
    def cli(*args, cwd):
        completed = subprocess.run([sys.executable, "-I", "-m", "zensigil", *args],
                                   cwd=cwd, capture_output=True, text=True)
        assert completed.returncode == 0, completed.stderr + completed.stdout
        return completed.stdout
    with tempfile.TemporaryDirectory() as directory:
        report = json.loads(cli("doctor", "--json", cwd=directory))
        assert report["ok"]
        folder = Path(directory) / "reading"
        cli("example", "reading-list", "--output", str(folder), cwd=directory)
        assert (folder / "proposal.contract.json").is_file()
        portable = Path(directory) / "reading.sigil.json"
        cli("pack", str(folder / "program.zs"), "--data", str(folder / "input.json"),
            "--contract", str(folder / "input.contract.json"), "--proposal-contract",
            str(folder / "proposal.contract.json"), "--name", "Installed reading example",
            "--output", str(portable), cwd=directory)
        result = json.loads(cli("run", str(portable), "--json", cwd=directory))
        assert len(result["proposals"]) == 1
        assert result["proposals"][0]["fields"]["id"] == "B1"
        assert len(result["notes"]) == 2
        project = Path(directory) / "project"
        cli("init", str(project), cwd=directory)
        assert json.loads(cli("run", str(project), "--json", cwd=directory))["ok"]
        assert json.loads(cli("test", str(project), "--json", cwd=directory))["passed"] > 0
        cli("fmt", str(project / "main.zs"), "--check", cwd=directory)
        assert json.loads(cli("ast", str(project / "main.zs"), "--json", cwd=directory))
        modular = Path(directory) / "modular"
        cli("example", "module-lab", "--output", str(modular), cwd=directory)
        portable_module = Path(directory) / "modular.sigil.json"
        cli("pack", str(modular / "program.zs"), "--data", str(modular / "input.json"),
            "--name", "Installed modules", "--output", str(portable_module), cwd=directory)
        module_result = json.loads(cli("run", str(portable_module), "--json", cwd=directory))
        assert module_result["values"] == [{"mean": 6, "squares": [9, 36, 81], "classification": "low"}]
        assert json.loads(cli("test", str(portable_module), "--json", cwd=directory))["passed"] == 2
        assert zensigil.run('emit dec_add("0.1", "0.2")')["values"] == ["0.3"]
        assert zensigil.run('let offset = 3\nlet add = fn (n: number) -> number => n + offset\nemit map([1, 2], add)')["values"] == [[4, 5]]
        assert zensigil.run('let values: record<list<integer | null>> = {scores: [1, null]}\nemit values')["ok"]
        assert zensigil.run('emit count_by([1, 2, 3], fn (n) => text(n % 2))')["values"] == [{"1": 2, "0": 1}]
        listed = json.loads(cli("test", str(project), "--list", "--json", cwd=directory))
        assert listed["total"] > 0 and listed["passed"] == 0
        assert all(case["ok"] is None for case in listed["tests"])
        assert json.loads(cli("lint", str(project), "--json", cwd=directory))["ok"]
        cli("fmt", str(project), "--check", cwd=directory)
        frames = []
        for message in ({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                        {"jsonrpc": "2.0", "id": 2, "method": "shutdown"},
                        {"jsonrpc": "2.0", "method": "exit"}):
            payload = json.dumps(message).encode("utf-8")
            frames.append(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload)
        process = subprocess.run([sys.executable, "-I", "-m", "zensigil", "lsp"],
                                 input=b"".join(frames), capture_output=True, cwd=directory, timeout=10)
        assert process.returncode == 0, process.stderr
        assert b'completionProvider' in process.stdout, process.stdout
        verify_adoption(directory, [sys.executable, "-I", "-m", "zensigil"])
    class Quiet(Handler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for route in ("/", "/api/health", "/api/examples"):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            connection.request("GET", route)
            response = connection.getresponse()
            body = response.read()
            assert response.status == 200, (route, body)
            if route == "/api/examples":
                entries = json.loads(body)
                assert len(entries) == 23
                assert next(e for e in entries if e["id"] == "reading-list")["proposal_contract"]
            connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    print(json.dumps({"ok": True, "version": zensigil.__version__, "installed_from": str(package),
                      "examples": 23, "portable_roundtrip": True, "module_roundtrip": True, "project_tools": True,
                      "closures_and_types": True, "collection_tools": True, "lsp_stdio": True, "http_resources": True,
                      "namespace_api": True, "repl_transactions": True, "junit_xml": True}, indent=2))


if __name__ == "__main__":
    verify()
