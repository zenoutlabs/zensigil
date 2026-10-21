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
  const opened = new Map();
  const asRange = range => new vscode.Range(range.start.line, range.start.character, range.end.line, range.end.character);
  const matches = document => document.languageId === 'zensigil' && document.uri.scheme === 'file';
  const log = message => output.appendLine(message);
  const notify = (method, params) => {
    if (method !== 'textDocument/publishDiagnostics' || !params || !Array.isArray(params.diagnostics)) return;
    const document = vscode.workspace.textDocuments.find(doc => doc.uri.toString() === params.uri);
    if (document && params.version !== undefined && document.version !== params.version) return;
    const items = params.diagnostics.map(item => {
      const diagnostic = new vscode.Diagnostic(asRange(item.range), item.message, vscode.DiagnosticSeverity.Error);
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
    try {
      const result = await client.request(method, {textDocument: {uri: document.uri.toString()}, ...extra});
      return document.version === version && !document.isClosed ? result : null;
    } catch (error) { log(error.message); return null; }
  }
  const position = at => ({line: at.line, character: at.character});
  context.subscriptions.push(diagnostics, output,
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
    vscode.languages.registerDocumentSymbolProvider(selector, {async provideDocumentSymbols(document) {
      const result = await query(document, 'textDocument/documentSymbol');
      return (result || []).map(item => new vscode.SymbolInformation(item.name, item.kind - 1, item.containerName,
        new vscode.Location(vscode.Uri.parse(item.location.uri), asRange(item.location.range))));
    }}),
    vscode.languages.registerDocumentFormattingEditProvider(selector, {async provideDocumentFormattingEdits(document, options) {
      const result = await query(document, 'textDocument/formatting', {options});
      return (result || []).map(item => vscode.TextEdit.replace(asRange(item.range), item.newText));
    }}),
    {dispose() { ready = false; client?.dispose(); }});

  const executable = vscode.workspace.getConfiguration('zensigil').get('pythonPath', 'python3');
  // -I prevents a workspace Python module from shadowing the installed interpreter.
  // Python is one executable string; source never becomes shell arguments.
  const child = spawn(executable, ['-I', '-m', 'zensigil', 'lsp'], {cwd: context.extensionPath, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true, shell: false});
  client = new Client(child, notify, log);
  client.request('initialize', {processId: process.pid, clientInfo: {name: 'zensigil-vscode'}, capabilities: {general: {positionEncodings: ['utf-16']}},
    workspaceFolders: (vscode.workspace.workspaceFolders || []).filter(folder => folder.uri.scheme === 'file').map(folder => ({uri: folder.uri.toString(), name: folder.name}))})
    .then(() => {
      if (client.closed) return;
      client.notification('initialized', {});
      ready = true;
      for (const document of vscode.workspace.textDocuments) sync(document);
    }).catch(error => {
      log(error.message);
      vscode.window.showErrorMessage('ZenSigil editor support could not start. Install the matching ZenSigil version in the selected Python environment, then reload the window. See the ZenSigil output channel.');
    });
}
exports.activate = activate;
