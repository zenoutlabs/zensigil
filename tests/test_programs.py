"""Portable files work across CLI entry points without losing unfinished drafts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from zensigil import __main__ as cli_module
from zensigil.server import CATALOG
from zensigil.programs import decode_program, encode_program, validate_program, MAX_PROGRAM_BYTES

ROOT = Path(__file__).resolve().parents[1]


def document(**changes):
    value = {"format": "zensigil-program", "format_version": 1, "language_version": "0.2.0",
             "name": "A portable program", "source": "say text(count)\n", "data_text": '{"count": 3}',
             "contract_text": '{"type":"object","required":["count"]}'}
    value.update(changes)
    return value


class PortableCodecTests(unittest.TestCase):
    def test_upgrade_retains_raw_unfinished_text(self):
        program = document(source="when unfinished\n", data_text="{\n", contract_text=" { ",
                           proposal_contract_text="\t{", name="  Draft name  ")
        upgraded = decode_program(json.dumps(program))
        self.assertEqual(upgraded["language_version"], "0.8.0")
        for key in ("source", "data_text", "contract_text", "proposal_contract_text", "name"):
            self.assertEqual(upgraded[key], program[key])
        self.assertEqual(decode_program(encode_program(upgraded)), upgraded)

    def test_strict_envelope_versions_fields_and_duplicates(self):
        for changes in ({"format_version": True}, {"format_version": 2}, {"language_version": "9.0.0"},
                        {"format": "other"}, {"source": None}, {"proposal_contract_text": {}},
                        {"name": " \t"}, {"name": "😀" * 41}, {"unexpected": "not accepted"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_program(document(**changes))
        missing = document()
        del missing["contract_text"]
        with self.assertRaises(ValueError):
            validate_program(missing)
        repeated = json.dumps(document())[:-1] + ',"name":"second"}'
        with self.assertRaisesRegex(ValueError, "repeated"):
            decode_program(repeated)

    def test_json_number_version_and_unicode_compatibility(self):
        self.assertEqual(validate_program(document(format_version=1.0))["format_version"], 1)
        for field in ("source", "data_text", "contract_text", "proposal_contract_text", "name"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_program(document(**{field: "\ud800"}))
        for version in (None, {}, [], True, 3):
            with self.subTest(version=version), self.assertRaises(ValueError):
                validate_program(document(language_version=version))
        with self.assertRaises(ValueError):
            validate_program(document(name="\ufeff"))
        self.assertEqual(validate_program(document(name="\u0085"))["name"], "\u0085")

    def test_utf8_limits_and_total_size(self):
        with self.assertRaisesRegex(ValueError, "65536"):
            validate_program(document(source="é" * 32769))
        with self.assertRaisesRegex(ValueError, "10 MiB"):
            decode_program(" " * (MAX_PROGRAM_BYTES + 1))
        # The outer bound permits even worst-case JSON escaping for maximum fields.
        large = document(source="\x00" * 65536, data_text="\x00" * 1048576,
                         contract_text="\x00" * 262144, proposal_contract_text="\x00" * 262144)
        self.assertEqual(decode_program(encode_program(large))["data_text"], large["data_text"])


class PortableCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.program = self.directory / "test.sigil.json"
        self.program.write_text(json.dumps(document()), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args):
        return subprocess.run([sys.executable, "-m", "zensigil", *map(str, args)], cwd=ROOT,
                              capture_output=True, text=True, timeout=10)

    def parsed(self, *args, ok=True):
        command = self.cli(*args, "--json")
        self.assertEqual(command.returncode, 0 if ok else 1, command.stderr or command.stdout)
        self.assertNotIn("Traceback", command.stderr)
        result = json.loads(command.stdout)
        self.assertEqual(result["ok"], ok)
        return result

    def test_run_and_check_embedded_inputs(self):
        result = self.parsed("run", self.program)
        self.assertEqual(result["notes"][0]["message"], "3")
        self.assertTrue(self.parsed("check", self.program)["input_names_checked"])

    def test_override_replaces_invalid_embedded_json(self):
        self.program.write_text(json.dumps(document(data_text="{broken", contract_text="{broken",
                                                   proposal_contract_text="{broken")))
        data = self.directory / "data.json"
        data.write_text('{"count":9}')
        contract = self.directory / "contract.json"
        contract.write_text('{}')
        proposal = self.directory / "proposals.json"
        # The empty action map accepts a program with no proposals.
        proposal.write_text('{}')
        result = self.parsed("run", self.program, "--data", data, "--contract", contract,
                             "--proposal-contract", proposal)
        self.assertEqual(result["notes"][0]["message"], "9")

    def test_json_diagnostics_identify_the_failing_boundary(self):
        cases = [(dict(data_text='{"count":1,"count":2}'), "E_INPUT"),
                 (dict(contract_text="{"), "E_CONTRACT"),
                 (dict(proposal_contract_text="null"), "E_PROPOSAL_CONTRACT"),
                 (dict(unrecognized=True), "E_PROGRAM")]
        for changes, code in cases:
            with self.subTest(code=code):
                self.program.write_text(json.dumps(document(**changes)))
                result = self.parsed("run", self.program, ok=False)
                self.assertEqual(result["diagnostics"][0]["code"], code)
                self.assertEqual(result["proposals"], [])

    def test_proposal_contract_checks_output_and_discards_notes(self):
        self.program.write_text(json.dumps(document(
            source='say "draft"\npropose review(quantity: -1)\n',
            proposal_contract_text=json.dumps({"review": {"type": "object", "properties": {
                "quantity": {"type": "integer", "minimum": 1}}, "required": ["quantity"]}}))))
        checked = self.parsed("check", self.program)
        self.assertFalse(checked["proposals_checked"])
        result = self.parsed("run", self.program, ok=False)
        self.assertEqual(result["diagnostics"][0]["code"], "E_PROPOSAL")
        self.assertEqual(result["diagnostics"][0]["output_path"], "$.proposals[0].fields.quantity")
        self.assertEqual(result["notes"], [])
        readable = self.cli("run", self.program)
        self.assertIn("$.proposals[0].fields.quantity", readable.stderr)

    def test_cli_option_errors_exit_one(self):
        for args in (("run",), ("run", self.program, "--force"), ("unpack", self.program)):
            result = self.cli(*args)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_invalid_unicode_and_nonstring_version_are_structured_errors(self):
        for changes in ({"source": "\ud800"}, {"language_version": {}}, {"name": "\udfff"}):
            with self.subTest(changes=changes):
                self.program.write_text(json.dumps(document(**changes)))
                result = self.parsed("run", self.program, ok=False)
                self.assertEqual(result["diagnostics"][0]["code"], "E_PROGRAM")

    def test_empty_explicit_contract_is_invalid(self):
        contract = self.directory / "empty.json"
        contract.write_text("")
        result = self.parsed("check", self.program, "--contract", contract, ok=False)
        self.assertEqual(result["diagnostics"][0]["code"], "E_CONTRACT")

    def test_pack_unpack_preserves_drafts_and_wont_replace(self):
        source = self.directory / "unfinished.zs"
        data = self.directory / "unfinished.json"
        contract = self.directory / "contract.json"
        proposal = self.directory / "proposal.json"
        for path, raw in ((source, "when unfinished\n"), (data, "{\n  \"open\": "),
                          (contract, "\n{unfinished"), (proposal, " \n{draft")):
            path.write_text(raw, encoding="utf-8")
        packed = self.directory / "draft.sigil.json"
        arguments = ("pack", source, "--data", data, "--contract", contract,
                     "--proposal-contract", proposal, "--name", "My draft", "--output", packed)
        first = self.cli(*arguments)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(self.cli(*arguments).returncode, 1)
        self.assertEqual(self.cli(*arguments, "--force").returncode, 0)
        before = source.read_bytes()
        protected = self.cli("pack", source, "--name", "Keep source", "--output", source, "--force")
        self.assertEqual(protected.returncode, 1)
        self.assertEqual(source.read_bytes(), before)
        extracted = self.directory / "extracted"
        result = self.cli("unpack", packed, "--output", extracted)
        self.assertEqual(result.returncode, 0, result.stderr)
        for original, name in ((source, "unfinished.zs"), (data, "input.json"),
                               (contract, "input.contract.json"), (proposal, "proposal.contract.json")):
            self.assertEqual(original.read_bytes(), (extracted / name).read_bytes())
        self.assertEqual(self.cli("unpack", packed, "--output", extracted).returncode, 1)

    def test_output_json_for_success_failure_and_exclusive_create(self):
        output = self.directory / "result.json"
        result = self.parsed("run", self.program, "--output", output)
        self.assertEqual(json.loads(output.read_text()), result)
        original = output.read_bytes()
        rejected = self.parsed("run", self.program, "--output", output, ok=False)
        self.assertEqual(rejected["diagnostics"][0]["code"], "E_OUTPUT")
        self.assertEqual(output.read_bytes(), original)
        self.program.write_text(json.dumps(document(source='say "before"\nrequire false, "Stop"\n')))
        result = self.parsed("run", self.program, "--output", output, "--force", ok=False)
        self.assertEqual(result["diagnostics"][0]["code"], "E_REQUIRE")
        self.assertEqual(result["notes"], [])
        self.assertEqual(json.loads(output.read_text()), result)

    def test_output_cannot_overwrite_an_input_even_with_force(self):
        original = self.program.read_bytes()
        result = self.parsed("run", self.program, "--output", self.program, "--force", ok=False)
        self.assertEqual(result["diagnostics"][0]["code"], "E_OUTPUT")
        self.assertEqual(self.program.read_bytes(), original)

    def test_output_aliases_cannot_overwrite_source_or_sidecars(self):
        source = self.directory / "source.zs"
        source.write_text('say "hello"\n')
        data = self.directory / "data.json"
        contract = self.directory / "contract.json"
        proposals = self.directory / "proposals.json"
        for path in (data, contract, proposals):
            path.write_text('{}')
        options = ("--data", data, "--contract", contract, "--proposal-contract", proposals)
        for input_path in (source, data, contract, proposals):
            alias = self.directory / (input_path.name + ".alias")
            os.link(input_path, alias)
            before = input_path.read_bytes()
            for command in ("run", "pack"):
                arguments = (command, source, *options, "--output", alias, "--force")
                if command == "pack":
                    arguments += ("--name", "Keep original")
                result = self.cli(*arguments)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("E_OUTPUT", result.stderr)
                self.assertEqual(input_path.read_bytes(), before)
                self.assertEqual(alias.read_bytes(), before)
        uppercase = source.with_name(source.name.upper())
        if uppercase.exists() and source.samefile(uppercase):
            result = self.cli("run", source, "--output", uppercase, "--force")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(source.read_text(), 'say "hello"\n')

    def test_doctor_requires_referenced_assets_and_catalog_examples(self):
        web = self.directory / "web"
        web.mkdir()
        (web / "assets").mkdir()
        index = web / "index.html"
        javascript = web / "assets" / "app.js"
        css = web / "assets" / "app.css"
        javascript.write_text("/* test fixture */")
        css.write_text("/* test fixture */")
        html = '<script src="/assets/app.js?version=1"></script><link rel="stylesheet" href="assets/app.css">'
        index.write_text(html)
        demo = self.directory / "demo"
        demo.mkdir()
        for name, _, _ in CATALOG:
            (demo / (name + ".zs")).write_text('say "example"')
            (demo / (name + ".json")).write_text('{}')
        with patch.object(cli_module, "WEB", web), patch.object(cli_module, "DEMO", demo):
            self.assertTrue(cli_module.doctor()["ok"])
            for asset in (javascript, css):
                asset.unlink()
                self.assertFalse(cli_module.doctor()["checks"]["playground"])
                asset.write_text("/* restored */")
            missing = CATALOG[0][0]
            for suffix in (".zs", ".json"):
                (demo / (missing + suffix)).unlink()
            self.assertFalse(cli_module.doctor()["checks"]["examples"])
            outside = self.directory / "outside.js"
            outside.write_text("/* exists outside bundle */")
            for reference in ("../outside.js", "%2e%2e/outside.js", "https://example.test/app.js"):
                index.write_text(f'<script src="{reference}"></script>')
                self.assertFalse(cli_module.doctor()["checks"]["playground"])
            alias = web / "alias.js"
            alias.symlink_to(outside)
            index.write_text('<script src="alias.js"></script>')
            self.assertFalse(cli_module.doctor()["checks"]["playground"])
            index.write_text("<html>No script bundle</html>")
            self.assertFalse(cli_module.doctor()["checks"]["playground"])

    def test_examples_scaffold_and_doctor(self):
        listed = self.cli("examples", "--json")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertIn("stock-review", json.loads(listed.stdout))
        destination = self.directory / "example"
        copied = self.cli("example", "stock-review", "--output", destination)
        self.assertEqual(copied.returncode, 0, copied.stderr)
        result = self.parsed("run", destination / "program.zs", "--data", destination / "input.json",
                             "--contract", destination / "input.contract.json")
        self.assertEqual(len(result["proposals"]), 2)
        reading = self.directory / "reading"
        self.assertEqual(self.cli("example", "reading-list", "--output", reading).returncode, 0)
        self.assertEqual((reading / "proposal.contract.json").read_bytes(),
                         (ROOT / "zensigil" / "demo" / "reading-list.proposal.json").read_bytes())
        self.assertEqual(self.cli("example", "../hello", "--output", self.directory / "bad").returncode, 1)
        health = self.parsed("doctor")
        self.assertTrue(all(health["checks"].values()))
        self.assertGreater(health["example_count"], 0)


if __name__ == "__main__":
    unittest.main()
