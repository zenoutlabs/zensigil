"""Execute explicit test blocks independently, with shared per-suite work budget."""
from .runtime import Runtime
from .errors import SigilError


def run_test_program(program, data, source, max_steps=100000):
    runtime = Runtime(program, data, max_steps=max_steps)
    results = []
    for node in program:
        if node.kind != 'test':
            continue
        before = runtime.steps
        try:
            runtime.child_block(node.parts[1], [], None)
            results.append({'name': node.parts[0], 'source_name': node.token.source_name or '<program>', 'ok': True, 'diagnostics': [],
                            'steps': runtime.steps - before})
        except SigilError as error:
            results.append({'name': node.parts[0], 'source_name': node.token.source_name or '<program>', 'ok': False,
                            'diagnostics': [error.as_dict(source)], 'steps': runtime.steps - before})
            if error.code == 'E_LIMIT':
                break
    return {'ok': all(item['ok'] for item in results), 'tests': results,
            'stats': {'steps': runtime.steps, 'passed': sum(item['ok'] for item in results),
                      'failed': sum(not item['ok'] for item in results)}}
