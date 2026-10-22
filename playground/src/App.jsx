import React, { useEffect, useRef, useState } from 'react';
import CodeEditor from './CodeEditor.jsx';
import Preview from './Preview.jsx';
import Guide from './Guide.jsx';
import ModuleEditor from './ModuleEditor.jsx';
import TestEditor from './TestEditor.jsx';
import { blankProgram, decodeProgram, encodeProgram, validateProgram, readLibrary, readSavedProgram, removeSavedProgram, decodeDraft, filename, DRAFT_KEY, LIBRARY_KEY, sourceSelection, editProgram } from './programs.mjs';

import { requestProgram } from './requests.mjs';

const problem = (message, code = 'E_INPUT') => ({ ok: false, proposals: [], notes: [], diagnostics: [{ code, message }] });
function recover() {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return { program: blankProgram(), recovered: false };
    return { program: decodeDraft(raw), recovered: true };
  } catch { return { program: blankProgram(), recovered: false, error: 'Could not restore the browser draft. Browser storage may be unavailable or the draft may be damaged.' }; }
}
function downloadText(text, name, type = 'application/json') {
  const url = URL.createObjectURL(new Blob([text], {type}));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export default function App() {
  const [initial] = useState(recover);
  const [program, setProgram] = useState(initial.program);
  const [examples, setExamples] = useState([]);
  const [selected, setSelected] = useState('');
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState('stale');
  const [page, setPage] = useState('playground');
  const [library, setLibrary] = useState([]);
  const [savedId, setSavedId] = useState(null);
  const [baseline, setBaseline] = useState(initial.recovered ? '' : JSON.stringify(initial.program));
  const [message, setMessage] = useState(initial.recovered ? 'Recovered your latest draft from this browser. Run preview when ready.' : '');
  const [storageError, setStorageError] = useState(initial.error || '');
  const [pending, setPending] = useState(null);
  const [deleteId, setDeleteId] = useState(null);
  const [requestMode, setRequestMode] = useState('run');
  const [selectedModule, setSelectedModule] = useState('');
  const [moduleJump, setModuleJump] = useState(null);
  const [selectedTest, setSelectedTest] = useState('');
  const [testJump, setTestJump] = useState(null);
  const testInput = useRef(null);
  const testDetails = useRef(null);
  const moduleInput = useRef(null);
  const moduleDetails = useRef(null);
  const editor = useRef(null);
  const activeRequest = useRef(null);
  const actions = useRef(null);
  const sequence = useRef(0);
  const touched = useRef(initial.recovered);
  const importInput = useRef(null);
  const dirty = JSON.stringify(program) !== baseline;
  const dirtyRef = useRef(dirty);
  dirtyRef.current = dirty;
  const example = examples.find(item => item.id === selected);

  function invalidate() {
    sequence.current += 1; activeRequest.current?.abort();
    activeRequest.current = null;
  }
  async function preview(current, mode = 'run') {
    invalidate();
    const requestId = sequence.current;
    const controller = new AbortController(); activeRequest.current = controller;
    setRequestMode(mode); setStatus('running'); setResult(null); setMessage('');
    try {
      const body = await requestProgram(mode, current, {signal: controller.signal});
      if (requestId !== sequence.current) return;
      if (mode === 'format' && body.ok) {edit('source', body.source); setMessage('Source formatted. Run or test again to update results.');}
      else {setResult(body); setStatus(mode === 'check' ? 'checked' : 'done');}
    } catch (error) {
      if (requestId !== sequence.current) return;
      setResult(problem(error.name === 'TypeError' ? 'Cannot reach the local interpreter. Start it with python3 -m zensigil serve, then retry.' : error.message, error.kind === 'input' ? 'E_INPUT' : 'E_CONNECTION'));
      setStatus(error.kind === 'input' ? (mode === 'check' ? 'checked' : 'done') : 'failed-request');
    } finally { if (requestId === sequence.current) activeRequest.current = null; }
  }
  useEffect(() => {
    try { setLibrary(readLibrary(localStorage)); } catch { setStorageError('Could not read your saved programs. Export your draft to keep a portable copy.'); }
    const controller = new AbortController();
    fetch('/api/examples', {signal: controller.signal}).then(response => {
      if (!response.ok) throw new Error('examples'); return response.json();
    }).then(items => {
      setExamples(items);
      if (!touched.current && items.length) openExample(items[0]);
    }).catch(error => {
      if (error.name !== 'AbortError') setMessage('Examples could not load. You can still write, save, and import programs. Start the local server to run previews.');
    });
    const refresh = event => {
      if (event.key !== LIBRARY_KEY && event.key !== null) return;
      try { setLibrary(readLibrary(localStorage)); }
      catch { setStorageError('Saved programs changed in another tab but could not be read. Export your draft to keep it safe.'); }
    };
    window.addEventListener('storage', refresh);
    return () => { controller.abort(); invalidate(); window.removeEventListener('storage', refresh); };
  }, []);
  useEffect(() => {
    if (!touched.current) return;
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify({version: 1, program})); }
    catch { setStorageError('Your latest draft could not be saved in this browser. Export a program file to keep your changes.'); }
  }, [program]);

  function edit(field, value) {
    touched.current = true; invalidate();
    setProgram(current => editProgram(current, field, value)); setResult(null); setStatus('stale'); setMessage('');
  }
  function openProgram(next, id = null, exampleId = '') {
    touched.current = true; invalidate();
    setProgram(next); setBaseline(JSON.stringify(next)); setSavedId(id); setSelected(exampleId);
    setResult(null); setStatus('stale'); setMessage('Program opened. Run preview when ready.'); setPending(null); setDeleteId(null); setSelectedModule(''); setModuleJump(null); setSelectedTest(''); setTestJump(null);
  }
  function openExample(item) {
    openProgram({...blankProgram(), name: item.title, source: item.source, data_text: JSON.stringify(item.data, null, 2), contract_text: item.contract ? JSON.stringify(item.contract, null, 2) : '', proposal_contract_text: item.proposal_contract ? JSON.stringify(item.proposal_contract, null, 2) : '', modules: item.modules || {}}, null, item.id);
  }
  function focusSource(line, column, name = '<program>') {
    if (name && name !== '<program>' && Object.hasOwn(program.modules || {}, name)) {
      setSelectedModule(name); setModuleJump({line, column, name});
    } else if (name && name !== '<program>' && Object.hasOwn(program.tests || {}, name)) {
      setSelectedTest(name); setTestJump({line, column, name});
    } else editor.current?.focusLine(line, column);
  }
  useEffect(() => {
    if (!moduleJump || !moduleInput.current) return;
    const source = program.modules?.[moduleJump.name];
    if (typeof source !== 'string') return;
    moduleDetails.current.open = true;
    const range = sourceSelection(source, moduleJump.line, moduleJump.column);
    moduleInput.current.focus(); moduleInput.current.setSelectionRange(range.start, range.end);
    moduleInput.current.scrollIntoView({block: 'center'});
    setModuleJump(null);
  }, [moduleJump, selectedModule, program.modules]);
  useEffect(() => {
    if (!testJump || !testInput.current) return;
    const source = program.tests?.[testJump.name];
    if (typeof source !== 'string') return;
    testDetails.current.open = true;
    const range = sourceSelection(source, testJump.line, testJump.column);
    testInput.current.focus(); testInput.current.setSelectionRange(range.start, range.end);
    testInput.current.scrollIntoView({block: 'center'});
    setTestJump(null);
  }, [testJump, selectedTest, program.tests]);
  function openSaved(id) {
    try { openProgram(readSavedProgram(localStorage, id), id); }
    catch (error) { setMessage(`Could not open saved program: ${error.message}`); setPending(null); }
  }
  function requestOpen(action) { if (dirtyRef.current) setPending(() => action); else action(); }
  function save(copy = false) {
    touched.current = true;
    try {
      const snapshot = validateProgram(program);
      // Re-read so another open tab's saved entries are preserved.
      const latest = readLibrary(localStorage);
      const id = !copy && savedId ? savedId : crypto.randomUUID();
      const next = [...latest.filter(item => item.id !== id), {id, program: snapshot}];
      localStorage.setItem(LIBRARY_KEY, JSON.stringify({version: 1, programs: next}));
      setLibrary(next); setSavedId(id); setBaseline(JSON.stringify(program));
      setStorageError(''); setMessage(copy ? 'Copy saved in this browser.' : 'Saved in this browser.'); return true;
    } catch (error) { setStorageError(`Could not save: ${error.message} Export a program file to keep a portable copy.`); return false; }
  }
  function exportProgram() {
    try { downloadText(encodeProgram(program), `${filename(program.name)}.sigil.json`); setMessage('Program file downloaded. It includes your code, modules, test files, input, and optional contracts.'); }
    catch (error) { setMessage(error.message); }
  }
  async function importProgram(event) {
    const file = event.target.files?.[0]; event.target.value = '';
    if (!file) return;
    try {
      if (!file.name.toLowerCase().endsWith('.sigil.json')) throw new Error('Choose a .sigil.json program file exported from ZenSigil.');
      if (file.size > 10 * 1024 * 1024) throw new Error('That file is too large to be a portable ZenSigil program.');
      const next = decodeProgram(await file.text()); requestOpen(() => openProgram(next));
    } catch (error) { setMessage(`Could not open file: ${error.message}`); }
  }
  function deleteSaved() {
    try {
      const next = removeSavedProgram(localStorage, deleteId);
      setLibrary(next);
      if (savedId === deleteId) {setSavedId(null); setBaseline('');}
      setDeleteId(null); setStorageError(''); setMessage('Saved copy deleted from this browser. Your open draft is intact.');
    } catch (error) {setStorageError(`Could not delete saved program: ${error.message}`);}
  }
  actions.current = {run: () => preview(program), save: () => save()};
  useEffect(() => {
    const shortcuts = event => {
      if (!(event.metaKey || event.ctrlKey) || event.altKey || event.isComposing || event.repeat) return;
      if (event.key === 'Enter') {event.preventDefault(); actions.current.run();}
      if (event.key.toLowerCase() === 's') {event.preventDefault(); actions.current.save();}
    };
    window.addEventListener('keydown', shortcuts);
    return () => window.removeEventListener('keydown', shortcuts);
  }, []);
  return <>
    <header className="topbar">
      <a className="wordmark" href="#" onClick={event => {event.preventDefault(); setPage('playground');}}>ZenSigil</a>
      <nav aria-label="Main navigation"><button aria-current={page === 'playground' ? 'page' : undefined} onClick={() => setPage('playground')}>Playground</button><button aria-current={page === 'guide' ? 'page' : undefined} onClick={() => setPage('guide')}>Language guide</button></nav>
      <span className="version">v0.8.0 · experimental</span>
    </header>
    {page === 'guide' ? <Guide onBack={() => setPage('playground')} /> : <main>
      <div className="intro"><h1>Expressive code. Clear intent.</h1><p>A language for your ideas. Write, check, and share programs.</p></div>
      <section className="program-library" aria-label="Your program">
        <div className="program-heading"><label htmlFor="program-name">Program name<input id="program-name" value={program.name} maxLength={80} onChange={event => edit('name', event.target.value)} /></label><span className="draft-status">{dirty ? 'Unsaved changes' : savedId ? 'Saved in this browser' : 'Local draft'}</span></div>
        <div className="library-actions"><button className="small-button" onClick={() => save()}>Save program</button><button className="small-button" onClick={() => save(true)}>Save copy</button><button onClick={() => requestOpen(() => openProgram(blankProgram()))}>New program</button><button onClick={exportProgram}>Export program</button><button onClick={() => {downloadText(program.source, `${filename(program.name)}.zs`, 'text/plain;charset=utf-8'); setMessage('Source downloaded as a .zs file. Export program to include input and contracts.');}}>Download source</button><button onClick={() => importInput.current.click()}>Import program</button><input ref={importInput} type="file" accept=".sigil.json,application/json" onChange={importProgram} hidden /></div>
        <div className="library-open"><label htmlFor="saved-program">Open saved</label><select id="saved-program" value="" onChange={event => {const id = event.target.value; if (id) requestOpen(() => openSaved(id));}}><option value="">Choose a saved program…</option>{library.map(item => <option key={item.id} value={item.id}>{item.program.name}</option>)}</select><button disabled={!savedId || !library.some(item => item.id === savedId)} onClick={() => setDeleteId(savedId)}>Delete saved copy</button><small>Saved programs and draft recovery stay in this browser. Export a .sigil.json file to share or back up.</small></div>
        {message ? <p className="library-message" role="status">{message}</p> : null}
        {storageError ? <p className="storage-error" role="alert">{storageError}</p> : null}
      </section>
      {deleteId ? <section className="open-confirm" role="dialog" aria-modal="false" aria-labelledby="delete-confirm-title"><h2 id="delete-confirm-title">Delete this saved copy?</h2><p>Delete “{library.find(item => item.id === deleteId)?.program.name || 'this program'}” from this browser? Your open draft stays available.</p><div className="library-actions"><button onClick={deleteSaved}>Confirm delete</button><button onClick={() => setDeleteId(null)}>Cancel delete</button></div></section> : null}
      {pending ? <section className="open-confirm" role="dialog" aria-modal="false" aria-labelledby="open-confirm-title"><h2 id="open-confirm-title">Keep your changes before opening another program?</h2><p>Your current draft has unsaved changes.</p><div className="library-actions"><button className="small-button" onClick={() => {if (save()) pending();}}>Save &amp; open</button><button onClick={() => pending()}>Discard &amp; open</button><button onClick={() => setPending(null)}>Cancel</button></div></section> : null}
      <div className="toolbar"><div className="example-choice"><label htmlFor="example">Example</label><select id="example" value={selected} onChange={event => {const item = examples.find(entry => entry.id === event.target.value); if (item) requestOpen(() => openExample(item));}} disabled={!examples.length}><option value="">Choose an example…</option>{examples.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></div><span className="sample-label">{selected ? 'Synthetic sample data' : 'Your local program'}</span><button disabled={status === 'running'} onClick={() => preview(program, 'format')}>Format source</button><button disabled={status === 'running'} onClick={() => preview(program, 'test')}>Run tests</button><button className="check-button" disabled={status === 'running'} onClick={() => preview(program, 'check')}>Check program</button><button disabled={status === 'running'} onClick={() => preview(program, 'lint')}>Find warnings</button><button className="primary run" disabled={status === 'running'} onClick={() => preview(program)}>{status === 'running' && requestMode === 'run' ? 'Running…' : 'Run preview'}</button></div>
      <p className="shortcut-hint">Ctrl or ⌘ + Enter runs a preview. Ctrl or ⌘ + S saves your program. Tab moves between controls.</p>
      <div className="workspace"><CodeEditor ref={editor} source={program.source} onChange={value => edit('source', value)} filename={`${filename(program.name)}.zs`} /><Preview result={result} status={status} mode={requestMode} onSourceLocation={focusSource} onRetry={() => preview(program, requestMode)} /></div>
      <details className="sample-data"><summary><svg viewBox="0 0 20 20" aria-hidden="true"><path d="m7 4 6 6-6 6" /></svg><span>Input data</span><small>{example?.summary || 'Editable JSON input'}</small></summary><div className="data-body"><label htmlFor="data">Input JSON</label><textarea id="data" value={program.data_text} onChange={event => edit('data_text', event.target.value)} spellCheck="false" /><p>Top-level input fields become variables in your program. Your draft preserves exactly what you type, including unfinished JSON.</p></div></details>
      <details className="sample-data"><summary><svg viewBox="0 0 20 20" aria-hidden="true"><path d="m7 4 6 6-6 6" /></svg><span>Input contract</span><small>Optional checks before your program runs</small></summary><div className="data-body"><label htmlFor="contract">Contract JSON (leave empty to skip)</label><textarea id="contract" value={program.contract_text} onChange={event => edit('contract_text', event.target.value)} spellCheck="false" /><p>A contract describes the input you expect, such as required fields, value types, and minimum numbers. Load the stock-review example for a starting point. Validation errors identify the affected input field.</p></div></details>
      <details className="sample-data"><summary><svg viewBox="0 0 20 20" aria-hidden="true"><path d="m7 4 6 6-6 6" /></svg><span>Proposal contract</span><small>Optional checks on the proposals your program produces</small></summary><div className="data-body"><label htmlFor="proposal-contract">Proposal contract JSON (leave empty to skip)</label><textarea id="proposal-contract" value={program.proposal_contract_text} onChange={event => edit('proposal_contract_text', event.target.value)} spellCheck="false" /><p>Describe the fields expected for each action. A preview succeeds only when every proposal matches its action contract. Check program checks the contract itself; Run preview checks the actual proposals.</p></div></details>
      <ModuleEditor modules={program.modules || {}} selected={selectedModule} onSelect={setSelectedModule} onChange={value => edit('modules', value)} inputRef={moduleInput} detailsRef={moduleDetails} />
      <TestEditor tests={program.tests || {}} selected={selectedTest} onSelect={setSelectedTest} onChange={value => edit('tests', value)} inputRef={testInput} detailsRef={testDetails} />
      <footer><p>Programs run on your local server. Proposals describe actions for review.</p><button className="download" disabled={!result?.ok || status !== 'done' || requestMode !== 'run'} onClick={() => downloadText(JSON.stringify(result, null, 2), `${filename(program.name)}-preview.json`)}>Download preview</button></footer>
    </main>}
  </>;
}
