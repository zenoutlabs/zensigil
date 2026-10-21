import copy
import json
from pathlib import Path
import unittest
from zensigil import run

EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


class StockReviewTests(unittest.TestCase):
    def setUp(self):
        self.source = (EXAMPLES / 'stock-review.zs').read_text()
        self.data = json.loads((EXAMPLES / 'stock-review.json').read_text())
        self.contract = json.loads((EXAMPLES / 'stock-review.contract.json').read_text())

    def preview(self):
        return run(self.source, self.data, contract=self.contract)

    def test_expected_proposals_and_explanations(self):
        result = self.preview()
        self.assertTrue(result['ok'], result)
        fields = [p['fields'] for p in result['proposals']]
        self.assertEqual([(f['sku'], f['quantity']) for f in fields], [('A17', 105), ('B24', 54)])
        self.assertEqual(fields[0]['explanation'], 'A17 has about 3.75 days of stock, below the 14-day review threshold. Propose 105 units to reach at least 30 days.')
        self.assertEqual(fields[0]['evidence'], [
            '15 units / 4 average daily sales = about 3.75 days of stock',
            'Round up (4 average daily sales * 30 target days - 15 units) = 105 units'])
        self.assertEqual(len(result['notes']), 3)

    def test_threshold_boundary_and_zero_sales(self):
        self.data['policy']['review_below_days'] = 3
        result = self.preview()
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['proposals'], [])

        self.assertEqual(len(result['notes']), 5)
        self.data['inventory'][0]['daily_sales'] = 0
        result = self.preview()
        self.assertTrue(result['ok'], result)
        self.assertIn('average daily sales is zero', result['notes'][0]['message'])

    def test_missing_optional_sales_is_explained(self):
        del self.data['inventory'][3]['daily_sales']
        result = self.preview()
        self.assertTrue(result['ok'], result)
        self.assertTrue(any('D09: needs sales data' in n['message'] for n in result['notes']))

    def test_invalid_product_blocks_the_whole_review(self):
        self.data['inventory'][2]['stock'] = -1
        self.data['inventory'][3]['daily_sales'] = 'unknown'
        result = self.preview()
        self.assertFalse(result['ok'])
        self.assertEqual(result['proposals'], [])
        self.assertEqual(result['notes'], [])
        self.assertEqual({d['data_path'] for d in result['diagnostics']}, {'$.inventory[2].stock', '$.inventory[3].daily_sales'})

    def test_duplicate_sku_is_input_error(self):
        self.data['inventory'].append(copy.deepcopy(self.data['inventory'][0]))
        result = self.preview()
        self.assertFalse(result['ok'])
        self.assertTrue(any('unique' in d['message'].lower() or 'duplicate' in d['message'].lower() for d in result['diagnostics']))

    def test_invalid_policy_relationship(self):
        self.data['policy']['target_days'] = 7
        result = self.preview()
        self.assertFalse(result['ok'])
        self.assertEqual(result['diagnostics'][0]['code'], 'E_REQUIRE')
        self.assertIn('Target days must be at least', result['diagnostics'][0]['message'])
        self.assertEqual(result['proposals'], [])

    def test_round_up_and_determinism(self):
        self.data['inventory'][0]['daily_sales'] = 4.01
        result = self.preview()
        self.assertEqual(result['proposals'][0]['fields']['quantity'], 106)
        self.assertEqual(result['proposals'][0]['fields']['evidence'][1], 'Round up (4.01 average daily sales * 30 target days - 15 units) = 106 units')
        self.assertEqual(result, self.preview())

    def test_decimal_sales_do_not_add_a_phantom_unit(self):
        for daily, target in ((0.14, 50), (0.07, 100)):
            with self.subTest(daily=daily, target=target):
                self.data['policy']['target_days'] = target
                self.data['inventory'] = [{'sku': 'X', 'stock': 0, 'daily_sales': daily, 'discontinued': False}]
                result = self.preview()
                self.assertTrue(result['ok'], result)
                self.assertEqual(result['proposals'][0]['fields']['quantity'], 7)

    def test_decimal_threshold_is_strict_at_the_exact_boundary(self):
        self.data['policy'] = {'review_below_days': 50, 'target_days': 100}
        self.data['inventory'] = [{'sku': 'X', 'stock': 7, 'daily_sales': 0.14, 'discontinued': False}]
        result = self.preview()
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['proposals'], [])
        self.assertIn('about 50.0 days', result['notes'][0]['message'])

    def test_full_supported_batch_fits_runtime_budget(self):
        self.data['inventory'] = [{'sku': f'X-{i}', 'stock': 0, 'daily_sales': 1, 'discontinued': False} for i in range(400)]
        result = self.preview()
        self.assertTrue(result['ok'], result)
        self.assertEqual(len(result['proposals']), 400)
        self.assertLess(result['stats']['steps'], 100000)
        self.data['inventory'].append({'sku': 'X-400', 'stock': 0, 'daily_sales': 1, 'discontinued': False})
        self.assertFalse(self.preview()['ok'])

    def test_noncommerce_uses_the_same_contract_engine(self):
        source = (EXAMPLES / 'support.zs').read_text()
        data = json.loads((EXAMPLES / 'support.json').read_text())
        contract = json.loads((EXAMPLES / 'support.contract.json').read_text())
        result = run(source, data, contract=contract)
        self.assertTrue(result['ok'], result)
        fields = result['proposals'][0]['fields']
        self.assertEqual(fields['ticket_id'], 'T-01')
        self.assertIn('7 hours', fields['explanation'])
        data['tickets'][0]['waiting_hours'] = -1
        result = run(source, data, contract=contract)
        self.assertFalse(result['ok'])
        self.assertEqual(result['diagnostics'][0]['data_path'], '$.tickets[0].waiting_hours')
