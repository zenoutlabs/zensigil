"""Developer workflows from files, with explicit input and overwrite boundaries."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from zensigil.projects import init_project, load_project

ROOT = Path(__file__).resolve().parents[1]


class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.project = self.directory / "project"
        init_project(self.project)

    def cli(self, *args):
        return subprocess.run([sys.executable, "-m", "zensigil", *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True, timeout=10)

    def manifest(self, **changes):
        path = self.project / "zensigil.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value.update(changes)
        path.write_text(json.dumps(value), encoding="utf-8")

    def write(self, name, value):
        path = self.project / name
        # Fixtures use the formatter's LF form on every host. Text-mode defaults
        # translate LF to CRLF on Windows, which correctly fails fmt --check.
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(value if isinstance(value, str) else json.dumps(value))
        return path

    def use_data(self):
        self.manifest(data="input.json", contract="input.contract.json",
                      proposal_contract="proposal.contract.json")
        self.write("input.json", {"quantity": 3})
        self.write("input.contract.json", {
            "type": "object", "properties": {"quantity": {"type": "integer", "minimum": 0}},
            "required": ["quantity"], "additionalProperties": False})
        self.write("proposal.contract.json", {
            "review": {"type": "object", "properties": {"amount": {"type": "integer"}},
                       "required": ["amount"], "additionalProperties": False}})
        self.write("main.zs", 'use "lib/math.zs" as math\n'
                   'emit math.double(quantity)\npropose review(amount: math.double(quantity))\n')

    def test_project_defaults_work_from_another_directory(self):
        self.use_data()
        for command in ("check", "run", "test", "lint"):
            with self.subTest(command=command):
                result = self.cli(command, self.project, "--json")
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                report = json.loads(result.stdout)
                self.assertTrue(report["ok"])
                if command == "run":
                    self.assertEqual(report["values"], [6])
                    self.assertEqual(report["proposals"][0]["fields"], {"amount": 6})

    def test_each_explicit_override_takes_precedence(self):
        self.use_data()
        data = self.write("other.json", {"quantity": -2})
        contract = self.write("other.contract.json", {"type": "object"})
        proposals = self.write("other.proposal.json", {
            "review": {"type": "object", "properties": {"amount": {"type": "integer", "minimum": 0}}}})
        result = self.cli("run", self.project, "--data", data, "--json")
        self.assertEqual(json.loads(result.stdout)["diagnostics"][0]["code"], "E_INPUT_DATA")
        result = self.cli("run", self.project, "--data", data, "--contract", contract, "--json")
        self.assertEqual(json.loads(result.stdout)["values"], [-4])
        result = self.cli("run", self.project, "--data", data, "--contract", contract,
                          "--proposal-contract", proposals, "--json")
        report = json.loads(result.stdout)
        self.assertEqual(report["diagnostics"][0]["code"], "E_PROPOSAL")
        self.assertEqual(report["values"], [])

    def test_invalid_or_empty_override_does_not_use_default(self):
        self.use_data()
        for flag, code in (("--data", "E_INPUT"), ("--contract", "E_CONTRACT"),
                           ("--proposal-contract", "E_PROPOSAL_CONTRACT")):
            for text in ("", "{bad", "[]"):
                with self.subTest(flag=flag, text=text):
                    path = self.write("override.json", text)
                    result = self.cli("run", self.project, flag, path, "--json")
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(json.loads(result.stdout)["diagnostics"][0]["code"], code)

    def test_blank_path_flags_cannot_disable_project_defaults(self):
        self.use_data()
        self.write("input.json", {"quantity": -1})
        self.assertEqual(self.cli("run", self.project, "--json").returncode, 1)
        for command in ("run", "pack"):
            for flag in ("--data", "--contract", "--proposal-contract"):
                with self.subTest(command=command, flag=flag):
                    output = self.directory / "never-created.json"
                    extra = ("--name", "Invalid", "--output", output) if command == "pack" else ("--json",)
                    result = self.cli(command, self.project, flag, "", *extra)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertFalse(output.exists())
                    if command == "run":
                        parsed = json.loads(result.stdout)
                        self.assertEqual(parsed["values"], [])
                        self.assertFalse(parsed["ok"])

    def test_module_root_symlink_loop_returns_an_import_error(self):
        root = self.directory / "loop"
        try:
            root.symlink_to(root.name)
        except OSError:
            self.skipTest("Symbolic links are unavailable.")
        for command in ("run", "pack"):
            output = self.directory / "never-created.json"
            extra = ("--name", "Loop", "--output", output) if command == "pack" else ("--json",)
            result = self.cli(command, self.project, "--module-root", root, *extra)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn("E_IMPORT", result.stderr + result.stdout)
            self.assertFalse(output.exists())

    def test_pack_project_preserves_input_contracts_and_modules(self):
        self.use_data()
        before = json.loads(self.cli("run", self.project, "--json").stdout)
        target = self.directory / "project.sigil.json"
        result = self.cli("pack", self.project, "--name", "Review", "--output", target)
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(document["modules"].keys(), {"lib/math.zs"})
        self.assertEqual(json.loads(document["data_text"]), {"quantity": 3})
        self.assertTrue(document["contract_text"])
        self.assertTrue(document["proposal_contract_text"])
        self.project.rename(self.directory / "moved")
        after = json.loads(self.cli("run", target, "--json").stdout)
        for field in ("ok", "values", "proposals", "notes"):
            self.assertEqual(before[field], after[field])

    def test_pack_project_uses_explicit_input_override(self):
        self.use_data()
        other = self.write("other.json", {"quantity": 7})
        target = self.directory / "override.sigil.json"
        result = self.cli("pack", self.project, "--data", other, "--name", "Override", "--output", target)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.cli("run", target, "--json").stdout)["values"], [14])

    def test_default_files_are_protected_even_when_overridden(self):
        self.use_data()
        override = self.write("other.json", {"quantity": 4})
        names = ("input.json", "input.contract.json", "proposal.contract.json", "zensigil.json",
                 "main.zs", "tests.zs", "lib/math.zs")
        for command in ("run", "pack"):
            for name in names:
                with self.subTest(command=command, name=name):
                    target = self.project / name
                    before = target.read_bytes()
                    extra = ("--name", "Protected") if command == "pack" else ("--json",)
                    result = self.cli(command, self.project, "--data", override,
                                      "--output", target, "--force", *extra)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(target.read_bytes(), before)

    def test_test_only_module_is_protected_from_run_and_pack(self):
        target = self.write("lib/test-helper.zs", "fn truth():\n    return true\n")
        self.write("tests.zs", 'use "lib/test-helper.zs"\ntest "Truth":\n    require truth(), "yes"\n')
        before = target.read_bytes()
        for command in ("run", "pack"):
            extra = ("--name", "Protected") if command == "pack" else ("--json",)
            result = self.cli(command, self.project, "--output", target, "--force", *extra)
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertEqual(target.read_bytes(), before)

    def test_early_invalid_default_cannot_replace_project_input(self):
        self.use_data()
        self.write("input.json", "{bad")
        target = self.project / "lib/math.zs"
        before = target.read_bytes()
        result = self.cli("run", self.project, "--output", target, "--force", "--json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["diagnostics"][0]["code"], "E_OUTPUT")
        self.assertEqual(target.read_bytes(), before)

    def test_output_hardlink_cannot_replace_declared_input(self):
        self.use_data()
        target = self.directory / "alias.json"
        try:
            import os
            os.link(self.project / "input.json", target)
        except OSError:
            self.skipTest("Hard links are unavailable.")
        before = target.read_bytes()
        result = self.cli("run", self.project, "--output", target, "--force", "--json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(target.read_bytes(), before)

    def test_output_symlink_loop_returns_diagnostic_for_run_and_pack(self):
        target = self.directory / "loop.json"
        try:
            target.symlink_to(target.name)
        except OSError:
            self.skipTest("Symbolic links are unavailable.")
        before = (self.project / "main.zs").read_bytes()
        for command in ("run", "pack"):
            extra = ("--name", "Loop") if command == "pack" else ("--json",)
            result = self.cli(command, self.project, "--output", target, "--force", *extra)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn("E_OUTPUT", result.stdout + result.stderr)
            self.assertTrue(target.is_symlink())
            self.assertEqual((self.project / "main.zs").read_bytes(), before)

    def test_json_input_paths_reject_escape_wrong_types_and_extensions(self):
        for field in ("data", "contract", "proposal_contract"):
            for value in (None, [], {}, "", "../data.json", "/data.json", "a\\b.json", "./data.json", "data.zs"):
                with self.subTest(field=field, value=value):
                    self.manifest(**{field: value})
                    result = self.cli("run", self.project, "--json")
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(json.loads(result.stdout)["diagnostics"][0]["code"], "E_PROJECT")
            self.manifest(**{field: "allowed.json"})

    def test_input_symlink_escape_and_loop_are_project_errors(self):
        outside = self.directory / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        target = self.project / "input.json"
        self.manifest(data="input.json")
        for link in (outside, Path("input.json")):
            try:
                target.symlink_to(link)
            except OSError:
                self.skipTest("Symbolic links are unavailable.")
            result = self.cli("run", self.project, "--json")
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(json.loads(result.stdout)["diagnostics"][0]["code"], "E_PROJECT")
            target.unlink()

    def test_manifest_version_types_return_project_errors(self):
        for value in ([], {}, None, True, 7):
            self.manifest(language_version=value)
            result = self.cli("run", self.project, "--json")
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(json.loads(result.stdout)["diagnostics"][0]["code"], "E_PROJECT")

    def test_prior_project_versions_still_load(self):
        for version in ("0.4.0", "0.5.0", "0.6.0", "0.7.0"):
            self.manifest(language_version=version)
            self.assertEqual(load_project(self.project)["entry"], (self.project / "main.zs").resolve())

    def test_missing_default_has_a_diagnostic_and_valid_override_can_replace_it(self):
        self.manifest(data="missing.json")
        result = self.cli("run", self.project, "--json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["diagnostics"][0]["code"], "E_INPUT")
        explicit = self.write("present.json", {})
        result = self.cli("run", self.project, "--data", explicit, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_quickstart_files_run_with_the_documented_result(self):
        guide = (ROOT / "docs/quickstart.md").read_text(encoding="utf-8")
        files = dict(re.findall(r"<!-- file:([^ >]+) -->\s*```[^\n]*\n(.*?)```", guide, re.S))
        self.assertEqual(set(files), {"zensigil.json", "input.json", "input.contract.json",
                                      "main.zs", "tests.zs", "lib/statistics.zs"})
        for name, source in files.items():
            self.write(name, source)
        result = self.cli("run", self.project, "--json")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)["values"],
                         [{"count": 3, "total_ms": 300, "average_ms": 100}])
        tested = self.cli("test", self.project, "--fail-if-empty", "--json")
        self.assertEqual(tested.returncode, 0, tested.stderr + tested.stdout)
        self.assertEqual(json.loads(tested.stdout)["passed"], 2)
        self.assertEqual(self.cli("fmt", self.project, "--check").returncode, 0)
        self.assertEqual(self.cli("lint", self.project, "--strict").returncode, 0)

    def test_crlf_project_sources_format_to_lf_without_changing_results(self):
        source = (self.project / "main.zs").read_text(encoding="utf-8")
        before = self.cli("run", self.project, "--json")
        self.assertEqual(before.returncode, 0, before.stderr)
        path = self.project / "main.zs"
        with path.open("w", encoding="utf-8", newline="\r\n") as stream:
            stream.write(source)
        self.assertIn(b"\r\n", path.read_bytes())
        checked = self.cli("fmt", self.project, "--check")
        self.assertEqual(checked.returncode, 1, checked.stdout + checked.stderr)
        self.assertIn("main.zs", checked.stdout)
        formatted = self.cli("fmt", self.project, "--write")
        self.assertEqual(formatted.returncode, 0, formatted.stdout + formatted.stderr)
        self.assertNotIn(b"\r", path.read_bytes())
        self.assertEqual(path.read_bytes(), source.encode("utf-8"))
        self.assertEqual(self.cli("fmt", self.project, "--check").returncode, 0)
        after = self.cli("run", self.project, "--json")
        self.assertEqual(after.returncode, 0, after.stderr)
        self.assertEqual(json.loads(before.stdout)["values"], json.loads(after.stdout)["values"])


if __name__ == "__main__":
    unittest.main()
