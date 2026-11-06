/* Static per-slide object visibility: positive and negative regression cases. */
import assert from 'node:assert/strict';import fs from 'node:fs/promises';import path from 'node:path';import os from 'node:os';import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';
const here=path.dirname(fileURLToPath(import.meta.url));
const out=process.argv[2]?path.resolve(process.argv[2]):await fs.mkdtemp(path.join(os.tmpdir(),'gd-object-visibility-'));
await fs.mkdir(out,{recursive:true});if((await fs.readdir(out)).length)throw Error('Output directory must be empty');
const svg='data:image/svg+xml;base64,'+Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><circle cx="40" cy="40" r="35" fill="red"/></svg>').toString('base64');
const cases=[
 {name:'two_slides_loaded_svg',markup:`<img data-source-id="target" src="${svg}" style="width:80px;height:80px">`,status:'mapped_review',decoded:true},
 {name:'lazy_svg',markup:`<img data-source-id="target" loading="lazy" src="${svg}" style="width:80px;height:80px">`,status:'mapped_review',decoded:true},
 {name:'hidden_target',markup:`<img data-source-id="target" src="${svg}" style="width:80px;height:80px;visibility:hidden">`,status:'hidden'},
 {name:'hidden_ancestor',markup:`<div style="display:none"><img data-source-id="target" src="${svg}" style="width:80px;height:80px"></div>`,status:'hidden'},
 {name:'transparent_ancestor',markup:`<div style="opacity:0"><img data-source-id="target" src="${svg}" style="width:80px;height:80px"></div>`,status:'hidden'},
 {name:'zero_width',markup:`<img data-source-id="target" src="${svg}" style="width:0;height:80px">`,status:'hidden',reason:'zero-geometry'},
 {name:'off_frame',markup:`<img data-source-id="target" src="${svg}" style="width:80px;height:80px;transform:translateX(-4000px)">`,status:'hidden',reason:'fully-clipped'},
 {name:'clipped_ancestor',markup:`<div style="width:20px;height:20px;overflow:hidden"><img data-source-id="target" src="${svg}" style="width:80px;height:80px;transform:translateX(100px)"></div>`,status:'hidden',reason:'fully-clipped'},
 {name:'excluded_slide',markup:`<img data-source-id="target" src="${svg}" style="width:80px;height:80px">`,status:'slide_missing',selectedOnlyFirst:true},
 {name:'missing',markup:'<p>Not the source object</p>',status:'unmapped'},
 {name:'broken_image',markup:'<img data-source-id="target" src="data:image/png;base64,INVALID" style="width:80px;height:80px">',status:'image_load_failed'},
 {name:'hidden_child_image',markup:`<div data-source-id="target" style="width:80px;height:80px"><img src="${svg}" style="display:none"></div>`,status:'hidden'},
 {name:'duplicate',markup:`<img data-source-id="target" src="${svg}" style="width:80px;height:80px"><img data-source-id="target" src="${svg}" style="width:80px;height:80px">`,status:'ambiguous'},
 {name:'hidden_child_media',kind:'media',markup:'<div data-source-id="target" style="width:80px;height:80px"><video style="display:none"></video></div>',status:'hidden'},
 {name:'missing_media',kind:'media',markup:'<div data-source-id="target" style="width:80px;height:80px"></div>',status:'media_not_detected'},
];
const run=(command,args)=>spawnSync(command,args,{encoding:'utf8',env:process.env,maxBuffer:20*1024*1024,timeout:30000});
const checker=path.join(here,'check_source_objects.mjs'),hash=createHash('sha256').update(await fs.readFile(checker)).digest('hex');
const results=[];
for(const c of cases){
 const dir=path.join(out,c.name);await fs.mkdir(dir);const kind=c.kind||'image';
 const b1={id:'first',kind:'geometry'},b2={id:'target',kind};
 const project={title:'Object test',slides:[{id:'s1',sourceNumber:1,blocks:[b1],html:'<div data-source-id="first" style="width:80px;height:80px;background:red"></div>'},{id:'s2',sourceNumber:2,blocks:[b2],html:c.markup}]};
 if(c.selectedOnlyFirst)project.order=['s1'];
 const source={source:{sha256:'a'.repeat(64)},slides:[{id:'s1',sourceNumber:1,blocks:[b1]},{id:'s2',sourceNumber:2,blocks:[b2]}]};
 const projectPath=path.join(dir,'project.json'),inventoryPath=path.join(dir,'inventory.json'),htmlPath=path.join(dir,'deck.html');
 await fs.writeFile(projectPath,JSON.stringify(project));await fs.writeFile(inventoryPath,JSON.stringify(source));
 const build=run('python3',[path.join(here,'build.py'),projectPath,htmlPath]);assert.equal(build.status,0,c.name+': '+build.stderr);
 const tested=run(process.execPath,[checker,htmlPath,inventoryPath,projectPath]);assert.equal(tested.status,0,c.name+': '+tested.stderr);await fs.writeFile(path.join(dir,'report.json'),tested.stdout);
 const report=JSON.parse(tested.stdout),first=report.objects.find(o=>o.sourceId==='first'),target=report.objects.find(o=>o.sourceId==='target');
 assert.equal(first.status,'mapped_review',c.name+': first slide');assert.equal(target.status,c.status,c.name+': '+JSON.stringify(target));
 if(c.decoded){assert.equal(target.target.images[0].status,'decoded');assert.equal(target.target.images[0].visible,true);}
 if(c.reason)assert.equal(target.target.reason,c.reason,c.name+': '+JSON.stringify(target));
 results.push({case:c.name,status:'pass',targetStatus:target.status});console.log(c.name+' PASS');
}
assert.equal(createHash('sha256').update(await fs.readFile(checker)).digest('hex'),hash,'Checker changed during test');
await fs.writeFile(path.join(out,'summary.json'),JSON.stringify({checkerSha256:hash,results},null,2));
