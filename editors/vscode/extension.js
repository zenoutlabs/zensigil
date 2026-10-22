'use strict';
const vscode = require('vscode');
const {spawn} = require('node:child_process');
const {Client} = require('./client');

function activate(context) {
  // This check supplements the manifest's disabled-in-untrusted-workspaces policy.
  if (!vscode.workspace.isTrusted) return;
  const diagnostics = vscode.languages.createDiagnosticCollection('zensigil');
  const output = vscode.window.createOutputChannel('ZenSigil');
  const selector = {language: 'zensigil', scheme: 'file'};
  let client;
  let ready = false;
  let generation = 0;
  let disposed = false;
  let watchTimer;
  const changedFiles = new Map();
  const opened = new Map();
  const asRange = range => new vscode.Range(range.start.line, range.start.character, range.end.line, range.end.character);
  const matches = document => document.languageId === 'zensigil' && document.uri.scheme === 'file';
  const log = message => output.appendLine(message);
  const notify = (method, params) => {
    if (method !== 'textDocument/publishDiagnostics' || !params || !Array.isArray(params.diagnostics)) return;
    const document = vscode.workspace.textDocuments.find(doc => doc.uri.toString() === params.uri);
    if (document && params.version !== undefined && document.version !== params.version) return;
    const items = params.diagnostics.map(item => {
      const severity = item.severity === 2 ? vscode.DiagnosticSeverity.Warning : vscode.DiagnosticSeverity.Error;
      const diagnostic = new vscode.Diagnostic(asRange(item.range), item.message, severity);
      diagnostic.code = item.code;
      diagnostic.source = 'ZenSigil';
      return diagnostic;
    });
    diagnostics.set(vscode.Uri.parse(params.uri), items);
  };
  function sync(document) {
    if (!ready || !matches(document)) return false;
    const uri = document.uri.toString();
    const text = document.getText();
    try {
      if (!opened.has(uri)) {
        client.notification('textDocument/didOpen', {textDocument: {uri, languageId: 'zensigil', version: document.version, text}});
      } else if (opened.get(uri) !== document.version) {
        client.notification('textDocument/didChange', {textDocument: {uri, version: document.version}, contentChanges: [{text}]});
      }
      opened.set(uri, document.version);
      return true;
    } catch (error) { log(error.message); return false; }
  }
  async function query(document, method, extra = {}) {
    if (!ready || !vscode.workspace.isTrusted) return null;
    if (!sync(document)) return null;
    const version = document.version;
    const current = generation;
    try {
      const result = await client.request(method, {textDocument: {uri: document.uri.toString()}, ...extra});
      return current === generation && ready && document.version === version && !document.isClosed ? result : null;
    } catch (error) { log(error.message); return null; }
  }
  const position = at => ({line: at.line, character: at.character});
  const folders = values => values.filter(folder => folder.uri.scheme === 'file').map(folder => ({uri: folder.uri.toString(), name: folder.name}));
  function flushFiles() {
    clearTimeout(watchTimer);
    watchTimer = undefined;
    const changes = [...changedFiles.values()];
    changedFiles.clear();
    if (!ready || !changes.length) return;
    try { client.notification('workspace/didChangeWatchedFiles', {changes}); }
    catch (error) { log(error.message); }
  }
  function changed(uri, type) {
    if (!ready || uri.scheme !== 'file') return;
    changedFiles.set(uri.toString(), {uri: uri.toString(), type});
    if (changedFiles.size >= 256) flushFiles();
    else if (!watchTimer) watchTimer = setTimeout(flushFiles, 100);
  }
  async function start() {
    const current = ++generation;
    ready = false;
    opened.clear();
    diagnostics.clear();
    clearTimeout(watchTimer);
    watchTimer = undefined;
    changedFiles.clear();
    client?.dispose();
    client = undefined;
    if (disposed || !vscode.workspace.isTrusted) return;
    let candidate;
    try {
      const executable = vscode.workspace.getConfiguration('zensigil').get('pythonPath', 'python3');
      // Isolated Python prevents workspace modules from replacing the installed server.
      const child = spawn(executable, ['-I', '-m', 'zensigil', 'lsp'], {cwd: context.extensionPath, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true, shell: false});
      candidate = new Client(child, (method, params) => {
        if (current === generation && !disposed) notify(method, params);
      }, log, () => {
        if (current !== generation || disposed) return;
        ready = false;
        opened.clear();
        diagnostics.clear();
        log('Use ZenSigil: Restart Language Server to reconnect.');
      });
      client = candidate;
      await candidate.request('initialize', {processId: process.pid, clientInfo: {name: 'zensigil-vscode'}, capabilities: {general: {positionEncodings: ['utf-16']}},
        workspaceFolders: folders(vscode.workspace.workspaceFolders || [])});
      if (current !== generation || disposed || candidate.closed) return;
      candidate.notification('initialized', {});
      ready = true;
      for (const document of vscode.workspace.textDocuments) sync(document);
    } catch (error) {
      candidate?.dispose();
      if (current !== generation || disposed) return;
      ready = false;
      log(error.message);
      vscode.window.showErrorMessage('ZenSigil editor support could not start. Install ZenSigil in the selected Python environment, then use ZenSigil: Restart Language Server. See the ZenSigil output channel.');
    }
  }
  const watcher = vscode.workspace.createFileSystemWatcher('**/*.zs');
  context.subscriptions.push(diagnostics, output, watcher,
    watcher.onDidCreate(uri => changed(uri, 1)),
    watcher.onDidChange(uri => changed(uri, 2)),
    watcher.onDidDelete(uri => changed(uri, 3)),
    vscode.workspace.onDidChangeWorkspaceFolders(event => {
      if (!ready) { start(); return; }
      try { client.notification('workspace/didChangeWorkspaceFolders', {event: {added: folders(event.added), removed: folders(event.removed)}}); }
      catch (error) { log(error.message); }
    }),
    vscode.workspace.onDidChangeConfiguration(event => {
      if (event.affectsConfiguration('zensigil.pythonPath')) start();
    }),
    vscode.commands.registerCommand('zensigil.restartServer', start),
    vscode.workspace.onDidOpenTextDocument(sync),
    vscode.workspace.onDidChangeTextDocument(event => {
      diagnostics.delete(event.document.uri);
      sync(event.document);
    }),
    vscode.workspace.onDidCloseTextDocument(document => {
      const uri = document.uri.toString();
      if (ready && opened.has(uri)) {
        try { client.notification('textDocument/didClose', {textDocument: {uri}}); } catch (error) { log(error.message); }
      }
      opened.delete(uri);
      diagnostics.delete(document.uri);
    }),
    vscode.commands.registerCommand('zensigil.check', async () => {
      const document = vscode.window.activeTextEditor?.document;
      if (!document || !matches(document) || !ready || !vscode.workspace.isTrusted) return;
      const uri = document.uri.toString();
      // Reopen explicitly to refresh reachable modules after an external disk edit.
      try {
        if (opened.has(uri)) client.notification('textDocument/didClose', {textDocument: {uri}});
        opened.delete(uri);
        sync(document);
      } catch (error) { log(error.message); }
    }),
    vscode.languages.registerCompletionItemProvider(selector, {async provideCompletionItems(document, at) {
      const result = await query(document, 'textDocument/completion', {position: position(at)});
      return (result || []).map(item => { const completion = new vscode.CompletionItem(item.label, item.kind - 1); completion.detail = item.detail; return completion; });
    }}, '.'),
    vscode.languages.registerHoverProvider(selector, {async provideHover(document, at) {
      const result = await query(document, 'textDocument/hover', {position: position(at)});
      if (!result) return null;
      const content = new vscode.MarkdownString();
      content.appendCodeblock(result.contents.value, 'zensigil');
      return new vscode.Hover(content, asRange(result.range));
    }}),
    vscode.languages.registerDefinitionProvider(selector, {async provideDefinition(document, at) {
      const result = await query(document, 'textDocument/definition', {position: position(at)});
      return result ? new vscode.Location(vscode.Uri.parse(result.uri), asRange(result.range)) : null;
    }}),
    vscode.languages.registerReferenceProvider(selector, {async provideReferences(document, at, context) {
      const result = await query(document, 'textDocument/references', {position: position(at), context: {includeDeclaration: context.includeDeclaration}});
      return (result || []).map(item => new vscode.Location(vscode.Uri.parse(item.uri), asRange(item.range)));
    }}),
    vscode.languages.registerDocumentSymbolProvider(selector, {async provideDocumentSymbols(document) {
      const result = await query(document, 'textDocument/documentSymbol');
      return (result || []).map(item => new vscode.SymbolInformation(item.name, item.kind - 1, item.containerName,
        new vscode.Location(vscode.Uri.parse(item.location.uri), asRange(item.location.range))));
    }}),
    vscode.languages.registerDocumentFormattingEditProvider(selector, {async provideDocumentFormattingEdits(document, options) {
      const result = await query(document, 'textDocument/formatting', {options});
      return (result || []).map(item => vscode.TextEdit.replace(asRange(item.range), item.newText));
    }}),
    {dispose() {
      disposed = true;
      generation++;
      ready = false;
      clearTimeout(watchTimer);
      changedFiles.clear();
      client?.dispose();
    }});

  start();
}
exports.activate = activate;
