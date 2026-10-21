"""Proposal contracts validate reviewable output without executing actions."""
import copy
import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from zensigil import __version__, check, run
from zensigil.proposals import proposal_contract_diagnostics
from zensigil.server import Handler

CONTRACT = {
    "review": {
        "type": "object", "required": ["count", "explanation"], "additionalProperties": False,
        "properties": {"count": {"type": "integer", "minimum": 1},
                       "explanation": {"type": "string", "minLength": 1},
                       "evidence": {"type": "array", "items": {"type": "string"}}}}}
GOOD = 'propose review(count: 2, explanation: "Two places remain", evidence: ["10 - 8 = 2"])'


class ProposalContractTests(unittest.TestCase):
    def invalid(self, source, contract=CONTRACT, code="E_PROPOSAL"):
        result = run(source, {}, proposal_contract=contract)
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['proposals'], [])
        self.assertEqual(result['notes'], [])
        self.assertTrue(result['diagnostics'])
        self.assertTrue(all(d['code'] == code for d in result['diagnostics']), result)
        self.assertTrue(all(d['output_path'].startswith('$') for d in result['diagnostics']))
        return result['diagnostics']

    def test_valid_output_retains_original_fields_identity_and_input(self):
        contract = copy.deepcopy(CONTRACT)
        expected = run(GOOD, {})
        actual = run(GOOD, {}, proposal_contract=contract)
        self.assertEqual(actual, expected)
        self.assertEqual(contract, CONTRACT)
        self.assertEqual(actual['version'], __version__)

    def test_omitted_contract_open_actions_and_empty_contract_closed_actions(self):
        self.assertTrue(run(GOOD, {}, proposal_contract=None)['ok'])
        self.invalid(GOOD, {})
        self.assertTrue(run('say "nothing proposed"', {}, proposal_contract={})['ok'])
        self.assertEqual(self.invalid('propose unlisted(value: 1)')[0]['output_path'], '$.proposals[0].action')

    def test_missing_wrong_extra_and_nested_fields(self):
        cases = [('propose review(count: 2)', '.explanation'),
                 ('propose review(count: "2", explanation: "Why")', '.count'),
                 ('propose review(count: 2, explanation: "Why", extra: 1)', '.extra'),
                 ('propose review(count: 2, explanation: "Why", evidence: [1])', '.evidence[0]'),
                 ('propose review(count: 0, explanation: "")', '.count')]
        for source, suffix in cases:
            with self.subTest(source=source):
                self.assertEqual(self.invalid(source)[0]['output_path'], '$.proposals[0].fields' + suffix)

    def test_boolean_is_not_integer_or_numeric_enum(self):
        self.invalid('propose review(count: true, explanation: "Why")')
        schema = {'review': {'type': 'object', 'properties': {'count': {'enum': [1]}}}}
        self.invalid('propose review(count: true)', schema)
        self.assertTrue(run('propose review(count: 1)', {}, proposal_contract=schema)['ok'])

    def test_all_or_nothing_and_source_location(self):
        source = 'say "would have been shown"\n' + GOOD + '\nrule "Capacity":\n    propose review(count: false, explanation: "Wrong")'
        errors = self.invalid(source)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['output_path'], '$.proposals[1].fields.count')
        self.assertEqual(errors[0]['action'], 'review')
        self.assertEqual((errors[0]['line'], errors[0]['column']), (4, 5))
        self.assertEqual(errors[0]['source_line'], source.splitlines()[3])

    def test_check_validates_definitions_but_does_not_run_or_guarantee_output(self):
        source = 'propose unlisted(value: 1)\nlet fail = 1 / 0'
        checked = check(source, {}, proposal_contract=CONTRACT)
        self.assertTrue(checked['ok'], checked)
        self.assertTrue(checked['proposal_contract_checked'])
        self.assertFalse(checked['proposals_checked'])
        self.assertFalse(check(GOOD)['proposal_contract_checked'])
        broken = copy.deepcopy(CONTRACT)
        broken['unused'] = {'type': 'object', 'properties': {'field': {'format': 'email'}}}
        result = check(source, {}, proposal_contract=broken)
        self.assertFalse(result['ok'])
        self.assertEqual(result['diagnostics'][0]['output_path'], '$.unused.properties.field.format')

    def test_malformed_definitions_rejected_before_execution(self):
        cases = [[], True, {'bad-name': {'type': 'object'}}, {'when': {'type': 'object'}},
                 {'x': []}, {'x': {}}, {'x': {'type': 'string'}},
                 {'x': {'type': ['object', 'null']}}, {'x': {'type': 'object', 'properties': {'unused': False}}}]
        for contract in cases:
            with self.subTest(contract=contract):
                self.invalid('let broken = 1 / 0', contract, 'E_PROPOSAL_CONTRACT')
        self.assertTrue(run('propose x(a: 1)', {}, proposal_contract={'x': {'type': ['object']}})['ok'])

    def test_mapping_size_and_non_json_python_values(self):
        large = {name: {'type': 'object', 'description': 'x' * 140000} for name in ('one', 'two')}
        for contract in (large, {'x': {'type': 'object', 'description': 'x' * 262145}},
                         {'x': {'type': 'object', 'enum': [float('inf')]}}, {1: {}},
                         {'x': {'type': 'object', 'description': '\ud800'}},
                         {'x': {'type': 'object', 'enum': [object()]}}):
            with self.subTest(kind=type(contract)):
                errors = proposal_contract_diagnostics(contract)
                self.assertEqual(errors[0]['code'], 'E_PROPOSAL_CONTRACT')
        cyclic = {'type': 'object'}
        cyclic['properties'] = {'self': cyclic}
        self.assertTrue(proposal_contract_diagnostics({'x': cyclic}))

    def test_diagnostic_limit_across_actions_and_proposals(self):
        malformed = {'action_' + str(i): {'type': 'object', 'bad': True} for i in range(60)}
        self.assertEqual(len(proposal_contract_diagnostics(malformed)), 50)
        source = 'for value in values:\n    propose review(count: value)'
        result = run(source, {'values': list(range(60))}, proposal_contract=CONTRACT)
        self.assertFalse(result['ok'])
        self.assertEqual(len(result['diagnostics']), 50)
        self.assertEqual(result['proposals'], [])

    def test_large_allowed_set_at_full_proposal_limit(self):
        schema = {'suggest': {'type': 'object', 'properties': {
            'id': {'type': 'integer'}, 'choice': {'enum': list(range(8500))}}}}
        source = 'for id in ids:\n    propose suggest(id: id, choice: 8499)'
        result = run(source, {'ids': list(range(1000))}, proposal_contract=schema)
        self.assertTrue(result['ok'], result)
        self.assertEqual(len(result['proposals']), 1000)
        self.assertEqual(result['proposals'][-1]['fields'], {'id': 999, 'choice': 8499})

    def test_enum_matches_are_type_aware_and_do_not_persist_across_runs(self):
        allowed = {'nested': [1, True]}
        schema = {'review': {'type': 'object', 'properties': {'choice': {'enum': [allowed]}}}}
        source = 'for choice in choices:\n    propose review(choice: choice)'
        good = {'choices': [{'nested': [1.0, True]}, {'nested': [1, True]}]}
        self.assertTrue(run(source, good, proposal_contract=schema)['ok'])
        # Changing a definition between runs must not reuse old enum membership.
        allowed['nested'] = [True, 1]
        rejected = run(source, good, proposal_contract=schema)
        self.assertFalse(rejected['ok'])
        self.assertEqual(rejected['proposals'], [])
        self.assertEqual(rejected['diagnostics'][0]['output_path'], '$.proposals[0].fields.choice')
        self.assertTrue(run(source, {'choices': [{'nested': [True, 1]}]}, proposal_contract=schema)['ok'])

    def test_input_contract_and_require_still_gate_execution(self):
        input_contract = {'type': 'object', 'required': ['items']}
        result = run(GOOD, {}, contract=input_contract, proposal_contract=CONTRACT)
        self.assertEqual(result['diagnostics'][0]['code'], 'E_INPUT_DATA')
        result = run('require false, "Stop"\n' + GOOD, {}, proposal_contract=CONTRACT)
        self.assertEqual(result['diagnostics'][0]['code'], 'E_REQUIRE')


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class ProposalHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request('GET' if body is None else 'POST', path,
                           body=None if body is None else json.dumps(body),
                           headers=headers or {'Content-Type': 'application/json'})
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def test_contract_object_text_and_check(self):
        for key, value in [('proposal_contract', CONTRACT), ('proposal_contract_text', json.dumps(CONTRACT))]:
            for route in ('/api/run', '/api/check'):
                with self.subTest(key=key, route=route):
                    status, body = self.request(route, {'source': GOOD, 'data': {}, key: value})
                    self.assertEqual(status, 200)
                    self.assertTrue(body['ok'], body)
        status, body = self.request('/api/run', {'source': 'say "note"\npropose unknown(a: 1)', 'data': {}, 'proposal_contract': {}})
        self.assertFalse(body['ok'])
        self.assertEqual(body['notes'], [])
        self.assertEqual(body['diagnostics'][0]['code'], 'E_PROPOSAL')

    def test_http_rejects_malformed_null_duplicate_and_oversized_contract(self):
        cases = [{'proposal_contract': None}, {'proposal_contract': []},
                 {'proposal_contract': {}, 'proposal_contract_text': '{}'},
                 {'proposal_contract_text': None}, {'proposal_contract_text': ''},
                 {'proposal_contract_text': '{"x":{},"x":{}}'},
                 {'proposal_contract_text': 'null'}, {'proposal_contract_text': '{'},
                 {'proposal_contract_text': ' ' * 262145},
                 {'proposal_contract_text': '{"x":{"type":"object","enum":[NaN]}}'}]
        for extra in cases:
            with self.subTest(keys=list(extra)):
                status, body = self.request('/api/run', dict({'source': GOOD, 'data': {}}, **extra))
                self.assertEqual(status, 200)
                self.assertFalse(body['ok'])
                self.assertEqual(body['diagnostics'][0]['code'], 'E_PROPOSAL_CONTRACT')
                self.assertEqual(body['diagnostics'][0]['output_path'], '$')
                self.assertEqual(body['proposals'], [])

    def test_health_version_and_host_guard(self):
        status, body = self.request('/api/health')
        self.assertEqual(status, 200)
        self.assertEqual(body, {'status': 'ok', 'version': __version__})
        self.assertEqual(self.request('/api/health', headers={'Host': 'external.test'})[0], 403)

    def test_example_contract_sidecars_and_beginner_order(self):
        status, body = self.request('/api/examples')
        self.assertEqual(status, 200)
        self.assertEqual(body[0]['id'], 'hello')
        self.assertTrue(all('proposal_contract' in example for example in body))
        reading = next(example for example in body if example['id'] == 'reading-list')
        self.assertIsInstance(reading['proposal_contract'], dict)


if __name__ == '__main__':
    unittest.main()
