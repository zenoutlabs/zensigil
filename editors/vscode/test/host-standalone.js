'use strict';
// Run in an isolated, empty Extension Development Host. No trust setting is changed.
const vscode = require('vscode');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(check, label) {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    const result = await check();
    if (result) return result;
    await delay(150);
  }
  throw new Error('Timed out: ' + label);
}

exports.run = async function run() {
  const root = process.env.ZENSIGIL_TEST_WORKSPACE;
  const python = process.env.ZENSIGIL_TEST_PYTHON;
  const evidence = process.env.ZENSIGIL_TEST_EVIDENCE;
  const report = {ok: false, host: 'VS Code Extension Development Host',
    vscode: vscode.version, scope: 'standalone source in an empty trusted window', checks: []};
  try {
    assert(root && python && evidence, 'Set the three ZENSIGIL_TEST environment paths.');
    assert(!vscode.workspace.workspaceFolders?.length, 'Start an empty isolated test window.');
    assert(vscode.workspace.isTrusted, 'The empty window must already be trusted. Do not disable trust.');
    await vscode.workspace.getConfiguration('zensigil').update('pythonPath', python, vscode.ConfigurationTarget.Global);
    const uri = vscode.Uri.file(path.join(root, 'standalone.zs'));
    const source = 'fn double(value: number) -> number:\n    return value * 2\nlet amount=3\nemit ["🌱",double(amount)]\n';
    assert.equal(await fs.readFile(uri.fsPath, 'utf8'), source, 'Use only the exact synthetic fixture.');
    const extension = vscode.extensions.getExtension('zenoutlabs.zensigil');
    assert(extension, 'The development extension must be installed.');
    await extension.activate();
    const document = await vscode.workspace.openTextDocument(uri);
    await vscode.window.showTextDocument(document);
    const completions = await until(async () => {
      const result = await vscode.commands.executeCommand('vscode.executeCompletionItemProvider', uri, new vscode.Position(3, 12));
      return result?.items.some(item => item.label === 'double') && result;
    }, 'completion readiness');
    assert(completions.items.some(item => item.label === 'map'));
    report.checks.push('Real completion provider lists user functions and built-in functions.');
    const hover = await vscode.commands.executeCommand('vscode.executeHoverProvider', uri, new vscode.Position(3, 13));
    assert(hover.some(item => item.contents.some(content => (typeof content === 'string' ? content : content.value).includes('fn double(value: number) -> number'))));
    report.checks.push('Real hover provider shows the annotated function signature.');
    const definitions = await vscode.commands.executeCommand('vscode.executeDefinitionProvider', uri, new vscode.Position(3, 13));
    assert(definitions.some(item => (item.uri || item.targetUri).toString() === uri.toString() && (item.range || item.targetRange).start.line === 0));
    report.checks.push('Real definition provider returns the function declaration.');

    const references = await vscode.commands.executeCommand('vscode.executeReferenceProvider', uri, new vscode.Position(3, 13));
    assert(references.some(item => item.uri.toString() === uri.toString() && item.range.start.line === 3));
    report.checks.push('Real reference provider finds the function call.');
    await vscode.commands.executeCommand('zensigil.restartServer');
    await until(async () => {
      const result = await vscode.commands.executeCommand('vscode.executeDefinitionProvider', uri, new vscode.Position(3, 13));
      return result?.some(item => (item.uri || item.targetUri).toString() === uri.toString());
    }, 'navigation after server restart');
    report.checks.push('Server restart restores open source and navigation without reloading the window.');

    const symbols = await vscode.commands.executeCommand('vscode.executeDocumentSymbolProvider', uri);
    assert(symbols.some(item => item.name === 'amount'));
    report.checks.push('Real symbol provider lists local declarations.');
    const formatting = await vscode.commands.executeCommand('vscode.executeFormatDocumentProvider', uri, {tabSize: 4, insertSpaces: true});
    assert(formatting.length > 0);
    const formatted = new vscode.WorkspaceEdit();
    for (const edit of formatting) formatted.replace(uri, edit.range, edit.newText);
    assert(await vscode.workspace.applyEdit(formatted));
    assert(document.getText().includes('let amount = 3'));
    report.checks.push('Real formatting provider returns normalized source.');
    async function replace(text) {
      const edit = new vscode.WorkspaceEdit();
      edit.replace(uri, new vscode.Range(0, 0, document.lineCount, 0), text);
      assert(await vscode.workspace.applyEdit(edit));
    }
    await replace('let count: integer = "three"\nemit count\n');
    const warning = await until(() => vscode.languages.getDiagnostics(uri).find(item => item.code === 'W_TYPE'), 'type advice');
    assert.equal(warning.severity, vscode.DiagnosticSeverity.Warning);
    report.checks.push('A known type conflict appears as Warning, not Error.');
    await replace('fn fail():\n    return missing\n');
    const error = await until(() => vscode.languages.getDiagnostics(uri).find(item => item.code === 'E_NAME'), 'binding error');
    assert.equal(error.severity, vscode.DiagnosticSeverity.Error);
    assert.equal(error.range.start.line, 1);
    report.checks.push('An unsaved binding error appears as Error at the correct line.');
    await replace(source);
    await until(() => vscode.languages.getDiagnostics(uri).length === 0, 'diagnostic repair');
    assert.equal(await fs.readFile(uri.fsPath, 'utf8'), source);
    report.checks.push('Repair clears diagnostics; tests leave the disk source unchanged.');
    report.ok = true;
  } catch (error) {
    report.error = error.stack || String(error);
    throw error;
  } finally {
    if (evidence) {
      await fs.mkdir(path.dirname(evidence), {recursive: true});
      await fs.writeFile(evidence, JSON.stringify(report, null, 2) + '\n');
    }
  }
};
