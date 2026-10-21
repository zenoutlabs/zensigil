import test from 'node:test';
import assert from 'node:assert/strict';
import {validateModules} from './modules.mjs';
import {blankProgram,decodeProgram,encodeProgram,decodeDraft} from './programs.mjs';
test('module bundles survive exports and draft recovery including unfinished source',()=>{
 const program={...blankProgram(),modules:{'lib/math.zs':'fn unfinished('}};
 assert.deepEqual(decodeProgram(encodeProgram(program)),program);
 assert.deepEqual(decodeDraft(JSON.stringify({version:1,program})),program);
});
test('old exports migrate with an empty module bundle',()=>{
 const old={...blankProgram(),language_version:'0.3.0'};delete old.modules;
 assert.deepEqual(decodeProgram(JSON.stringify(old)),{...old,language_version:'0.7.0',modules:{}});
});
test('module paths, aliases, text encodings and byte sizes are validated before saving',()=>{
 for(const bad of [null,[],{'../bad.zs':''},{'/bad.zs':''},{'bad\\file.zs':''},{'a.zs':'','A.zs':''},{'a.zs':'','a.zs/b.zs':''},{'a.zs':'\ud800'},{'a.zs':3},{'a.zs':'x'.repeat(65537)}])assert.throws(()=>validateModules(bad));
 assert.throws(()=>validateModules(Object.fromEntries(Array.from({length:33},(_,i)=>[`${i}.zs`,'']))));
 assert.doesNotThrow(()=>validateModules({'lib/math.zs':'# text\n'}));
});
