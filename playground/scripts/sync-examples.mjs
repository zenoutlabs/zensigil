import {mkdir, readdir, copyFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root = fileURLToPath(new URL('../../', import.meta.url));
const destination = path.join(root,'zensigil','demo');
await mkdir(destination,{recursive:true});
await copyFile(path.join(root,'THIRD_PARTY_NOTICES.md'),path.join(root,'zensigil','THIRD_PARTY_NOTICES.md'));
async function copy(source, target) {
  await mkdir(target,{recursive:true});
  for (const item of await readdir(source,{withFileTypes:true})) {
    if (item.isDirectory() && item.name === 'lib') await copy(path.join(source,item.name),path.join(target,item.name));
    else if (item.isFile() && /\.(zs|json)$/.test(item.name)) await copyFile(path.join(source,item.name),path.join(target,item.name));
  }
}
await copy(path.join(root,'examples'),destination);
