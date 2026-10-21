import React, {useState} from 'react';
import {validateModules} from './modules.mjs';

export default function ModuleEditor({modules, onChange, selected, onSelect, inputRef, detailsRef}) {
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [confirm, setConfirm] = useState(false);
  const names = Object.keys(modules);
  const current = names.includes(selected) ? selected : names[0] || '';
  function add() {
    try {
      if (Object.hasOwn(modules, name)) throw new Error('That module already exists.');
      const next = validateModules({...modules, [name]: '# Pure reusable functions belong here.\n'});
      onChange(next); onSelect(name); setName(''); setError('');
    } catch (problem) {setError(problem.message);}
  }
  return <details className="sample-data" ref={detailsRef}><summary><span>Source modules</span><small>{names.length ? `${names.length} local file${names.length === 1 ? '' : 's'}` : 'Reusable pure functions; optional'}</small></summary>
    <div className="data-body module-editor"><p>Use <code>use "lib/math.zs" as math</code> in your program. Paths are relative to the program bundle. Imported files contain functions, tests, and other use declarations.</p>
      <div className="library-actions"><label htmlFor="new-module">New module path<input id="new-module" value={name} onChange={e=>setName(e.target.value)} placeholder="lib/math.zs" /></label><button onClick={add}>Add module</button></div>
      {error ? <p role="alert">{error}</p> : null}
      {current ? <><label htmlFor="selected-module">Module file</label><select id="selected-module" value={current} onChange={e=>{onSelect(e.target.value);setConfirm(false);}}>{names.map(path=><option key={path} value={path}>{path}</option>)}</select><label htmlFor="module-source">Module source code</label><textarea ref={inputRef} id="module-source" value={modules[current]} onChange={e=>onChange({...modules,[current]:e.target.value})} spellCheck="false" />
      {confirm ? <div className="library-actions"><span>Remove {current} from this draft?</span><button onClick={()=>{const next={...modules};delete next[current];onChange(next);onSelect('');setConfirm(false);}}>Confirm remove module</button><button onClick={()=>setConfirm(false)}>Keep module</button></div> : <button onClick={()=>setConfirm(true)}>Remove module</button>}</> : <p>No modules in this program yet.</p>}
    </div></details>;
}
