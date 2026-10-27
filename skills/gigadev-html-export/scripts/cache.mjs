import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
export const digest=data=>createHash('sha256').update(data).digest('hex');

export class ExportCache{
 constructor(directory,enabled=true){this.directory=directory;this.enabled=enabled;this.stats={enabled,directory,fontHits:0,fontMisses:0,slideHits:0,slideMisses:0,slideBypasses:0,invalidEntries:0,bytesRestored:0,bytesWritten:0,lookupSeconds:0,writeErrors:0};}
 entry(kind,key){if(!['fonts','slides'].includes(kind)||!/^[a-f0-9]{64}$/.test(key))throw Error('Invalid cache address');return path.join(this.directory,kind,key);}
 async restore(kind,key,destination,expectedNames){
  if(!this.enabled)return false;
  const started=performance.now(),directory=this.entry(kind,key);let manifest;
  try{
   manifest=JSON.parse(await fs.readFile(path.join(directory,'manifest.json'),'utf8'));
   if(manifest.schema!==1||manifest.key!==key||manifest.kind!==kind||!Array.isArray(manifest.files)||!manifest.files.length)throw Error('Invalid cache manifest');
   if(JSON.stringify(manifest.files.map(f=>f.name).sort())!==JSON.stringify([...expectedNames].sort()))throw Error('Cache artifact set differs');
   const buffers=[];
   for(const f of manifest.files){
    if(typeof f.name!=='string'||path.basename(f.name)!==f.name||!f.name||!/^[a-f0-9]{64}$/.test(f.sha256))throw Error('Invalid cache file');
    const data=await fs.readFile(path.join(directory,f.name));if(digest(data)!==f.sha256)throw Error('Cache checksum differs');buffers.push([f.name,data]);
   }
   for(const [name,data] of buffers){await fs.writeFile(path.join(destination,name),data);this.stats.bytesRestored+=data.length;}
   this.stats[kind==='fonts'?'fontHits':'slideHits']++;return true;
  }catch(e){if(e.code!=='ENOENT')this.stats.invalidEntries++;this.stats[kind==='fonts'?'fontMisses':'slideMisses']++;return false;}
  finally{this.stats.lookupSeconds+=(performance.now()-started)/1000;}
 }
 async store(kind,key,source,names){
  if(!this.enabled)return;
  try{
  const directory=this.entry(kind,key);await fs.mkdir(directory,{recursive:true});const files=[];
  for(const name of names){
   if(path.basename(name)!==name)throw Error('Cache file must be flat');
   const data=await fs.readFile(path.join(source,name)),tmp=path.join(directory,'.tmp-'+randomUUID());
   await fs.writeFile(tmp,data);await fs.rename(tmp,path.join(directory,name));files.push({name,sha256:digest(data),bytes:data.length});this.stats.bytesWritten+=data.length;
  }
  // Commit last. Concurrent/incomplete writes can only become misses on read.
  const tmp=path.join(directory,'.manifest-'+randomUUID());await fs.writeFile(tmp,JSON.stringify({schema:1,kind,key,files}));await fs.rename(tmp,path.join(directory,'manifest.json'));
  }catch(e){this.stats.writeErrors++;this.enabled=false;this.stats.enabled=false;this.stats.disabledReason='cache-write-error: '+(e.code||e.message);}
 }
}

// Only self-contained paint can be reused without a separate file-dependency adapter.
export function hasExternalPaint(items){
 return items.some(it=>{
  if(it.tag!=='VIDEO'&&it.src&&!it.src.startsWith('data:'))return true;
  const paint=[it.svg||'',it.props?.backgroundImage||''].join(' ');
  return [...paint.matchAll(/(?:href\s*=\s*["']([^"']+)|url\(\s*["']?([^)'"\s]+))/g)].some(m=>{const url=m[1]||m[2];return !url.startsWith('data:')&&!url.startsWith('#')});
 });
}
