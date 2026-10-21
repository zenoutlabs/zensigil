"""Regression checks for opt-in, domain-neutral input contracts."""
import copy
import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from zensigil import check, run
from zensigil.contracts import contract_diagnostics
from zensigil.server import Handler

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'say "validated"\npropose review(reason: "ready")'
CONTRACT = {
    "type": "object", "required": ["inventory"], "additionalProperties": False,
    "properties": {"inventory": {
        "type": "array", "minItems": 1, "maxItems": 10, "uniqueBy": "sku",
        "items": {"type": "object", "required": ["sku", "stock", "sales"],
                  "additionalProperties": False,
                  "properties": {
                      "sku": {"type": "string", "minLength": 1, "maxLength": 20},
                      "stock": {"type": "integer", "minimum": 0, "maximum": 1000},
                      "sales": {"type": ["number", "null"], "minimum": 0},
                      "active": {"type": "boolean"},
                      "status": {"enum": ["active", "paused"]}}}}}}
DATA = {"inventory": [{"sku": "A17", "stock": 15, "sales": 4}]}


class ContractTests(unittest.TestCase):
    def invalid(self, data, contract=CONTRACT, code='E_INPUT_DATA'):
        result = run(SOURCE, data, contract=contract)
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['proposals'], [])
        self.assertEqual(result['notes'], [])
        for error in result['diagnostics']:
            self.assertEqual(error['code'], code)
            self.assertEqual((error['line'], error['column'], error['source_line']), (1, 1, ''))
            self.assertTrue(error['data_path'].startswith('$'))
        return result['diagnostics']

    def test_valid_preview_and_check_do_not_mutate_inputs(self):
        data, contract = copy.deepcopy(DATA), copy.deepcopy(CONTRACT)
        self.assertTrue(run(SOURCE, data, contract=contract)['ok'])
        self.assertTrue(check(SOURCE, data, contract=contract)['ok'])
        self.assertEqual(data, DATA)
        self.assertEqual(contract, CONTRACT)

    def test_optional_contract_keeps_existing_behavior(self):
        self.assertTrue(run(SOURCE, {'anything': True})['ok'])
        self.assertTrue(run(SOURCE, {'anything': True}, contract=None)['ok'])
        self.assertTrue(check(SOURCE, contract=CONTRACT)['ok'])
        self.invalid({}, CONTRACT)

    def test_collects_missing_negative_and_wrong_type_with_paths(self):
        errors = self.invalid({'inventory': [
            {'sku': 'A17', 'stock': -2, 'sales': '4'},
            {'sku': 'B24', 'sales': 1}]})
        self.assertEqual([e['data_path'] for e in errors], [
            '$.inventory[0].stock', '$.inventory[0].sales', '$.inventory[1].stock'])
        self.assertIn('A17', errors[0]['message'])
        self.assertIn('B24', errors[2]['message'])
        self.assertIn('missing', errors[2]['message'])

    def test_no_type_coercion_and_explicit_null(self):
        for stock in (True, '15', None, 15.0):
            with self.subTest(stock=stock):
                data = copy.deepcopy(DATA)
                data['inventory'][0]['stock'] = stock
                self.invalid(data)
        data = copy.deepcopy(DATA)
        data['inventory'][0]['sales'] = None
        self.assertTrue(run(SOURCE, data, contract=CONTRACT)['ok'])
        del data['inventory'][0]['sales']
        self.invalid(data)

    def test_number_bounds_string_bounds_and_additional_fields(self):
        data = {'inventory': [{'sku': '', 'stock': 1001, 'sales': -1, 'extra': 1}]}
        errors = self.invalid(data)
        self.assertEqual(len(errors), 4)
        self.assertIn('Unexpected field', errors[-1]['message'])
        self.invalid({'inventory': [{'sku': 'x' * 21, 'stock': 0, 'sales': 0}]})
        self.invalid({'inventory': []})
        self.invalid({'inventory': DATA['inventory'] * 11})

    def test_unique_record_values_and_missing_identity(self):
        errors = self.invalid({'inventory': DATA['inventory'] * 2})
        self.assertEqual(errors[0]['data_path'], '$.inventory[1].sku')
        self.assertIn('first appears at $.inventory[0]', errors[0]['message'])
        simple = {'type': 'object', 'properties': {'records': {'type': 'array', 'uniqueBy': 'id'}}}
        errors = self.invalid({'records': [{}, {'id': None}, 3]}, simple)
        self.assertEqual(len(errors), 3)
        self.assertTrue(run(SOURCE, {'records': [{'id': True}, {'id': 1}]}, contract=simple)['ok'])
        self.invalid({'records': [{'id': 1}, {'id': 1.0}]}, simple)

    def test_enum_is_structural_and_boolean_is_not_number(self):
        schema = {'properties': {'choice': {'enum': [{'a': [1, True]}]}}}
        self.assertTrue(run(SOURCE, {'choice': {'a': [1.0, True]}}, contract=schema)['ok'])
        self.invalid({'choice': {'a': [True, 1]}}, schema)
        self.invalid({'choice': True}, {'properties': {'choice': {'enum': [1]}}})

    def test_bad_contract_keywords_types_and_bounds(self):
        for contract in ([], True, {'unknown': 1}, {'type': 'date'}, {'type': []},
                         {'type': ['string', 'string']}, {'properties': []},
                         {'properties': {'x': True}}, {'required': 'sku'},
                         {'required': [2]}, {'required': ['x', 'x']},
                         {'additionalProperties': {}}, {'items': []},
                         {'minItems': True}, {'maxLength': -1}, {'minimum': '0'},
                         {'minimum': 2, 'maximum': 1}, {'minItems': 2, 'maxItems': 1},
                         {'enum': []}, {'title': 3}, {'description': []}, {'uniqueBy': ''},
                         {'type': 'string', 'minimum': 0},
                         {'required': ['x'], 'additionalProperties': False}):
            with self.subTest(contract=contract):
                self.invalid(DATA, contract, 'E_CONTRACT')

    def test_unused_invalid_contract_branch_is_rejected(self):
        self.invalid({}, {'properties': {'unused': {'format': 'email'}}}, 'E_CONTRACT')

    def test_contract_limits_and_non_json_values(self):
        nested = {}
        for _ in range(40):
            nested = {'properties': {'child': nested}}
        for contract in ({'description': 'x' * 262145}, nested,
                         {'enum': list(range(10001))}, {'enum': [float('inf')]},
                         {1: {}}, {'description': '\ud800'}, {'enum': [object()]}):
            with self.subTest(kind=type(contract)):
                self.assertEqual(contract_diagnostics(contract)[0]['code'], 'E_CONTRACT')

    def test_diagnostic_limit_and_escaped_paths(self):
        errors = self.invalid({'bad': [-1] * 100},
                              {'properties': {'bad': {'items': {'minimum': 0}}}})
        self.assertEqual(len(errors), 50)
        errors = self.invalid({'odd.key': False}, {'properties': {'odd.key': {'type': 'string'}}})
        self.assertEqual(errors[0]['data_path'], '$["odd.key"]')

    def test_invalid_host_values_with_contract_have_input_diagnostics(self):
        for data in ([], {"value": float("nan")}, {"value": object()}):
            self.invalid(data, {})
        self.assertEqual(run(SOURCE, [])['diagnostics'][0]['code'], 'E_INPUT')

    def test_validation_happens_before_execution(self):
        result = run('propose placed()\nsay "side effect"\nlet broken = 1 / 0', {}, contract=CONTRACT)
        self.assertEqual(result['diagnostics'][0]['code'], 'E_INPUT_DATA')
        self.assertEqual(result['proposals'], [])
        self.assertEqual(result['notes'], [])
        self.assertFalse(check(SOURCE, {}, contract=CONTRACT)['ok'])


class ContractCLITests(unittest.TestCase):
    def test_cli_contract_path_json_and_readable_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            source, data, contract = [directory / name for name in ('program.zs', 'data.json', 'contract.json')]
            source.write_text(SOURCE)
            data.write_text(json.dumps({'inventory': [{'sku': 'A17', 'stock': -1, 'sales': 0}]}))
            contract.write_text(json.dumps(CONTRACT))
            command = [sys.executable, '-m', 'zensigil', 'run', str(source), '--data', str(data), '--contract', str(contract)]
            raw = subprocess.run(command + ['--json'], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(raw.returncode, 1, raw.stderr)
            self.assertEqual(json.loads(raw.stdout)['diagnostics'][0]['data_path'], '$.inventory[0].stock')
            text = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            self.assertIn('$.inventory[0].stock', text.stderr)
            self.assertIn('A17', text.stderr)
            data.write_text(json.dumps(DATA))
            good = subprocess.run(command + ['--json'], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            for invalid in ('{"type":"object","type":"array"}', 'null', '{'):
                contract.write_text(invalid)
                bad = subprocess.run(command + ['--json'], cwd=ROOT, text=True, capture_output=True)
                self.assertEqual(json.loads(bad.stdout)['diagnostics'][0]['code'], 'E_CONTRACT')


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class ContractHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)

    def request(self, body, path='/api/run'):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request('POST', path, json.dumps(body), {'Content-Type': 'application/json'})
        response = connection.getresponse()
        status, parsed = response.status, json.loads(response.read())
        connection.close()
        return status, parsed

    def test_contract_object_and_text_on_run_and_check(self):
        for path in ('/api/run', '/api/check'):
            for field, value in (('contract', CONTRACT), ('contract_text', json.dumps(CONTRACT))):
                with self.subTest(path=path, field=field):
                    status, result = self.request({'source': SOURCE, 'data': DATA, field: value}, path)
                    self.assertEqual(status, 200)
                    self.assertTrue(result['ok'], result)
                    status, result = self.request({'source': SOURCE, 'data_text': '{}', field: value}, path)
                    self.assertEqual(result['diagnostics'][0]['code'], 'E_INPUT_DATA')
                    self.assertEqual(result['diagnostics'][0]['data_path'], '$.inventory')
                    self.assertEqual(result['proposals'], [])
                    self.assertEqual(result['notes'], [])

    def test_bad_contract_text_envelopes_and_unknown_keywords(self):
        for extra in ({'contract': {}, 'contract_text': '{}'}, {'contract': None},
                      {'contract_text': 1}, {'contract_text': 'null'},
                      {'contract_text': '{"type":"object","type":"array"}'},
                      {'contract_text': '{'}, {'contract_text': '{"enum":[NaN]}'},
                      {'contract': {'format': 'email'}}):
            with self.subTest(extra=extra):
                status, result = self.request(dict({'source': SOURCE, 'data': {}}, **extra))
                self.assertEqual(status, 200)
                self.assertFalse(result['ok'])
                self.assertEqual(result['diagnostics'][0]['code'], 'E_CONTRACT')
                self.assertEqual(result['proposals'], [])
                self.assertEqual(result['notes'], [])

    def test_duplicate_input_json_is_still_rejected_before_validation(self):
        status, _ = self.request({'source': SOURCE, 'data_text': '{"a":1,"a":2}', 'contract': {}})
        self.assertEqual(status, 400)

    def test_example_catalog_exposes_sidecar_contracts(self):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request('GET', '/api/examples')
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        examples = json.loads(response.read())
        connection.close()
        by_id = {example['id']: example for example in examples}
        self.assertIsInstance(by_id['stock-review']['contract'], dict)
        self.assertIsNone(by_id['hello']['contract'])
