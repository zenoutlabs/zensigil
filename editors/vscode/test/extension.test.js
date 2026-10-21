'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function load(vscode, spawn, Client) {
  const sandbox = {exports: {}, process, require(name) {
    if (name === 'vscode') return vscode;
    if (name === 'node:child_process') return {spawn};
    if (name === './client') return {Client};
    throw new Error(`Unexpected import ${name}`);
  }};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../extension.js'), 'utf8'), sandbox);
  return sandbox.exports;
}
const disposable = () => ({dispose() {}});

test('untrusted workspace never registers a process or executes an interpreter', () => {
  let spawned = 0;
  const extension = load({workspace: {isTrusted: false}}, () => { spawned++; });
  extension.activate({subscriptions: [], extensionPath: '/extension'});
  assert.equal(spawned, 0);
});

test('trusted fake host initializes isolated Python and routes every editor provider', async () => {
  const providers = {}, triggers = {}, events = {}, requests = [], notifications = [], spawns = [], diagnostics = [];
  let notify;
  class FakeClient {
    constructor(child, notification) { notify = notification; this.closed = false; }
    notification(method, params) { notifications.push({method, params}); }
    request(method, params) {
      requests.push({method, params});
      const range = {start: {line: 0, character: 0}, end: {line: 0, character: 1}};
      const values = {'initialize': {}, 'textDocument/completion': [{label: 'map', kind: 3, detail: 'map(arg1, arg2)'}],
        'textDocument/hover': {contents: {value: 'fn double(x)'}, range}, 'textDocument/definition': {uri: 'file:///workspace/lib.zs', range},
        'textDocument/documentSymbol': [{name: 'double', kind: 12, containerName: '', location: {uri: 'file:///workspace/main.zs', range}}],
        'textDocument/formatting': [{range, newText: 'emit 1\n'}]};
      return Promise.resolve(values[method]);
    }
    dispose() {}
  }
  const uri = {scheme: 'file', toString: () => 'file:///workspace/main.zs'};
  const document = {uri, languageId: 'zensigil', version: 1, isClosed: false, getText: () => 'emit 1\n'};
  const vscode = {
    workspace: {isTrusted: true, textDocuments: [document], workspaceFolders: [{uri: {scheme: 'file', toString: () => 'file:///workspace'}, name: 'workspace'}],
      getConfiguration: () => ({get: () => '/user/python'}),
      onDidOpenTextDocument: fn => { events.open = fn; return disposable(); },
      onDidChangeTextDocument: fn => { events.change = fn; return disposable(); },
      onDidCloseTextDocument: fn => { events.close = fn; return disposable(); }},
    window: {createOutputChannel: () => ({appendLine() {}, dispose() {}}), showErrorMessage() {}, activeTextEditor: {document}},
    languages: {createDiagnosticCollection: () => ({set: (...args) => diagnostics.push(args), delete() {}, dispose() {}})},
    commands: {registerCommand: (name, fn) => { events.check = fn; return disposable(); }},
    Range: class {constructor(...args) { this.args = args; }}, Diagnostic: class {constructor(range, message, severity) { this.range = range; this.message = message; this.severity = severity; }},
    DiagnosticSeverity: {Error: 0, Warning: 1}, Uri: {parse: value => value},
    CompletionItem: class {constructor(label, kind) { this.label = label; this.kind = kind; }},
    MarkdownString: class {appendCodeblock(value) { this.value = value; }}, Hover: class {constructor(contents) { this.contents = contents; }},
    Location: class {constructor(uri, range) { this.uri = uri; this.range = range; }}, SymbolInformation: class {constructor(name) { this.name = name; }},
    TextEdit: {replace: (range, newText) => ({range, newText})}
  };
  for (const kind of ['CompletionItem', 'Hover', 'Definition', 'DocumentSymbol', 'DocumentFormattingEdit']) {
    vscode.languages[`register${kind}Provider`] = (selector, provider, ...characters) => { providers[kind] = provider; triggers[kind] = characters; return disposable(); };
  }
  load(vscode, (...args) => { spawns.push(args); return {}; }, FakeClient).activate({subscriptions: [], extensionPath: '/extension'});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(spawns.length, 1);
  assert.deepEqual(triggers.CompletionItem, ['.']);
  assert.equal(spawns[0][0], '/user/python');
  assert.deepEqual(Array.from(spawns[0][1]), ['-I', '-m', 'zensigil', 'lsp']);
  assert.equal(spawns[0][2].shell, false);
  assert.equal(spawns[0][2].cwd, '/extension');
  assert.equal(notifications[0].method, 'initialized');
  assert.equal(notifications[1].method, 'textDocument/didOpen');
  const at = {line: 0, character: 3};
  assert.equal((await providers.CompletionItem.provideCompletionItems(document, at))[0].label, 'map');
  assert.equal((await providers.Hover.provideHover(document, at)).contents.value, 'fn double(x)');
  assert.equal((await providers.Definition.provideDefinition(document, at)).uri, 'file:///workspace/lib.zs');
  assert.equal((await providers.DocumentSymbol.provideDocumentSymbols(document))[0].name, 'double');
  assert.equal((await providers.DocumentFormattingEdit.provideDocumentFormattingEdits(document, {}))[0].newText, 'emit 1\n');
  document.version = 2;
  events.change({document});
  assert.equal(notifications.at(-1).method, 'textDocument/didChange');
  assert.equal(notifications.at(-1).params.textDocument.version, 2);
  notify('textDocument/publishDiagnostics', {uri: uri.toString(), version: 1, diagnostics: []});
  assert.equal(diagnostics.length, 0);
  notify('textDocument/publishDiagnostics', {uri: uri.toString(), version: 2, diagnostics: []});
  assert.equal(diagnostics.length, 1);
  const range = {start: {line: 0, character: 0}, end: {line: 0, character: 1}};
  notify('textDocument/publishDiagnostics', {uri: uri.toString(), version: 2, diagnostics: [
    {range, severity: 2, code: 'W_UNUSED', message: 'A binding is unused.'},
    {range, severity: 1, code: 'E_NAME', message: 'A name is unknown.'}
  ]});
  assert.equal(diagnostics.at(-1)[1][0].severity, vscode.DiagnosticSeverity.Warning);
  assert.equal(diagnostics.at(-1)[1][1].severity, vscode.DiagnosticSeverity.Error);
  events.close(document);
  assert.equal(notifications.at(-1).method, 'textDocument/didClose');
});
