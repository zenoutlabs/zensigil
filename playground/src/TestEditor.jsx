import React, {useState} from 'react';
import {validateModules} from './modules.mjs';

export default function TestEditor({tests, selected, onSelect, onChange, inputRef, detailsRef}) {
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [confirm, setConfirm] = useState(false);
  const names = Object.keys(tests);
  const current = names.includes(selected) ? selected : names[0] || '';
  function add() {
    try {
      if (Object.hasOwn(tests, name)) throw new Error('That test file already exists.');
      const next = validateModules({...tests, [name]: 'test "My first test":\n    require 2 + 2 == 4, "Expected 4."\n'});
      onChange(next); onSelect(name); setName(''); setError(''); setConfirm(false);
    } catch (problem) {setError(problem.message);}
  }
  return <details className="sample-data" ref={detailsRef}><summary><span>Test files</span><small>{names.length ? `${names.length} separate file${names.length === 1 ? '' : 's'}` : 'Optional tests to share with this program'}</small></summary>
    <div className="data-body module-editor"><p><strong>Run tests</strong> checks the main source and these test files. Each file imports the functions it needs. Shared module tests run once. Run preview does not execute these files. Save and export keep them with your program.</p>
      <div className="library-actions"><label htmlFor="new-test">New test path<input id="new-test" value={name} onChange={event=>setName(event.target.value)} placeholder="tests/math.zs" /></label><button onClick={add}>Add test file</button></div>
      {error ? <p role="alert">{error}</p> : null}
      {current ? <><label htmlFor="selected-test">Test file</label><select id="selected-test" value={current} onChange={event=>{onSelect(event.target.value);setConfirm(false);}}>{names.map(path=><option key={path} value={path}>{path}</option>)}</select><label htmlFor="test-source">Test source code</label><textarea ref={inputRef} id="test-source" value={tests[current]} onChange={event=>onChange({...tests,[current]:event.target.value})} spellCheck="false" />
      {confirm ? <div className="library-actions"><span>Remove {current} from this draft?</span><button onClick={()=>{const next={...tests};delete next[current];onChange(next);onSelect('');setConfirm(false);}}>Confirm remove test file</button><button onClick={()=>setConfirm(false)}>Keep test file</button></div> : <button onClick={()=>setConfirm(true)}>Remove test file</button>}</> : <p>No separate test files yet. You can also put test blocks in the main source.</p>}
    </div></details>;
}
