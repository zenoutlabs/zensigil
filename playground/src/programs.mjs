import {validateModules} from './modules.mjs';
export const DRAFT_KEY = 'zensigil-draft-v1';
export const LIBRARY_KEY = 'zensigil-library-v1';
export const blankProgram = () => ({ format: 'zensigil-program', format_version: 1, language_version: '0.8.0', name: 'Untitled program', source: '# Write your ZenSigil program here.\nsay "Hello, ZenSigil"\n', data_text: '{}', contract_text: '', proposal_contract_text: '', modules: {}, tests: {} });
const bytes = value => new TextEncoder().encode(value).length;
export function validateProgram(value, {allowBlankName = false} = {}) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || value.format !== 'zensigil-program') throw new Error('Choose a ZenSigil program exported as a .sigil.json file.');
  if (value.format_version !== 1 || !['0.2.0', '0.3.0', '0.4.0', '0.5.0', '0.6.0', '0.7.0', '0.8.0'].includes(value.language_version)) throw new Error('This program uses an unsupported format or language version. Expected format 1 and ZenSigil 0.2.0, 0.3.0, 0.4.0, 0.5.0, 0.6.0, 0.7.0 or 0.8.0.');
  const keys = ['format', 'format_version', 'language_version', 'name', 'source', 'data_text', 'contract_text', 'proposal_contract_text', 'modules', 'tests', ...(Object.hasOwn(value, 'entry_path') ? ['entry_path'] : [])];
  if (Object.keys(value).some(key => !keys.includes(key))) throw new Error('This program contains unsupported fields.');
  value = {...value, modules: validateModules(Object.hasOwn(value, 'modules') ? value.modules : {}), tests: validateModules(Object.hasOwn(value, 'tests') ? value.tests : {}), language_version: '0.8.0', proposal_contract_text: Object.hasOwn(value, 'proposal_contract_text') ? value.proposal_contract_text : ''};
  if (Object.hasOwn(value, 'entry_path')) {
    if (typeof value.entry_path !== 'string') throw new Error('entry_path must be a root-relative .zs path.');
    validateModules({[value.entry_path]: value.source});
    for (const [name, source] of [...Object.entries(value.modules), ...Object.entries(value.tests)]) {
      const left = value.entry_path.toLowerCase(), right = name.toLowerCase();
      if (value.entry_path === name) {
        if (value.source !== source) throw new Error('The entry path must have identical source wherever it is included.');
      } else if (left === right || left.startsWith(right + '/') || right.startsWith(left + '/')) {
        throw new Error('The entry path must not conflict with a module or test path.');
      }
    }
  }
  for (const [name, source] of Object.entries(value.tests)) {
    for (const [module, body] of Object.entries(value.modules)) {
      const left = name.toLowerCase(), right = module.toLowerCase();
      if (name === module) {
        if (source !== body) throw new Error('A shared module and test path must contain identical source text.');
      } else if (left === right || left.startsWith(right + '/') || right.startsWith(left + '/')) {
        throw new Error('Module and test paths must not conflict, including when ignoring letter case.');
      }
    }
  }
  for (const [field, limit] of [['name', 80], ['source', 65536], ['data_text', 1048576], ['contract_text', 262144], ['proposal_contract_text', 262144]]) {
    if (typeof value[field] !== 'string') throw new Error(`The program is missing a valid ${field} field.`);
    if (/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(value[field])) throw new Error(`${field} contains an invalid Unicode character. Replace any broken characters and try again.`);
    if ((field === 'name' ? value[field].length : bytes(value[field])) > limit) throw new Error(`${field} is too large (maximum ${limit}${field === 'name' ? ' characters' : ' UTF-8 bytes'}).`);
  }
  if (!allowBlankName && !value.name.trim()) throw new Error('Give your program a name before saving.');
  return Object.fromEntries(keys.map(key => [key, value[key]]));
}
export const decodeProgram = text => {
  if (bytes(text) > 10 * 1024 * 1024) throw new Error('That file exceeds the 10 MiB portable program limit.');
  let value;
  try { value = JSON.parse(text); } catch { throw new Error('This file is not valid JSON. Choose a .sigil.json program exported from ZenSigil.'); }
  // JSON.parse alone silently takes the last duplicate key. Reject ambiguity in files.
  const stack = [];
  const tokens = /"(?:[^"\\]|\\.)*"|[{}\[\]:,]/g;
  for (const match of text.matchAll(tokens)) {
    const token = match[0];
    if (token === '{') stack.push(new Set());
    else if (token === '[') stack.push(null);
    else if (token === '}' || token === ']') stack.pop();
    else if (token.startsWith('"') && /^\s*:/.test(text.slice(match.index + token.length))) {
      const key = JSON.parse(token);
      const keys = stack.at(-1);
      if (keys?.has(key)) throw new Error(`Duplicate program field: ${key}. Each field must appear once.`);
      keys?.add(key);
    }
  }
  return validateProgram(value);
};
export const encodeProgram = program => {
  const text = JSON.stringify(validateProgram(program), null, 2);
  if (bytes(text) > 10 * 1024 * 1024) throw new Error('Portable program exceeds the 10 MiB file limit after JSON encoding.');
  return text;
};
export const filename = name => (name.replace(/[^a-z0-9_-]+/gi, '-').replace(/^-|-$/g, '').toLowerCase() || 'program');
export function readLibrary(storage) {
  const raw = storage.getItem(LIBRARY_KEY);
  if (!raw) return [];
  const data = JSON.parse(raw);
  if (data.version !== 1 || !Array.isArray(data.programs)) throw new Error('The saved program library has an unsupported format.');
  return data.programs.map(item => {
    if (typeof item.id !== 'string') throw new Error('A saved program has an invalid identifier.');
    return { id: item.id, program: validateProgram(item.program) };
  });
}

// Drafts can be unfinished, including their names. Keep every raw text field intact.
export function decodeDraft(text) {
  const draft = JSON.parse(text);
  if (!draft || draft.version !== 1) throw new Error('Unsupported draft version.');
  return validateProgram(draft.program, {allowBlankName: true});
}
export function readSavedProgram(storage, id) {
  const item = readLibrary(storage).find(entry => entry.id === id);
  if (!item) throw new Error('That saved program is no longer available in this browser.');
  return item.program;
}

// Read immediately before mutation so unrelated saves from other tabs are retained.
export function removeSavedProgram(storage, id) {
  const latest = readLibrary(storage);
  if (!latest.some(item => item.id === id)) throw new Error('That saved program is no longer available in this browser.');
  const next = latest.filter(item => item.id !== id);
  storage.setItem(LIBRARY_KEY, JSON.stringify({version: 1, programs: next}));
  return next;
}
export function sourceSelection(source, line, column = 1) {
  const lines = source.split('\n');
  const index = Math.max(0, Math.min(lines.length - 1, (Number(line) || 1) - 1));
  const start = lines.slice(0, index).reduce((total, text) => total + text.length + 1, 0);
  return {start: start + Array.from(lines[index]).slice(0, Math.max(0, (Number(column) || 1) - 1)).join('').length, end: start + lines[index].length, index};
}

// One source path identifies one file, even when it has more than one role.
export function editProgram(program, field, value) {
  const next = {...program, [field]: value};
  if (field === 'source' && program.entry_path) {
    for (const map of ['modules', 'tests']) {
      if (Object.hasOwn(program[map] || {}, program.entry_path)) next[map] = {...program[map], [program.entry_path]: value};
    }
  } else if (field === 'modules' || field === 'tests') {
    const other = field === 'modules' ? 'tests' : 'modules';
    for (const [name, source] of Object.entries(value)) {
      if (program[field]?.[name] === source) continue;
      if (Object.hasOwn(next[other] || {}, name)) next[other] = {...next[other], [name]: source};
      if (program.entry_path === name) next.source = source;
    }
  }
  return next;
}
