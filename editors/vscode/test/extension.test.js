'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function load(vscode, spawn, Client) {
  const sandbox = {exports: {}, process, setTimeout, clearTimeout, require(name) {
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

function host(options = {}) {
  const providers = {}, triggers = {}, events = {}, requests = [], notifications = [], spawns = [], diagnostics = [], clients = [], errors = [];
  let clears = 0;
  let notify;
  class FakeClient {
    constructor(child, notification, log, stopped) { notify = notification; this.notify = notification; this.stopped = stopped; this.closed = false; clients.push(this); }
    notification(method, params) { notifications.push({method, params}); }
    request(method, params) {
      requests.push({method, params});
      if (options.request) { const result = options.request(method, this); if (result !== undefined) return result; }
      const range = {start: {line: 0, character: 0}, end: {line: 0, character: 1}};
      const values = {'initialize': {}, 'textDocument/completion': [{label: 'map', kind: 3, detail: 'map(arg1, arg2)'}],
        'textDocument/hover': {contents: {value: 'fn double(x)'}, range}, 'textDocument/definition': {uri: 'file:///workspace/lib.zs', range},
        'textDocument/references': [{uri: 'file:///workspace/main.zs', range}],
        'textDocument/documentSymbol': [{name: 'double', kind: 12, containerName: '', location: {uri: 'file:///workspace/main.zs', range}}],
        'textDocument/formatting': [{range, newText: 'emit 1\n'}]};
      return Promise.resolve(values[method]);
    }
    dispose() { this.disposed = true; }
  }
  const uri = {scheme: 'file', toString: () => 'file:///workspace/main.zs'};
  const document = {uri, languageId: 'zensigil', version: 1, isClosed: false, getText: () => 'emit 1\n'};
  const vscode = {
    workspace: {isTrusted: true, textDocuments: [document], workspaceFolders: [{uri: {scheme: 'file', toString: () => 'file:///workspace'}, name: 'workspace'}],
      getConfiguration: () => ({get: () => options.python || '/user/python'}),
      createFileSystemWatcher: () => ({dispose() {},
        onDidCreate: fn => { events.createFile = fn; return disposable(); },
        onDidChange: fn => { events.changeFile = fn; return disposable(); },
        onDidDelete: fn => { events.deleteFile = fn; return disposable(); }}),
      onDidChangeWorkspaceFolders: fn => { events.folders = fn; return disposable(); },
      onDidChangeConfiguration: fn => { events.configuration = fn; return disposable(); },
      onDidOpenTextDocument: fn => { events.open = fn; return disposable(); },
      onDidChangeTextDocument: fn => { events.change = fn; return disposable(); },
      onDidCloseTextDocument: fn => { events.close = fn; return disposable(); }},
    window: {createOutputChannel: () => ({appendLine() {}, dispose() {}}), showErrorMessage: value => errors.push(value), activeTextEditor: {document}},
    languages: {createDiagnosticCollection: () => ({set: (...args) => diagnostics.push(args), delete() {}, clear() { clears++; }, dispose() {}})},
    commands: {registerCommand: (name, fn) => { events[name] = fn; return disposable(); }},
    Range: class {constructor(...args) { this.args = args; }}, Diagnostic: class {constructor(range, message, severity) { this.range = range; this.message = message; this.severity = severity; }},
    DiagnosticSeverity: {Error: 0, Warning: 1}, Uri: {parse: value => value},
    CompletionItem: class {constructor(label, kind) { this.label = label; this.kind = kind; }},
    MarkdownString: class {appendCodeblock(value) { this.value = value; }}, Hover: class {constructor(contents) { this.contents = contents; }},
    Location: class {constructor(uri, range) { this.uri = uri; this.range = range; }}, SymbolInformation: class {constructor(name) { this.name = name; }},
    TextEdit: {replace: (range, newText) => ({range, newText})}
  };
  for (const kind of ['CompletionItem', 'Hover', 'Definition', 'Reference', 'DocumentSymbol', 'DocumentFormattingEdit']) {
    vscode.languages[`register${kind}Provider`] = (selector, provider, ...characters) => { providers[kind] = provider; triggers[kind] = characters; return disposable(); };
  }
  const context = {subscriptions: [], extensionPath: '/extension'};
  load(vscode, (...args) => { spawns.push(args); return {}; }, FakeClient).activate(context);
  return {providers, triggers, events, requests, notifications, spawns, diagnostics, clients, errors, document, vscode, uri,
    notify: (...args) => notify(...args), get clears() { return clears; },
    dispose() { for (const item of context.subscriptions) item.dispose(); }};
}

test('trusted fake host initializes isolated Python and routes every editor provider', async () => {
  const h = host();
  const {providers, triggers, events, requests, notifications, spawns, diagnostics, document, vscode, uri, notify} = h;
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
  assert.equal((await providers.Reference.provideReferences(document, at, {includeDeclaration: true}))[0].uri, 'file:///workspace/main.zs');
  assert.equal(requests.at(-1).params.context.includeDeclaration, true);
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
  h.dispose();
});

const tick = () => new Promise(resolve => setImmediate(resolve));
test('restart discards old diagnostics and queries, then reopens documents', async () => {
  let resolveQuery;
  const h = host({request: method => method === 'textDocument/hover' ? new Promise(resolve => { resolveQuery = resolve; }) : undefined});
  await tick();
  const old = h.clients[0];
  const pending = h.providers.Hover.provideHover(h.document, {line: 0, character: 0});
  await h.events['zensigil.restartServer']();
  assert.equal(old.disposed, true);
  assert.equal(h.clients.length, 2);
  assert.equal(h.notifications.at(-1).method, 'textDocument/didOpen');
  old.notify('textDocument/publishDiagnostics', {uri: h.uri.toString(), version: 1, diagnostics: []});
  assert.equal(h.diagnostics.length, 0);
  resolveQuery({contents: {value: 'old answer'}, range: {start: {line: 0, character: 0}, end: {line: 0, character: 1}}});
  assert.equal(await pending, null);
  old.stopped(new Error('Old process ended'));
  assert.equal((await h.providers.CompletionItem.provideCompletionItems(h.document, {line: 0, character: 0}))[0].label, 'map');
  h.dispose();
});

test('server exit clears diagnostics and manual restart restores queries', async () => {
  const h = host(); await tick();
  const before = h.clears;
  h.clients[0].closed = true;
  h.clients[0].stopped(new Error('Exited'));
  assert.equal(h.clears, before + 1);
  assert.equal((await h.providers.CompletionItem.provideCompletionItems(h.document, {line: 0, character: 0})).length, 0);
  await h.events['zensigil.restartServer']();
  assert.equal(h.clients.length, 2);
  assert.equal((await h.providers.CompletionItem.provideCompletionItems(h.document, {line: 0, character: 0}))[0].label, 'map');
  h.dispose();
});

test('configuration changes restart only for the interpreter and folders update in place', async () => {
  const options = {};
  const h = host(options); await tick();
  h.events.configuration({affectsConfiguration: () => false});
  assert.equal(h.clients.length, 1);
  options.python = '/another/python';
  h.events.configuration({affectsConfiguration: key => key === 'zensigil.pythonPath'});
  await tick();
  assert.equal(h.spawns.at(-1)[0], '/another/python');
  h.events.folders({added: [{uri: {scheme: 'file', toString: () => 'file:///added'}, name: 'added'}], removed: []});
  assert.equal(h.notifications.at(-1).method, 'workspace/didChangeWorkspaceFolders');
  assert.equal(h.notifications.at(-1).params.event.added[0].uri, 'file:///added');
  assert.equal(h.clients.length, 2);
  h.dispose();
});

test('file changes are batched and extension disposal cancels pending work', async () => {
  const h = host(); await tick();
  const uri = {scheme: 'file', toString: () => 'file:///workspace/lib.zs'};
  h.events.createFile(uri); h.events.changeFile(uri); h.events.deleteFile(uri);
  await new Promise(resolve => setTimeout(resolve, 120));
  const latest = h.notifications.at(-1);
  assert.equal(latest.method, 'workspace/didChangeWatchedFiles');
  assert.equal(latest.params.changes.length, 1);
  assert.equal(latest.params.changes[0].type, 3);
  h.events.changeFile(uri);
  const count = h.notifications.length;
  h.dispose();
  await new Promise(resolve => setTimeout(resolve, 120));
  assert.equal(h.notifications.length, count);
  assert.equal(h.clients[0].disposed, true);
});

test('failed initialization disposes the child and explains restart', async () => {
  const h = host({request: method => method === 'initialize' ? Promise.reject(new Error('Missing interpreter')) : undefined});
  await tick();
  assert.equal(h.clients[0].disposed, true);
  assert.equal(h.errors.length, 1);
  assert.match(h.errors[0], /Restart Language Server/);
  h.dispose();
});

test('a restart during initialization cannot revive the old server', async () => {
  let resolveOld;
  let initializes = 0;
  const h = host({request: method => method === 'initialize' && ++initializes === 1 ? new Promise(resolve => { resolveOld = resolve; }) : undefined});
  await h.events['zensigil.restartServer']();
  const old = h.clients[0];
  resolveOld({}); await tick();
  assert.equal(old.disposed, true);
  assert.equal(h.notifications.length, 2);
  h.dispose();
});
