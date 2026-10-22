'use strict';
// Run only in an isolated VS Code Extension Development Host, using the launch
// recipe in docs/editor-v05.md. This harness never changes the normal user profile.
const vscode = require('vscode');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(check, label, milliseconds = 15000) {
  const deadline = Date.now() + milliseconds;
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
  const report = {ok: false, host: 'VS Code Extension Development Host', vscode: vscode.version, checks: []};
  try {
    assert(root && python && evidence, 'Set ZENSIGIL_TEST_WORKSPACE, ZENSIGIL_TEST_PYTHON and ZENSIGIL_TEST_EVIDENCE.');
    const workspace = vscode.workspace.workspaceFolders?.find(folder => path.resolve(folder.uri.fsPath) === path.resolve(root));
    assert(workspace, 'The explicitly selected synthetic workspace must be open.');
    // Trust is deliberately not disabled or fabricated. Accept the real trust UI
    // for this synthetic directory, or record the missing approval as a failed run.
    await until(() => vscode.workspace.isTrusted, 'synthetic workspace trust', 60000);
    await vscode.workspace.getConfiguration('zensigil').update('pythonPath', python, vscode.ConfigurationTarget.Global);
    report.checks.push('Trusted workspace; Python path saved only in the isolated test profile.');
    const moduleUri = vscode.Uri.file(path.join(root, 'lib/math.zs'));
    const mainUri = vscode.Uri.file(path.join(root, 'main.zs'));
    const source = 'use "lib/math.zs"\nlet amount=3\nemit ["🌱",double(amount)]\n';
    // The parent prepares this exact fixture; no unknown user document is replaced.
    assert.equal(await fs.readFile(mainUri.fsPath, 'utf8'), source);
    const extension = vscode.extensions.getExtension('zenoutlabs.zensigil');
    assert(extension, 'Development extension is installed.');
    await extension.activate();
    const document = await vscode.workspace.openTextDocument(mainUri);
    await vscode.window.showTextDocument(document);
    const completions = await until(async () => {
      const result = await vscode.commands.executeCommand('vscode.executeCompletionItemProvider', mainUri, new vscode.Position(2, 12));
      return result?.items.some(item => item.label === 'double') && result;
    }, 'completion server readiness');
    assert(completions.items.some(item => item.label === 'map'));
    report.checks.push('Real completion provider includes module functions and the standard library.');
    const hover = await vscode.commands.executeCommand('vscode.executeHoverProvider', mainUri, new vscode.Position(2, 13));
    assert(hover.some(item => item.contents.some(content => (typeof content === 'string' ? content : content.value).includes('fn double(value: number) -> number'))));
    report.checks.push('Real hover provider returns the imported typed function signature.');
    const definitions = await vscode.commands.executeCommand('vscode.executeDefinitionProvider', mainUri, new vscode.Position(2, 13));
    assert(definitions.some(item => (item.uri || item.targetUri).toString() === moduleUri.toString()));
    report.checks.push('Real definition provider navigates to the explicit source module.');

    const references = await vscode.commands.executeCommand('vscode.executeReferenceProvider', mainUri, new vscode.Position(2, 13));
    assert(references.some(item => item.uri.toString() === mainUri.toString() && item.range.start.line === 2));
    report.checks.push('Real reference provider finds the imported function call.');
    await vscode.commands.executeCommand('zensigil.restartServer');
    await until(async () => {
      const result = await vscode.commands.executeCommand('vscode.executeDefinitionProvider', mainUri, new vscode.Position(2, 13));
      return result?.some(item => (item.uri || item.targetUri).toString() === moduleUri.toString());
    }, 'module navigation after server restart');
    report.checks.push('Server restart restores workspace imports and navigation without reloading the window.');

    const symbols = await vscode.commands.executeCommand('vscode.executeDocumentSymbolProvider', mainUri);
    assert(symbols.some(item => item.name === 'amount'));
    report.checks.push('Real document-symbol provider lists local declarations.');
    const edits = await vscode.commands.executeCommand('vscode.executeFormatDocumentProvider', mainUri, {tabSize: 4, insertSpaces: true});
    assert(edits.length > 0);
    // VS Code can reduce a whole-document provider edit into smaller edits.
    // Apply the returned edits and verify their result, not their wire shape.
    const formatted = new vscode.WorkspaceEdit();
    for (const edit of edits) formatted.replace(mainUri, edit.range, edit.newText);
    assert(await vscode.workspace.applyEdit(formatted));
    assert(document.getText().includes('let amount = 3'));
    report.checks.push('Real formatting provider returns verified source edits.');
    const imported = await vscode.workspace.openTextDocument(moduleUri);
    const replacement = new vscode.WorkspaceEdit();
    replacement.replace(moduleUri, new vscode.Range(0, 0, imported.lineCount, 0), 'fn double(value: number) -> number:\n    return missing\n');
    assert(await vscode.workspace.applyEdit(replacement));
    const diagnostics = await until(() => {
      const items = vscode.languages.getDiagnostics(moduleUri);
      return items.some(item => item.code === 'E_NAME') && items;
    }, 'unsaved module diagnostic');
    assert.equal(diagnostics.find(item => item.code === 'E_NAME').range.start.line, 1);
    assert(imported.isDirty);
    report.checks.push('Unsaved module edits generate diagnostics on the correct source document.');
    const repair = new vscode.WorkspaceEdit();
    repair.replace(moduleUri, new vscode.Range(0, 0, imported.lineCount, 0), 'fn double(value: number) -> number:\n    return value * 2\n');
    assert(await vscode.workspace.applyEdit(repair));
    await until(() => vscode.languages.getDiagnostics(moduleUri).length === 0, 'diagnostic clearing');
    report.checks.push('Repairing the unsaved module clears diagnostics.');
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
