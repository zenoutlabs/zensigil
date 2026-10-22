"""Portable project round trips retain tests, dependencies, and input defaults."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from zensigil.portable_testing import test_bundle
from zensigil.programs import (decode_program, encode_program, unpack_program,
                               validate_program)
from zensigil.projects import init_project, load_project

ROOT = Path(__file__).resolve().parents[1]
CASE = 'test "Expected value":\n    require true, "Expected true."\n'


def document(**changes):
    result = {"format": "zensigil-program", "format_version": 1,
              "language_version": "0.8.0", "name": "Portable tests",
              "source": "emit 42\n", "data_text": "{}", "contract_text": ""}
    result.update(changes)
    return result


class Portable08CodecTests(unittest.TestCase):
    def test_old_documents_gain_empty_tests_without_changing_drafts(self):
        for version in ("0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0"):
            with self.subTest(version=version):
                draft = document(language_version=version, source="when unfinished\n", data_text="{")
                decoded = decode_program(encode_program(draft))
                self.assertEqual(decoded["tests"], {})
                self.assertEqual(decoded["source"], draft["source"])
                self.assertEqual(decoded["data_text"], "{")
        tests = {"checks/draft.zs": "test unfinished\n"}
        self.assertEqual(decode_program(encode_program(document(tests=tests)))["tests"], tests)

    def test_test_maps_reject_invalid_paths_types_and_limits(self):
        bad_maps = [None, [], {"../escape.zs": ""}, {"/absolute.zs": ""},
                    {"checks.zs": 2}, {"checks.zs": "\ud800"},
                    {"A.zs": "", "a.zs": ""}, {"a.zs": "", "a.zs/b.zs": ""},
                    {"a.zs": "é" * 32769}, {f"case{i}.zs": "" for i in range(33)},
                    {f"case{i}.zs": "x" * 65536 for i in range(5)}]
        for tests in bad_maps:
            with self.subTest(tests=str(tests)[:80]), self.assertRaises(ValueError):
                validate_program(document(tests=tests))

    def test_source_maps_share_only_identical_exact_paths(self):
        accepted = validate_program(document(modules={"a.zs": CASE}, tests={"a.zs": CASE}))
        self.assertEqual(accepted["tests"], accepted["modules"])
        for tests in ({"a.zs": "different"}, {"A.zs": CASE}, {"a.zs/b.zs": CASE}):
            with self.subTest(tests=tests), self.assertRaises(ValueError):
                validate_program(document(modules={"a.zs": CASE}, tests=tests))
        # Each map has its own cap. The combined project can have 64 source files.
        modules = {f"modules/{i}.zs": "" for i in range(32)}
        tests = {f"tests/{i}.zs": "" for i in range(32)}
        self.assertEqual(len(validate_program(document(modules=modules, tests=tests))["tests"]), 32)

    def test_entry_identity_is_explicit_and_rejects_path_conflicts(self):
        for entry in (None, "../outside.zs", "/absolute.zs", "not-source.json", 2):
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                validate_program(document(entry_path=entry))
        for entry in ("A.zs", "a.zs/child.zs", "a.zs"):
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                validate_program(document(entry_path=entry, modules={"a.zs": "different"}))
        result = validate_program(document(source=CASE, entry_path="a.zs", modules={"a.zs": CASE}))
        self.assertEqual(result["entry_path"], "a.zs")

    def test_encoding_rejects_an_envelope_that_cannot_be_reopened(self):
        value = document(source="\x00" * 65536, data_text="\x00" * 1048576,
                         contract_text="\x00" * 262144, proposal_contract_text="\x00" * 262144,
                         tests={f"case{i}.zs": "\x00" * 65536 for i in range(4)})
        with self.assertRaisesRegex(ValueError, "10 MiB"):
            encode_program(value)

    def test_unpack_avoids_source_and_input_directory_collisions(self):
        value = document(modules={"program.zs": CASE, "input.json/helper.zs": ""},
                         tests={"checks.zs": CASE}, contract_text="{}", proposal_contract_text="{}")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "reopened"
            unpack_program(value, output)
            project = load_project(output)
            self.assertEqual(project["entry"].name, "_program.zs")
            self.assertEqual(project["data"].name, "_input.json")
            self.assertEqual(project["tests"], [(output / "checks.zs").resolve()])
            self.assertEqual(project["contract"].read_text(), "{}")
            self.assertEqual(project["proposal_contract"].read_text(), "{}")
            self.assertEqual((output / "program.zs").read_text(), CASE)

    def test_unpack_keeps_blank_contract_text_without_enabling_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "reopened"
            unpack_program(document(contract_text=" \n", proposal_contract_text="\t"), output)
            project = load_project(output)
            self.assertIsNone(project["contract"])
            self.assertIsNone(project["proposal_contract"])
            self.assertEqual((output / "input.contract.json").read_text(), " \n")
            self.assertEqual((output / "proposal.contract.json").read_text(), "\t")

    def test_unpack_manifest_conflict_fails_before_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "reopened"
            with self.assertRaisesRegex(ValueError, "zensigil.json"):
                unpack_program(document(modules={"ZenSigil.json/a.zs": ""}), output)
            self.assertFalse(output.exists())

    def test_unpack_cleans_its_files_after_a_write_failure(self):
        real_open = Path.open
        def failing_open(path, *args, **kwargs):
            if path.name == "input.json":
                raise OSError("Simulated full disk")
            return real_open(path, *args, **kwargs)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "reopened"
            with patch.object(Path, "open", failing_open), self.assertRaisesRegex(OSError, "full disk"):
                unpack_program(document(modules={"lib/a.zs": ""}), output)
            self.assertFalse(output.exists())


class Portable08TestRunnerTests(unittest.TestCase):
    def test_shared_modules_run_once_and_same_labels_keep_separate_roots(self):
        modules = {"math.zs": 'fn factor():\n    return 2\n' + CASE}
        source = 'use "math.zs" as math\n' + CASE
        result = test_bundle(source, modules=modules, tests={"tests.zs": source})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["passed"], 3)
        self.assertEqual({case["source_name"] for case in result["tests"]},
                         {"<program>", "math.zs", "tests.zs"})

    def test_test_roots_keep_function_scopes_and_do_not_run_effects(self):
        left = 'fn factor():\n    return 2\n' + 'test "Left":\n    require factor() == 2, "left"\n'
        right = 'fn factor():\n    return 3\n' + 'test "Right":\n    require factor() == 3, "right"\n'
        result = test_bundle('emit missing_input\n' + left, tests={"right.zs": right})
        self.assertTrue(result["ok"], result)
        self.assertEqual((result["total"], result["passed"], result["values"]), (2, 2, []))

    def test_all_roots_check_before_any_tests_run(self):
        with patch("zensigil.portable_testing.run_test_program") as execute:
            result = test_bundle(CASE, tests={"bad.zs": "test invalid\n"})
        execute.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["diagnostics"][0]["source_name"], "bad.zs")
        self.assertEqual(result["diagnostics"][0]["source_line"], "test invalid")

    def test_budget_is_shared_and_zero_remaining_is_a_limit_error(self):
        one = test_bundle(CASE)
        limit = one["stats"]["steps"]
        result = test_bundle(CASE, tests={"next.zs": CASE}, max_steps=limit)
        self.assertFalse(result["ok"])
        self.assertEqual((result["passed"], result["failed"]), (1, 1))
        self.assertEqual(result["stats"]["steps"], limit)
        self.assertEqual(result["diagnostics"][0]["code"], "E_LIMIT")
        self.assertEqual(result["diagnostics"][0]["source_name"], "next.zs")

    def test_filter_list_and_invalid_budget(self):
        result = test_bundle(CASE, tests={"bad.zs": 'test "Failure":\n    require false, "fail"\n'},
                             name_filter="Failure", list_only=True)
        self.assertTrue(result["ok"], result)
        self.assertEqual((result["total"], result["stats"]["steps"]), (1, 0))
        self.assertIsNone(result["tests"][0]["ok"])
        for budget in (0, True, 100001, "100", None):
            with self.subTest(budget=budget):
                result = test_bundle(CASE, max_steps=budget)
                self.assertFalse(result["ok"])
                self.assertEqual(result["diagnostics"][0]["code"], "E_TEST_BUNDLE")

    def test_same_source_identity_cannot_hide_different_test_text(self):
        result = test_bundle(CASE, source_name="checks.zs", tests={"checks.zs": "different"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["diagnostics"][0]["code"], "E_TEST_BUNDLE")

    def test_diagnostic_and_call_trace_aliases_use_the_test_path(self):
        source = 'fn fail():\n    return 1 / 0\ntest "Bad call":\n    require fail() == 1, "no"\n'
        result = test_bundle("emit 1\n", tests={"checks.zs": source})
        self.assertFalse(result["ok"])
        error = result["diagnostics"][0]
        self.assertEqual(error["source_name"], "checks.zs")
        self.assertEqual(error["source_file"], "checks.zs")
        self.assertEqual(error["call_trace"][0]["source_name"], "checks.zs")
        self.assertEqual(error["call_trace"][0].get("source_file", error["call_trace"][0]["source_name"]), "checks.zs")

    def test_equal_source_text_does_not_merge_distinct_files(self):
        result = test_bundle(CASE, source_name="main.zs", tests={"copy.zs": CASE})
        self.assertTrue(result["ok"])
        self.assertEqual(result["total"], 2)

    def test_failure_output_budget_is_shared_across_test_roots(self):
        module = 'export fn message():\n    return replace("xxxxxx", "x", "' + 'y' * 10000 + '")\n'
        body = 'use "messages.zs" as messages\ntest "Large failure":\n    require false, messages.message()\n'
        result = test_bundle('', modules={"messages.zs": module},
                             tests={f"test{i}.zs": body for i in range(12)})
        self.assertFalse(result["ok"])
        self.assertTrue(result["stopped_early"])
        self.assertLess(result["total"], 12)
        self.assertEqual(result["diagnostics"][-1]["code"], "E_TEST_LIMIT")
        self.assertEqual(result["tests"][-1]["source_name"], "<test output>")
        self.assertLessEqual(len(json.dumps(result, separators=(',', ':')).encode('utf-8')), 1048576)

    def test_list_output_budget_counts_long_source_names_without_execution(self):
        source = ''.join(f'test "Case {i}":\n    require true, "yes"\n' for i in range(200))
        tests = {'checks/' + 'x' * 140 + f'{i:02}.zs': source for i in range(16)}
        result = test_bundle('', tests=tests, list_only=True)
        self.assertFalse(result["ok"])
        self.assertTrue(result["listed"])
        self.assertTrue(result["stopped_early"])
        self.assertEqual(result["stats"]["steps"], 0)
        self.assertEqual(result["diagnostics"][-1]["code"], "E_TEST_LIMIT")
        self.assertLessEqual(len(json.dumps(result, separators=(',', ':')).encode('utf-8')), 1048576)


class Portable08CLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        init_project(self.project)
        manifest_path = self.project / "zensigil.json"
        manifest = json.loads(manifest_path.read_text())
        manifest.update(data="input.json", contract="contract.json", proposal_contract="proposals.json")
        manifest_path.write_text(json.dumps(manifest))
        (self.project / "input.json").write_text('{"value": 21}')
        (self.project / "contract.json").write_text('{"type":"object","required":["value"]}')
        (self.project / "proposals.json").write_text('{}')
        (self.project / "main.zs").write_text('use "lib/math.zs" as math\nemit math.double(value)\n')
        (self.project / "lib/only-tests.zs").write_text('export fn zero():\n    return 0\n')
        with (self.project / "tests.zs").open("a") as stream:
            stream.write('use "lib/only-tests.zs" as helper\n\ntest "Test dependency":\n    require helper.zero() == 0, "zero"\n')
        self.portable = self.root / "project.sigil.json"

    def tearDown(self):
        self.temporary.cleanup()

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, "-m", "zensigil", *map(str, args)], cwd=ROOT,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0 if ok else 1, result.stderr + result.stdout)
        self.assertNotIn("Traceback", result.stderr)
        return json.loads(result.stdout) if "--json" in args else result.stdout

    def pack(self):
        self.cli("pack", self.project, "--name", "Shared project", "--output", self.portable)

    def test_pack_run_test_unpack_roundtrip_without_source_folder(self):
        original = self.cli("test", self.project, "--fail-if-empty", "--json")
        self.pack()
        packed_bytes = self.portable.read_bytes()
        self.cli("pack", self.project, "--name", "Shared project", "--output", self.portable, "--force")
        self.assertEqual(self.portable.read_bytes(), packed_bytes)
        packed = decode_program(self.portable.read_text())
        self.assertIn("tests.zs", packed["tests"])
        self.assertIn("lib/only-tests.zs", packed["modules"])
        self.project.rename(self.root / "moved-source")
        self.assertEqual(self.cli("run", self.portable, "--json")["values"], [42])
        portable_tests = self.cli("test", self.portable, "--fail-if-empty", "--json")
        self.assertEqual(portable_tests["passed"], original["passed"])
        output = self.root / "reopened"
        self.cli("unpack", self.portable, "--output", output)
        self.assertEqual(self.cli("run", output, "--json")["values"], [42])
        self.assertEqual(self.cli("test", output, "--json")["passed"], original["passed"])
        self.assertTrue(self.cli("lint", self.portable, "--json")["ok"])

    def test_bundle_test_failures_do_not_change_run_and_have_junit_locations(self):
        (self.project / "tests.zs").write_text('test "Only fail":\n    require false, "Expected failure."\n')
        self.pack()
        self.assertEqual(self.cli("run", self.portable, "--json")["values"], [42])
        listed = self.cli("test", self.portable, "--list", "--filter", "Only", "--json")
        self.assertEqual(listed["total"], 1)
        report = self.root / "tests.xml"
        failed = self.cli("test", self.portable, "--junit", report, "--json", ok=False)
        self.assertEqual(failed["failed"], 1)
        self.assertEqual(failed["diagnostics"][0]["source_name"], "tests.zs")
        case = ET.parse(report).getroot().find("testsuite/testcase")
        self.assertEqual(case.get("file"), "tests.zs")
        self.assertEqual(case.find("failure").get("type"), "E_REQUIRE")

    def test_pack_protects_test_only_modules(self):
        path = self.project / "lib/only-tests.zs"
        before = path.read_bytes()
        self.cli("pack", self.project, "--name", "Keep test helper", "--output", path, "--force", ok=False)
        self.assertEqual(path.read_bytes(), before)

    def test_pack_preserves_unfinished_test_without_imports(self):
        for label, raw_source in (("lf", b"test unfinished\n"), ("crlf", b"test unfinished\r\n")):
            with self.subTest(newline=label):
                (self.project / "tests.zs").write_bytes(raw_source)
                portable = self.root / ("unfinished-" + label + ".sigil.json")
                self.cli("pack", self.project, "--name", "Shared project", "--output", portable)
                self.assertEqual(decode_program(portable.read_text())["tests"]["tests.zs"], raw_source.decode("utf-8"))
                failed = self.cli("test", portable, "--json", ok=False)
                self.assertEqual(failed["diagnostics"][0]["source_name"], "tests.zs")
                output = self.root / ("unfinished-" + label)
                self.cli("unpack", portable, "--output", output)
                self.assertEqual((output / "tests.zs").read_bytes(), raw_source)

    def test_entry_imported_by_tests_keeps_one_identity_after_roundtrip(self):
        (self.project / "main.zs").write_text('export fn answer():\n    return 42\n' + CASE)
        (self.project / "tests.zs").write_text('use "main.zs" as main\ntest "External check":\n    require main.answer() == 42, "answer"\n')
        original = self.cli("test", self.project, "--json")
        self.assertEqual(original["total"], 2)
        self.pack()
        packed = decode_program(self.portable.read_text())
        self.assertEqual(packed["entry_path"], "main.zs")
        self.project.rename(self.root / "moved-source")
        portable = self.cli("test", self.portable, "--json")
        self.assertEqual(portable["tests"], original["tests"])
        output = self.root / "reopened"
        self.cli("unpack", self.portable, "--output", output)
        self.assertEqual(load_project(output)["entry"], (output / "main.zs").resolve())
        reopened = self.cli("test", output, "--json")
        self.assertEqual(reopened["tests"], original["tests"])

    def test_plain_source_filenames_keep_space_and_unicode_compatibility(self):
        source = self.root / "My café program.zs"
        source.write_text("emit 42\n" + CASE, encoding="utf-8")
        self.cli("pack", source, "--name", "Named source", "--output", self.portable)
        self.assertNotIn("entry_path", decode_program(self.portable.read_text()))
        self.assertEqual(self.cli("run", self.portable, "--json")["values"], [42])
        self.assertEqual(self.cli("test", self.portable, "--json")["total"], 1)


if __name__ == "__main__":
    unittest.main()
