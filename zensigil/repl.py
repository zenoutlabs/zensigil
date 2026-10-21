"""Transactional source-replay REPL. ZenSigil source never reaches Python eval."""
import copy
import json
from pathlib import Path
import shlex
import sys

from . import __version__, check, run
from .errors import SigilError
from .programs import FORMAT, LANGUAGE_VERSION, encode_program, write_text
from .syntax import Parser, parse

MAX_SOURCE_BYTES = 65536
MAX_CELLS = 256
OUTPUTS = ('values', 'notes', 'proposals')
HELP = '''Enter ZenSigil statements or an expression. Expressions display their value.
Finish an indented block or multiline cell with a blank line.
:help           Show these commands.
:show           Show the accumulated runnable source.
:undo           Remove the last successful cell; no program is executed.
:reset          Clear successful cells; keep inputs, modules and work budget.
:load FILE.zs   Append one explicit UTF-8 source file as a cell.
:save FILE.sigil.json  Save a new portable program; existing files are never replaced.
:quit           Exit, discarding an unfinished cell.
Paths containing spaces may be quoted. Commands do not expand shell syntax.
Each accepted cell replays successful source with fixed input and supplied modules.
Only new output is shown. A failed cell preserves prior source and output.
'''


def _failure(code, message, source='', line=1, column=1):
    diagnostic = SigilError(code, message, line, column).as_dict(source)
    return {'ok': False, 'version': __version__, 'mode': 'repl', 'status': 'rejected',
            'values': [], 'notes': [], 'proposals': [], 'diagnostics': [diagnostic]}


def _empty():
    return {'ok': True, 'version': __version__, 'mode': 'preview', 'values': [],
            'notes': [], 'proposals': [], 'diagnostics': [],
            'stats': {'steps': 0, 'duplicates_collapsed': 0}}


def cell_source(source, expression=True):
    """Use the ZenSigil parser to distinguish complete statements from one expression."""
    if type(source) is not str:
        raise SigilError('E_INPUT', 'A REPL cell must be source text.')
    if len(source.encode('utf-8')) > MAX_SOURCE_BYTES:
        raise SigilError('E_LIMIT', 'A REPL cell allows at most 64 KiB of UTF-8 source.')
    if not source.strip():
        return ''
    text = source if source.endswith('\n') else source + '\n'
    try:
        parse(text)
        return text
    except SigilError as original:
        if not expression:
            raise
        try:
            parser = Parser(text)
            parser.expression()
            parser.need('NEWLINE')
            parser.need('EOF')
        except SigilError:
            raise original
        # Parentheses permit comments and already bracketed multiline expressions.
        wrapped = 'emit (\n' + text + ')\n'
        parse(wrapped)
        return wrapped


def _continues(source):
    """An unfinished bracket or a block waiting for indentation needs more input."""
    try:
        parser = Parser(source)
    except SigilError as error:
        return error.code == 'E_SYNTAX' and error.message == 'Unclosed bracket or parenthesis.'
    try:
        nodes = parser.program()
        return bool(nodes and nodes[0].kind in {'fn', 'when', 'for', 'while', 'rule', 'test'})
    except SigilError as error:
        return parser.current.kind == 'EOF' and "Expected 'INDENT'" in error.message


class Session:
    """A fixed-input REPL implemented by bounded replay, not an incremental VM.

    Failed attempts may consume the remaining work allowance, but never commit
    program text, variable changes or output. Undo and reset do not refund work.
    """
    def __init__(self, data=None, modules=None, *, max_steps=100000, max_total_steps=1000000):
        if type(max_steps) is not int or not 1 <= max_steps <= 1000000:
            raise ValueError('max_steps must be an integer from 1 to 1000000.')
        if type(max_total_steps) is not int or not 2 <= max_total_steps <= 10000000:
            raise ValueError('max_total_steps must be an integer from 2 to 10000000.')
        actual = {} if data is None else data
        supplied = {} if modules is None else modules
        validation = check('', actual, modules=supplied)
        if not validation['ok']:
            raise ValueError(validation['diagnostics'][0]['message'])
        self._data = copy.deepcopy(actual)
        self._modules = dict(supplied)
        self.max_steps, self.max_total_steps = max_steps, max_total_steps
        self.steps_spent = 0
        self._cells, self._checkpoints = [], []
        self._result = _empty()

    @property
    def source(self):
        return ''.join(self._cells)

    @property
    def history(self):
        return tuple(self._cells)

    @property
    def last_result(self):
        return copy.deepcopy(self._result)

    @property
    def remaining_steps(self):
        return max(0, self.max_total_steps - self.steps_spent)

    def _annotate(self, result, status):
        result = copy.deepcopy(result)
        result.update(mode='repl', status=status, cell_count=len(self._cells),
                      steps_spent=self.steps_spent, remaining_steps=self.remaining_steps)
        return result

    def submit(self, source, *, expression=True):
        """Commit one valid successful cell; return only its newly produced output."""
        try:
            cell = cell_source(source, expression)
        except SigilError as error:
            return self._annotate(_failure(error.code, error.message, source if type(source) is str else '',
                                           error.line, error.column), 'rejected')
        except (UnicodeError, RecursionError):
            return self._annotate(_failure('E_LIMIT', 'Source encoding or nesting exceeds REPL limits.'), 'rejected')
        except KeyboardInterrupt:
            return self._annotate(_failure('E_REPL_CANCELLED', 'Cell cancelled; previous source and output are unchanged.'), 'cancelled')
        if not cell:
            return self._annotate(_empty(), 'empty')
        if len(self._cells) >= MAX_CELLS:
            return self._annotate(_failure('E_LIMIT', 'A session allows at most 256 successful cells; save or reset it.'), 'rejected')
        candidate = self.source + cell
        if len(candidate.encode('utf-8')) > MAX_SOURCE_BYTES:
            return self._annotate(_failure('E_LIMIT', 'Accumulated REPL source exceeds 64 KiB; save or reset it.'), 'rejected')
        try:
            checked = check(candidate, self._data, modules=self._modules)
        except KeyboardInterrupt:
            return self._annotate(_failure('E_REPL_CANCELLED', 'Cell cancelled; previous source and output are unchanged.'), 'cancelled')
        if not checked['ok']:
            return self._annotate(checked, 'rejected')
        # Reserve one step for the runtime's tick which detects exhaustion.
        allowance = min(self.max_steps, self.remaining_steps - 1)
        if allowance < 1:
            return self._annotate(_failure('E_REPL_BUDGET', 'The session work budget is exhausted. Save and start a new session.'), 'rejected')
        try:
            result = run(candidate, self._data, modules=self._modules, max_steps=allowance)
        except KeyboardInterrupt:
            self.steps_spent += allowance + 1
            return self._annotate(_failure('E_REPL_CANCELLED', 'Cell cancelled; previous source and output are unchanged.'), 'cancelled')
        if not result['ok']:
            # The public failure contract has no partial step count. Charging the
            # whole reservation conservatively bounds work across repeated failures.
            self.steps_spent += allowance + 1
            return self._annotate(result, 'rejected')
        self.steps_spent += result['stats']['steps']
        # Frozen inputs/modules, immutable declarations and checked bindings make
        # appends deterministic. Check that promise before slicing old output away.
        for key in OUTPUTS:
            before = self._result[key]
            prefix = result[key][:len(before)]
            if json.dumps(prefix, sort_keys=True) != json.dumps(before, sort_keys=True):
                return self._annotate(_failure('E_REPL_REPLAY', 'This cell would change prior output. Start a new session instead.'), 'rejected')
        checkpoint = {key: len(self._result[key]) for key in OUTPUTS}
        checkpoint['stats'] = dict(self._result['stats'])
        delta = copy.deepcopy(result)
        for key in OUTPUTS:
            delta[key] = result[key][checkpoint[key]:]
        delta['stats']['duplicates_collapsed'] -= self._result['stats']['duplicates_collapsed']
        self._checkpoints.append(checkpoint)
        self._cells.append(cell)
        self._result = result
        return self._annotate(delta, 'accepted')

    def undo(self):
        if not self._cells:
            return self._annotate(_failure('E_REPL_HISTORY', 'There is no successful cell to undo.'), 'rejected')
        checkpoint = self._checkpoints.pop()
        self._cells.pop()
        for key in OUTPUTS:
            self._result[key] = self._result[key][:checkpoint[key]]
        self._result['stats'] = checkpoint['stats']
        return self._annotate(_empty(), 'undone')

    def reset(self):
        self._cells.clear()
        self._checkpoints.clear()
        self._result = _empty()
        return self._annotate(_empty(), 'reset')

    def load(self, filename):
        """Read only the explicitly named source; imports use the frozen module map."""
        try:
            path = Path(filename)
            if path.suffix != '.zs' or not path.is_file():
                raise ValueError('Load an existing regular .zs source file.')
            with path.open('rb') as handle:
                raw = handle.read(MAX_SOURCE_BYTES + 1)
            if len(raw) > MAX_SOURCE_BYTES:
                raise ValueError('Loaded source exceeds 64 KiB.')
            return self.submit(raw.decode('utf-8'), expression=False)
        except (OSError, ValueError, TypeError, RuntimeError, UnicodeError) as error:
            return self._annotate(_failure('E_REPL_FILE', str(error)), 'rejected')

    def save(self, filename, *, name='REPL session'):
        """Create a portable source/input/module snapshot; never overwrite any file."""
        try:
            path = Path(filename)
            if not path.name.endswith('.sigil.json'):
                raise ValueError('Save to a new filename ending in .sigil.json.')
            program = {'format': FORMAT, 'format_version': 1, 'language_version': LANGUAGE_VERSION,
                       'name': name, 'source': self.source, 'data_text': json.dumps(self._data, ensure_ascii=True),
                       'contract_text': '', 'proposal_contract_text': '', 'modules': dict(self._modules)}
            write_text(path, encode_program(program), force=False)
            result = self._annotate(_empty(), 'saved')
            result['path'] = str(path)
            return result
        except (OSError, ValueError, TypeError, UnicodeError) as error:
            return self._annotate(_failure('E_REPL_FILE', str(error)), 'rejected')


def _display(result, stdout, stderr):
    if not result['ok']:
        for item in result.get('diagnostics', []):
            source = item.get('source_file') or item.get('source_name') or '<session>'
            print(f"{item['code']} at {source}:{item.get('line', 1)}:{item.get('column', 1)}: {item['message']}", file=stderr)
        return False
    for value in result.get('values', []):
        print('VALUE ' + json.dumps(value, ensure_ascii=True, sort_keys=True), file=stdout)
    for note in result.get('notes', []):
        print('NOTE ' + note['message'], file=stdout)
    for proposal in result.get('proposals', []):
        print('PROPOSAL ' + json.dumps(proposal, ensure_ascii=True, sort_keys=True), file=stdout)
    return True


def main(data=None, modules=None, stdin=None, stdout=None, stderr=None):
    """Run an interactive or piped session. All streams may be supplied by tests."""
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    try:
        session = Session(data, modules)
    except (ValueError, UnicodeError, RecursionError) as error:
        print('E_REPL_INPUT: ' + str(error), file=stderr)
        return 2
    interactive = bool(getattr(stdin, 'isatty', lambda: False)() and getattr(stdout, 'isatty', lambda: False)())
    if interactive:
        print(f'ZenSigil {__version__} REPL. :help for commands; blank line completes a block.', file=stdout)
    pending, pending_bytes, discarding, had_error = [], 0, False, False
    while True:
        try:
            if interactive:
                print('... ' if pending or discarding else 'zs> ', end='', file=stdout, flush=True)
            line = stdin.readline(MAX_SOURCE_BYTES + 1)
        except KeyboardInterrupt:
            pending, pending_bytes, discarding = [], 0, False
            print('Cell cancelled. Use :quit to exit.', file=stderr)
            continue
        except (OSError, UnicodeError) as error:
            print('E_REPL_INPUT: ' + str(error), file=stderr)
            return 2
        if line == '':
            if pending:
                had_error = not _display(session.submit(''.join(pending)), stdout, stderr) or had_error
            return int(had_error)
        if discarding:
            if not line.strip():
                discarding = False
            continue
        try:
            size = len(line.encode('utf-8'))
        except UnicodeError:
            size = MAX_SOURCE_BYTES + 1
        if size > MAX_SOURCE_BYTES or pending_bytes + size > MAX_SOURCE_BYTES:
            had_error = True
            print('E_LIMIT: The pending cell exceeds 64 KiB or contains invalid Unicode.', file=stderr)
            # Do not accidentally evaluate the tail of one oversized physical line.
            try:
                while line and not line.endswith('\n'):
                    line = stdin.readline(MAX_SOURCE_BYTES + 1)
            except KeyboardInterrupt:
                pending = []
                print('Cell cancelled. Use :quit to exit.', file=stderr)
            except (OSError, UnicodeError) as error:
                print('E_REPL_INPUT: ' + str(error), file=stderr)
                return 2
            discarding = bool(pending)
            pending, pending_bytes = [], 0
            continue
        if line.startswith(':'):
            try:
                args = shlex.split(line)
            except ValueError as error:
                print('E_REPL_COMMAND: ' + str(error), file=stderr)
                had_error = True
                continue
            command = args[0] if args else ''
            if command == ':quit' and len(args) == 1:
                return int(had_error)
            if pending:
                print('E_REPL_COMMAND: Finish the pending cell with a blank line, or cancel it with Ctrl+C.', file=stderr)
                had_error = True
                continue
            if command in (':help', ':show', ':reset', ':undo') and len(args) == 1:
                if command == ':help':
                    print(HELP, end='', file=stdout)
                elif command == ':show':
                    print(session.source or '(empty session)\n', end='', file=stdout)
                elif command == ':reset':
                    session.reset()
                    print('Session cleared; inputs, modules and remaining work budget are retained.', file=stdout)
                else:
                    result = session.undo()
                    had_error = not _display(result, stdout, stderr) or had_error
                    if result['ok']:
                        print('Undid the last successful cell.', file=stdout)
            elif command in (':load', ':save') and len(args) == 2:
                result = session.load(args[1]) if command == ':load' else session.save(args[1])
                had_error = not _display(result, stdout, stderr) or had_error
                if command == ':save' and result['ok']:
                    print('Saved ' + result['path'], file=stdout)
            else:
                print('E_REPL_COMMAND: Unknown command or wrong arguments. Use :help.', file=stderr)
                had_error = True
            continue
        if not line.strip():
            if pending:
                had_error = not _display(session.submit(''.join(pending)), stdout, stderr) or had_error
                pending, pending_bytes = [], 0
            continue
        if pending:
            pending.append(line)
            pending_bytes += size
            continue
        try:
            continues = _continues(line)
        except (UnicodeError, RecursionError):
            continues = False
        if continues:
            pending, pending_bytes = [line], size
        else:
            had_error = not _display(session.submit(line), stdout, stderr) or had_error


if __name__ == '__main__':
    raise SystemExit(main())
