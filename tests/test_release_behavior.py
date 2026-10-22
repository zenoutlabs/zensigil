"""Cross-interface and adoption checks with independently specified outcomes."""
import json
from pathlib import Path
import random
import unittest

from zensigil import run
from zensigil.programs import decode_program

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class ReleaseBehaviorTests(unittest.TestCase):
    def test_portable_shared_fixtures(self):
        for case in json.loads((FIXTURES / "portable-cases.json").read_text()):
            with self.subTest(case=case["name"]):
                if case["valid"]:
                    result = decode_program(case["text"])
                    self.assertEqual(result["language_version"], "0.8.0")
                    self.assertEqual(result["data_text"], "{unfinished")
                else:
                    with self.assertRaises((ValueError, UnicodeError)):
                        decode_program(case["text"])

    def test_every_example_matches_expected_decisions(self):
        expected = json.loads((FIXTURES / "examples-expected.json").read_text())
        self.assertEqual(set(expected), {p.stem for p in (ROOT / "examples").glob("*.zs")})
        for key, outcome in expected.items():
            with self.subTest(example=key):
                folder = ROOT / "examples"
                def optional(suffix):
                    path = folder / (key + suffix)
                    return json.loads(path.read_text()) if path.exists() else None
                result = run((folder / (key + ".zs")).read_text(),
                             optional(".json"), contract=optional(".contract.json"),
                             proposal_contract=optional(".proposal.json"), modules=optional(".modules.json"))
                if "error" in outcome:
                    self.assertFalse(result["ok"])
                    self.assertEqual(result["diagnostics"][0]["code"], outcome["error"])
                    self.assertEqual(result["proposals"], [])
                    self.assertEqual(result["notes"], [])
                    continue
                self.assertTrue(result["ok"], result)
                self.assertEqual(result.get("values", []), outcome.get("values", []))
                proposals = outcome.get("proposals", [])
                self.assertEqual(len(result["proposals"]), len(proposals))
                for actual, (action, fields) in zip(result["proposals"], proposals):
                    self.assertEqual(actual["action"], action)
                    self.assertEqual({k: actual["fields"][k] for k in fields}, fields)
                    self.assertTrue(actual["requires_review"])
                if "notes" in outcome:
                    self.assertEqual([n["message"] for n in result["notes"]], outcome["notes"])
                else:
                    self.assertEqual(len(result["notes"]), outcome["note_count"])
                self.assertEqual(result["stats"]["duplicates_collapsed"], outcome.get("duplicates", 0))

    def test_new_example_boundaries(self):
        folder = ROOT / "examples"
        def evaluate(key, mutate):
            data = json.loads((folder / (key + ".json")).read_text())
            mutate(data)
            return run((folder / (key + ".zs")).read_text(), data,
                       contract=json.loads((folder / (key + ".contract.json")).read_text()),
                       proposal_contract=json.loads((folder / (key + ".proposal.json")).read_text()))
        self.assertEqual(len(evaluate("reading-list", lambda d: d.update(max_pages=500))["proposals"]), 2)
        self.assertEqual(len(evaluate("reading-list", lambda d: d.update(max_pages=179))["proposals"]), 0)
        self.assertEqual(len(evaluate("event-capacity", lambda d: d["sessions"][0].update(registered=20))["proposals"]), 0)
        self.assertEqual(len(evaluate("project-budget", lambda d: d["projects"][0].update(spent_cents=50000))["proposals"]), 0)
        bad = evaluate("project-budget", lambda d: d["projects"][0].update(spent_cents=1.5))
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["proposals"], [])

    def test_seeded_malformed_programs_never_escape_diagnostics(self):
        rng = random.Random(3719)
        alphabet = 'abcdef0129+-*/%<>=!():,[]{}"\\ \n\t'
        for index in range(1000):
            source = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 100)))
            result = run(source, {}, max_steps=500)
            self.assertIs(type(result["ok"]), bool, index)
            if not result["ok"]:
                self.assertTrue(result["diagnostics"], index)
                self.assertEqual(result["proposals"], [], index)
                self.assertEqual(result["notes"], [], index)


if __name__ == "__main__":
    unittest.main()
