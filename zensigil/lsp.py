"""Bounded standard-library-only LSP server over stdin/stdout. No program execution."""
import json
import re
import sys

from . import __version__
from .errors import SigilError
from .language_tools import LanguageService

MAX_MESSAGE_BYTES = 1024 * 1024
MAX_HEADER_BYTES = 8192


class FramingError(ValueError):
    pass


def read_message(stream):
    """Read one bounded LSP frame; EOF is None, malformed framing is fatal."""
    headers, size = {}, 0
    while True:
        line = stream.readline(MAX_HEADER_BYTES + 1)
        if not line:
            if not size:
                return None
            raise FramingError('Unexpected EOF in message headers.')
        size += len(line)
        if size > MAX_HEADER_BYTES or not line.endswith(b'\r\n'):
            raise FramingError('Headers must be bounded ASCII lines ending in CRLF.')
        if line == b'\r\n':
            break
        try:
            key, value = line[:-2].decode('ascii').split(':', 1)
        except (ValueError, UnicodeError):
            raise FramingError('Malformed message header.')
        key, value = key.strip().lower(), value.strip()
        if not key or key in headers:
            raise FramingError('Repeated or empty message header.')
        headers[key] = value
    content_type = headers.get('content-type', '')
    if 'charset=' in content_type.lower() and content_type.lower().split('charset=', 1)[1].strip() not in ('utf-8', 'utf8'):
        raise FramingError('Only UTF-8 JSON messages are supported.')
    length = headers.get('content-length', '')
    if not re.fullmatch('[0-9]{1,8}', length) or not 0 < int(length) <= MAX_MESSAGE_BYTES:
        raise FramingError('Content-Length must be between 1 and 1048576 bytes.')
    body = stream.read(int(length))
    if len(body) != int(length):
        raise FramingError('Unexpected EOF in message body.')
    return body


def write_message(stream, message):
    body = json.dumps(message, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    stream.write(b'Content-Length: ' + str(len(body)).encode('ascii') + b'\r\n\r\n' + body)
    stream.flush()


class Server:
    def __init__(self, send, log=None):
        self.send = send
        self.log = log or (lambda message: None)
        self.service = LanguageService()
        self.initialized = False
        self.shutting_down = False
        self.exited = False
        self.published = set()

    def error(self, identity, code, message):
        self.send({'jsonrpc': '2.0', 'id': identity, 'error': {'code': code, 'message': message}})

    def publish(self, closed=None):
        combined = {}
        for uri in self.service.documents:
            for target, diagnostics in self.service.diagnostics(uri).items():
                bucket = combined.setdefault(target, [])
                for item in diagnostics:
                    if item not in bucket:
                        bucket.append(item)
        for uri in sorted(self.published | set(combined) | ({closed} if closed else set())):
            params = {'uri': uri, 'diagnostics': combined.get(uri, [])}
            if uri in self.service.documents:
                params['version'] = self.service.documents[uri].version
            self.send({'jsonrpc': '2.0', 'method': 'textDocument/publishDiagnostics', 'params': params})
        self.published = set(combined)

    def handle(self, message):
        identity = message.get('id') if isinstance(message, dict) else None
        request = isinstance(message, dict) and 'id' in message
        if (not isinstance(message, dict) or message.get('jsonrpc') != '2.0'
                or not isinstance(message.get('method'), str)
                or (request and (type(identity) not in (int, str) or isinstance(identity, str) and len(identity) > 1024))):
            self.error(None, -32600, 'Invalid JSON-RPC request.')
            return
        method = message['method']
        params = message.get('params', {})
        if not isinstance(params, dict):
            if request:
                self.error(identity, -32602, 'Parameters must be an object.')
            return
        if method == 'exit':
            self.exited = True
            return
        if method == 'initialize':
            if not request or self.initialized:
                if request:
                    self.error(identity, -32600, 'The server is already initialized.')
                return
            folders = params.get('workspaceFolders')
            roots = [folder.get('uri') for folder in folders[:32] if isinstance(folder, dict)] if isinstance(folders, list) else [params.get('rootUri')]
            self.service = LanguageService(roots)
            self.initialized = True
            self.send({'jsonrpc': '2.0', 'id': identity, 'result': {'serverInfo': {'name': 'ZenSigil', 'version': __version__}, 'capabilities': {
                'positionEncoding': 'utf-16',
                'textDocumentSync': {'openClose': True, 'change': 1},
                'completionProvider': {'resolveProvider': False, 'triggerCharacters': ['.']},
                'hoverProvider': True, 'definitionProvider': True,
                'documentSymbolProvider': True, 'documentFormattingProvider': True}}})
            return
        if not self.initialized:
            if request:
                self.error(identity, -32002, 'Server not initialized.')
            return
        if self.shutting_down:
            if request:
                self.error(identity, -32600, 'Server has shut down.')
            return
        if method == 'shutdown':
            if request:
                self.shutting_down = True
                self.send({'jsonrpc': '2.0', 'id': identity, 'result': None})
            return
        if method in ('initialized', '$/cancelRequest', '$/setTrace'):
            return
        supported = {'textDocument/didOpen', 'textDocument/didChange', 'textDocument/didClose',
                     'textDocument/completion', 'textDocument/hover', 'textDocument/definition',
                     'textDocument/documentSymbol', 'textDocument/formatting'}
        if method not in supported:
            if request:
                self.error(identity, -32601, 'Method not found.')
            return
        document = params.get('textDocument', {})
        if not isinstance(document, dict) or not isinstance(document.get('uri'), str):
            if request:
                self.error(identity, -32602, 'A textDocument URI is required.')
            return
        uri = document['uri']
        try:
            if method == 'textDocument/didOpen':
                if self.service.open(uri, document.get('text'), document.get('version')):
                    self.publish()
                return
            if method == 'textDocument/didChange':
                changes = params.get('contentChanges')
                if isinstance(changes, list) and len(changes) == 1 and isinstance(changes[0], dict) and 'range' not in changes[0]:
                    if self.service.change(uri, changes[0].get('text'), document.get('version')):
                        self.publish()
                else:
                    self.log('ZenSigil accepts one full-text change per notification.')
                return
            if method == 'textDocument/didClose':
                if self.service.close(uri):
                    self.publish(closed=uri)
                return
            queries = {
                'textDocument/completion': lambda: self.service.completion(uri, params.get('position')),
                'textDocument/hover': lambda: self.service.hover(uri, params.get('position')),
                'textDocument/definition': lambda: self.service.definition(uri, params.get('position')),
                'textDocument/documentSymbol': lambda: self.service.symbols(uri),
                'textDocument/formatting': lambda: self.service.formatting(uri),
            }
            if request and method in queries:
                self.send({'jsonrpc': '2.0', 'id': identity, 'result': queries[method]()})
            elif request:
                self.error(identity, -32601, 'Method not found.')
        except SigilError as error:
            if request:
                self.error(identity, -32602, error.code + ': ' + error.message)
            else:
                self.log(error.code + ': ' + error.message)
        except (ValueError, TypeError, KeyError, OSError, RecursionError, UnicodeError):
            # Invalid client fields and pathological source never contaminate stdout.
            if request:
                self.error(identity, -32602, 'Invalid or unsupported editor parameters.')
            else:
                self.log('Ignored invalid editor notification.')


def main(stdin=None, stdout=None, stderr=None):
    stdin = stdin or sys.stdin.buffer
    stdout = stdout or sys.stdout.buffer
    stderr = stderr or sys.stderr
    server = Server(lambda item: write_message(stdout, item), lambda message: print(message, file=stderr))
    try:
        while not server.exited:
            body = read_message(stdin)
            if body is None:
                return 0 if server.shutting_down else 1
            try:
                message = json.loads(body.decode('utf-8'), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            except (ValueError, UnicodeError, RecursionError):
                server.error(None, -32700, 'Invalid UTF-8 JSON message.')
                continue
            server.handle(message)
    except FramingError as error:
        print('ZenSigil LSP: ' + str(error), file=stderr)
        return 1
    except (BrokenPipeError, KeyboardInterrupt):
        return 1
    return 0 if server.shutting_down else 1


if __name__ == '__main__':
    raise SystemExit(main())
