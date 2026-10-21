"""Transactional replay, portable source, and stream behavior for the REPL."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from zensigil import run
from zensigil.programs import decode_program
from zensigil.repl import MAX_CELLS, Session, cell_source, main


class SessionTests(unittest.TestCase):
    def test_variables_expressions_and_only_new_outputs(self):
        session = Session()
        self.assertTrue(session.submit('var total = 2')['ok'])
        self.assertEqual(session.submit('total + 3')['values'], [5])
        self.assertTrue(session.submit('set total = total * 4')['ok'])
        self.assertEqual(session.submit('total')['values'], [8])
        self.assertEqual(session.last_result['values'], [5, 8])
        self.assertEqual(run(session.source)['values'], [5, 8])
        self.assertEqual(len(session.history), 4)
        self.assertGreater(session.steps_spent, session.last_result['stats']['steps'])
        result = session.submit('say "hello"\npropose review(item: "demo")\n')
        self.assertEqual([item['message'] for item in result['notes']], ['hello'])
        self.assertEqual(len(result['proposals']), 1)
        duplicate = session.submit('propose review(item: "demo")\n')
        self.assertEqual(duplicate['proposals'], [])
        self.assertEqual(duplicate['stats']['duplicates_collapsed'], 1)

    def test_failed_cells_preserve_source_state_and_successful_output(self):
        session = Session(max_steps=1000)
        session.submit('var total = 3\nemit total\n')
        before = (session.source, session.history, session.last_result)
        failed = session.submit('set total = 999\nemit total\nrequire false, "rollback"\n')
        self.assertFalse(failed['ok'])
        self.assertEqual(failed['values'], [])
        self.assertEqual((session.source, session.history, session.last_result), before)
        self.assertEqual(session.submit('total')['values'], [3])
        previous = session.source
        self.assertFalse(session.submit('let broken =')['ok'])
        self.assertEqual(session.source, previous)

    def test_functions_multiline_expressions_and_no_host_evaluation(self):
        session = Session()
        self.assertTrue(session.submit('fn double(n: number) -> number:\n    return n * 2\n')['ok'])
        self.assertEqual(session.submit('double(7)')['values'], [14])
        self.assertEqual(session.submit('[\n  2,\n  3\n]')['values'], [[2, 3]])
        self.assertEqual(session.submit('# Keep expression comment\n3 + 4 # end')['values'], [7])
        for source in ['__import__("os")', '1\n2', 'open("secret")', 'import os']:
            with self.subTest(source=source):
                self.assertFalse(session.submit(source)['ok'])
        self.assertTrue(cell_source('let letter = "emit"').startswith('let '))
        self.assertTrue(cell_source('choose true then 1 otherwise 2').startswith('emit ('))

    def test_later_declarations_never_repair_or_rebind_old_cells(self):
        session = Session(data={'input_name': 7})
        self.assertFalse(session.submit('fn first():\n    return later()\n')['ok'])
        self.assertEqual(session.history, ())
        self.assertTrue(session.submit('fn later():\n    return 42\n')['ok'])
        self.assertEqual(session.submit('later()')['values'], [42])
        session.submit('let old = 3\nemit old\nemit input_name\n')
        previous = (session.source, session.last_result)
        for source in ['fn old():\n    return 99\n', 'fn input_name():\n    return 99\n',
                       'fn later():\n    return 99\n']:
            self.assertFalse(session.submit(source)['ok'])
            self.assertEqual((session.source, session.last_result), previous)

    def test_undo_and_reset_do_not_replay_or_refund_spent_work(self):
        session = Session()
        session.submit('var counter = 1\nemit counter\n')
        prior = session.last_result
        session.submit('set counter = 5\nemit counter\n')
        spent = session.steps_spent
        with patch('zensigil.repl.run', side_effect=AssertionError('Undo executed source')):
            self.assertTrue(session.undo()['ok'])
        self.assertEqual(session.last_result, prior)
        self.assertEqual(session.steps_spent, spent)
        self.assertEqual(session.submit('counter')['values'], [1])
        session.undo()
        session.undo()
        self.assertEqual(session.source, '')
        self.assertFalse(session.undo()['ok'])
        session.submit('1')
        spent = session.steps_spent
        session.reset()
        self.assertEqual(session.source, '')
        self.assertEqual(session.last_result['values'], [])
        self.assertEqual(session.steps_spent, spent)

    def test_fixed_inputs_modules_and_returned_results_cannot_be_mutated_by_caller(self):
        data = {'items': [2, 3]}
        modules = {'math.zs': 'fn double(x):\n    return x * 2\n'}
        session = Session(data, modules)
        data['items'][0] = 999
        modules['math.zs'] = 'invalid'
        self.assertTrue(session.submit('use "math.zs"')['ok'])
        result = session.submit('map(items, double)')
        self.assertEqual(result['values'], [[4, 6]])
        result['values'][0][0] = 999
        snapshot = session.last_result
        snapshot['values'][0][0] = 999
        self.assertEqual(session.last_result['values'], [[4, 6]])
        session.reset()
        self.assertEqual(session.submit('items')['values'], [[2, 3]])

    def test_cumulative_work_budget_counts_replay_and_failed_attempts(self):
        session = Session(max_steps=5, max_total_steps=12)
        self.assertTrue(session.submit('emit 1')['ok'])
        self.assertEqual(session.steps_spent, 2)
        self.assertTrue(session.submit('emit 2')['ok'])
        self.assertEqual(session.steps_spent, 6)
        before = session.source
        limited = session.submit('while true:\n    continue\n')
        self.assertFalse(limited['ok'])
        self.assertEqual(limited['diagnostics'][0]['code'], 'E_LIMIT')
        self.assertEqual(session.source, before)
        self.assertEqual(session.remaining_steps, 0)
        self.assertEqual(session.submit('emit 3')['diagnostics'][0]['code'], 'E_REPL_BUDGET')
        session.undo()
        session.reset()
        self.assertEqual(session.remaining_steps, 0)
        for settings in [dict(max_steps=True), dict(max_steps=0), dict(max_total_steps=1), dict(max_total_steps=10**9)]:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                Session(**settings)

    def test_source_cells_and_validation_limits(self):
        session = Session()
        self.assertFalse(session.submit('x' * 65537)['ok'])
        self.assertFalse(session.submit('\ud800')['ok'])
        self.assertFalse(session.submit(42)['ok'])
        self.assertEqual(session.submit(' \n')['status'], 'empty')
        self.assertEqual(session.history, ())
        self.assertTrue(session.submit('#' + 'x' * 40000)['ok'])
        self.assertFalse(session.submit('#' + 'x' * 40000)['ok'])
        session.reset()
        for unused in range(MAX_CELLS):
            self.assertTrue(session.submit('# comment')['ok'])
        self.assertFalse(session.submit('# one too many')['ok'])
        for data in [[], {'bad': float('inf')}, {'say': 1}]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                Session(data)

    def test_load_only_explicit_source_and_save_new_portable_program(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            loaded = root / 'source with spaces.zs'
            loaded.write_text('var total = 6\nemit total\n', encoding='utf-8')
            session = Session(data={'sample': [1]})
            self.assertEqual(session.load(loaded)['values'], [6])
            saved = root / 'session.sigil.json'
            self.assertTrue(session.save(saved)['ok'])
            portable = decode_program(saved.read_text())
            self.assertEqual(portable['source'], session.source)
            self.assertEqual(json.loads(portable['data_text']), {'sample': [1]})
            self.assertEqual(run(portable['source'], json.loads(portable['data_text']), modules=portable['modules'])['values'], [6])
            original = saved.read_bytes()
            self.assertFalse(session.save(saved)['ok'])
            self.assertEqual(saved.read_bytes(), original)
            self.assertEqual(loaded.read_text(), 'var total = 6\nemit total\n')
            self.assertFalse(session.save(loaded)['ok'])
            self.assertFalse(session.load(saved)['ok'])
            missing = root / 'missing.zs'
            self.assertFalse(session.load(missing)['ok'])
            loaded.write_text('use "missing.zs"\n')
            self.assertFalse(session.load(loaded)['ok'])  # No implicit file discovery.

    def test_execution_interrupt_is_transactional_and_charges_reserved_work(self):
        session = Session(max_steps=20, max_total_steps=100)
        session.submit('emit 7')
        before = (session.source, session.last_result)
        spent = session.steps_spent
        with patch('zensigil.repl.run', side_effect=KeyboardInterrupt):
            interrupted = session.submit('emit 8')
        self.assertEqual(interrupted['status'], 'cancelled')
        self.assertEqual(interrupted['diagnostics'][0]['code'], 'E_REPL_CANCELLED')
        self.assertEqual((session.source, session.last_result), before)
        self.assertEqual(session.steps_spent, spent + 21)
        self.assertEqual(session.submit('emit 9')['values'], [9])

    def test_replay_prefix_guard_rejects_changed_prior_output(self):
        session = Session()
        session.submit('emit true')
        before = (session.source, session.last_result)
        changed = copy.deepcopy(session.last_result)
        changed['values'] = [1, 2]  # Python considers true == 1; language output does not.
        with patch('zensigil.repl.run', return_value=changed):
            result = session.submit('emit 2')
        self.assertFalse(result['ok'])
        self.assertEqual(result['diagnostics'][0]['code'], 'E_REPL_REPLAY')
        self.assertEqual((session.source, session.last_result), before)


class StreamTests(unittest.TestCase):
    def repl(self, text, **kwargs):
        stdout, stderr = io.StringIO(), io.StringIO()
        code = main(stdin=io.StringIO(text), stdout=stdout, stderr=stderr, **kwargs)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_piped_multiline_blocks_blank_submission_and_eof(self):
        code, out, err = self.repl('fn double(x):\n    let y = x * 2\n    return y\n\nvar amount = 3\ndouble(amount)\nwhen true:\n    say "done"\n')
        self.assertEqual(code, 0, err)
        self.assertEqual(out, 'VALUE 6\nNOTE done\n')
        self.assertEqual(err, '')
        self.assertNotIn('zs>', out)
        code, out, err = self.repl('when true:\n')
        self.assertEqual(code, 1)
        self.assertIn('E_SYNTAX', err)
        self.assertEqual(out, '')

    def test_commands_errors_and_recovery(self):
        code, out, err = self.repl(':help\n1\n:undo\n:show\n:reset\n:bad\nlet broken =\n2\n:quit\n999\n')
        self.assertEqual(code, 1)
        self.assertIn('Each accepted cell replays', out)
        self.assertIn('VALUE 1\n', out)
        self.assertIn('VALUE 2\n', out)
        self.assertNotIn('999', out)
        self.assertIn('(empty session)', out)
        self.assertIn('E_REPL_COMMAND', err)
        self.assertIn('E_SYNTAX', err)
        self.assertEqual(self.repl(':quit extra\n:quit\n')[0], 1)

    def test_quoted_load_save_paths_and_pending_command(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'some code.zs'
            target = Path(folder) / 'saved code.sigil.json'
            source.write_text('emit 12\n')
            code, out, err = self.repl(f':load "{source}"\n:save "{target}"\n:quit\n')
            self.assertEqual(code, 0, err)
            self.assertIn('VALUE 12', out)
            self.assertTrue(target.is_file())
        code, out, err = self.repl('fn work():\n:show\n    return 3\n\nwork()\n')
        self.assertEqual(code, 1)
        self.assertIn('Finish the pending cell', err)
        self.assertEqual(out, 'VALUE 3\n')
        self.assertEqual(self.repl('fn unfinished():\n:quit\n'), (0, '', ''))

    def test_ctrl_c_cancels_pending_cell_and_eof_is_clean(self):
        class Interrupted:
            def __init__(self):
                self.lines = iter(['fn ignored():\n', KeyboardInterrupt(), '4\n', ''])
            def readline(self, limit):
                value = next(self.lines)
                if isinstance(value, BaseException):
                    raise value
                return value
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(main(stdin=Interrupted(), stdout=out, stderr=err), 0)
        self.assertEqual(out.getvalue(), 'VALUE 4\n')
        self.assertIn('Cell cancelled', err.getvalue())
        self.assertEqual(self.repl(''), (0, '', ''))
        self.assertEqual(self.repl('', data=[])[0], 2)

    def test_large_physical_line_tail_is_never_executed(self):
        code, out, err = self.repl('#' + 'x' * 70000 + 'emit 999\n5\n')
        self.assertEqual(code, 1)
        self.assertEqual(out, 'VALUE 5\n')
        self.assertIn('E_LIMIT', err)
        code, out, err = self.repl('when true:\n' + '    # ' + 'x' * 70000 + '\n    emit 999\n\n6\n')
        self.assertEqual(code, 1)
        self.assertEqual(out, 'VALUE 6\n')


if __name__ == '__main__':
    unittest.main()
