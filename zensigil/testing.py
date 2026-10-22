"""Execute explicit test blocks independently, with shared per-suite work budget."""
import json
from .runtime import Runtime
from .errors import SigilError

MAX_TEST_RESULT_BYTES = 1_048_576
_RESULT_RESERVE = 4096


def _encoded_size(value, remaining):
    """Stop measuring once a compact JSON value exceeds the available budget."""
    size = 0
    encoder = json.JSONEncoder(ensure_ascii=True, allow_nan=False, separators=(',', ':'))
    for piece in encoder.iterencode(value):
        size += len(piece.encode('ascii'))
        if size > remaining:
            return size
    return size


def _limit_case(steps=0):
    return {'name': 'Test output limit', 'source_name': '<test output>', 'ok': False,
            'diagnostics': [{'code': 'E_TEST_LIMIT',
                'message': 'Test output exceeds 1 MiB. Run fewer tests or shorten failure messages.',
                'line': 1, 'column': 1, 'source_line': ''}], 'steps': steps}


class TestResultBudget:
    """Bound finalized cases and their duplicated top-level diagnostics.

    A fixed reserve covers the result envelope and one short failure case. A
    rejected case is replaced by that failure case, never silently discarded.
    Callers must stop when stopped is true. This object can span several roots.
    """
    def __init__(self):
        self.bytes = 0
        self.stopped = False

    def add(self, case):
        remaining = MAX_TEST_RESULT_BYTES - _RESULT_RESERVE - self.bytes
        cost = _encoded_size(case, remaining)
        # The public result repeats every diagnostic outside the case array.
        cost += _encoded_size(case.get('diagnostics', []), max(0, remaining - cost)) + 2
        if cost > remaining:
            self.stopped = True
            return _limit_case(case.get('steps', 0))
        self.bytes += cost
        return case


def bound_test_result(result):
    """Final guard after all API-specific fields and source lines are attached."""
    if _encoded_size(result, MAX_TEST_RESULT_BYTES) <= MAX_TEST_RESULT_BYTES:
        return result
    case = _limit_case()
    return {'ok': False, 'version': result.get('version', ''), 'mode': 'test',
            'tests': [case], 'total': 1, 'passed': 0, 'failed': 1,
            'diagnostics': case['diagnostics'], 'proposals': [], 'notes': [], 'values': [],
            'stats': {'steps': result.get('stats', {}).get('steps', 0), 'passed': 0, 'failed': 1},
            'stopped_early': True}


def run_test_program(program, data, source, max_steps=100000, *, result_budget=None,
                     prepare_case=None):
    runtime = Runtime(program, data, max_steps=max_steps)
    budget = TestResultBudget() if result_budget is None else result_budget
    results = []
    stopped_early = False
    for node in program:
        if node.kind != 'test':
            continue
        before = runtime.steps
        try:
            runtime.child_block(node.parts[1], [], None)
            case = {'name': node.parts[0], 'source_name': node.token.source_name or '<program>', 'ok': True, 'diagnostics': [],
                    'steps': runtime.steps - before}
        except SigilError as error:
            case = {'name': node.parts[0], 'source_name': node.token.source_name or '<program>', 'ok': False,
                    'diagnostics': [error.as_dict(source)], 'steps': runtime.steps - before}
        if prepare_case is not None:
            case = prepare_case(case)
        results.append(budget.add(case))
        if budget.stopped or any(item['code'] == 'E_LIMIT' for item in case['diagnostics']):
            stopped_early = True
            break
    return {'ok': all(item['ok'] for item in results), 'tests': results, 'stopped_early': stopped_early,
            'stats': {'steps': runtime.steps, 'passed': sum(item['ok'] for item in results),
                      'failed': sum(not item['ok'] for item in results)}}
