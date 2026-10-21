export function validateModules(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length > 32) throw new Error('Use an object containing at most 32 source modules.');
  let total = 0; const names = new Set();
  for (const [name, source] of Object.entries(value)) {
    if (!name.endsWith('.zs') || name.length > 160 || name.split('/').some(part => !/^[A-Za-z0-9_][A-Za-z0-9_.-]*$/.test(part) || part === '.' || part === '..')) throw new Error('Module names must be root-relative .zs paths, such as lib/math.zs.');
    const folded = name.toLowerCase();
    if (names.has(folded)) throw new Error('Module names must also be unique ignoring letter case.');
    if ([...names].some(other => folded.startsWith(other + '/') || other.startsWith(folded + '/'))) throw new Error('A module path cannot also be another module’s directory.');
    names.add(folded);
    if (typeof source !== 'string' || /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(source)) throw new Error(`Module ${name} must contain valid Unicode source text.`);
    const size = new TextEncoder().encode(source).length; total += size;
    if (size > 65536 || total > 262144) throw new Error('Modules allow 64 KiB per file and 256 KiB in total.');
  }
  return {...value};
}
