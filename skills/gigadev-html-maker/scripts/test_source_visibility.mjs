/* Regression for independent source visibility and painted list markers. */
import assert from 'node:assert/strict';import fs from 'node:fs/promises';import os from 'node:os';import path from 'node:path';import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const out=process.argv[2] ? path.resolve(process.argv[2]) : await fs.mkdtemp(path.join(os.tmpdir(),'gd-source-visibility-'));
await fs.mkdir(out,{recursive:true});if((await fs.readdir(out)).length)throw Error('Output directory must be empty');
const python=process.env.HTML_MAKER_PYTHON||'python3';const ordered={status:'resolved',kind:'ol',attributes:{type:'arabicPeriod'}},unordered={status:'resolved',kind:'ul'};
const block=kind=>({id:'list',kind:'text',paragraphs:[{text:'First point',level:0,effectiveList:kind},{text:'Second point',level:0,effectiveList:kind}]});
const second={id:'last',kind:'text',paragraphs:[{text:'Second slide remains visible'}]};
const cases=[
 {name:'visible_two_slides',expected:'pass'},
 {name:'display_contents',wrap:'style="display:contents"',expected:'pass'},
 {name:'hidden_empty_blocks',wrap:'style="display:none"',empty:true,expected:'fail',code:'source-text-invisible'},
 {name:'hidden_child',secondStyle:' style="display:none"',expected:'fail',code:'source-text-invisible'},
 {name:'transparent',wrap:'style="opacity:0"',expected:'fail',code:'source-text-invisible'},
 {name:'off_canvas',wrap:'style="transform:translateX(-4000px)"',expected:'fail',code:'source-text-clipped'},
 {name:'clipped',wrap:'style="height:2px;overflow:hidden"',expected:'fail',code:'source-text-clipped'},
 {name:'marker_clipped',listStyle:' style="padding-left:0;overflow:hidden"',expected:'fail',code:'list-marker-clipped'},
 {name:'marker_reset',listStyle:' style="list-style:none"',expected:'fail',code:'list-marker-missing'},
 {name:'marker_pseudo_empty',extra:'<style>li::marker{content:""}</style>',expected:'fail',code:'list-marker-missing'},
 {name:'marker_transparent',extra:'<style>li::marker{color:transparent}</style>',expected:'fail',code:'list-marker-missing'},
 {name:'numbered_reset',ordered:true,listStyle:' style="list-style:none"',expected:'fail',code:'list-marker-missing'},
 {name:'numbered_wrong_type',ordered:true,listStyle:' style="list-style-type:lower-roman"',expected:'fail',code:'list-marker-type-mismatch'},
 {name:'custom_unapproved',listStyle:' style="list-style:none"',extra:'<style>li::before{content:"• ";color:white}</style>',expected:'fail',code:'custom-list-marker-unapproved'},
 {name:'custom_approved',listStyle:' style="list-style:none"',extra:'<style>li::before{content:"• ";color:white}</style>',approved:true,expected:'review',observation:'custom-list-marker-review'},
];
const run=(cmd,args)=>{const r=spawnSync(cmd,args,{encoding:'utf8',maxBuffer:64*1024*1024,env:process.env});if(r.error)throw r.error;return r};
const results=[];
for(const c of cases){
 const dir=path.join(out,c.name);await fs.mkdir(dir);const type=c.ordered?'ol':'ul',b=block(c.ordered?ordered:unordered);
 const body=`${c.extra??''}<div data-source-id="list" ${c.wrap??''}><${type}${c.listStyle??''}><li>First point</li><li${c.secondStyle??''}>Second point</li></${type}></div>`;
 const project={title:'Source visibility test',slides:[{id:'s1',sourceNumber:1,blocks:c.empty?[]:[b],html:body},{id:'s2',sourceNumber:2,blocks:[second],html:'<p data-source-id="last">Second slide remains visible</p>'}]};
 if(c.approved)project.deliveryReview={customListMarkers:[{slide:'s1',sourceId:'list',approved:true,reason:'Approved marker treatment for this sample.'}]};
 const inventory={source:{sha256:'a'.repeat(64)},slides:[{id:'s1',sourceNumber:1,blocks:[b]},{id:'s2',sourceNumber:2,blocks:[second]}]};
 const proj=path.join(dir,'project.json'),inv=path.join(dir,'inventory.json'),html=path.join(dir,'deck.html');await fs.writeFile(proj,JSON.stringify(project));await fs.writeFile(inv,JSON.stringify(inventory));
 const build=run(python,[path.join(here,'build.py'),proj,html]);assert.equal(build.status,0,build.stderr);
 const source=run(process.execPath,[path.join(here,'check_source_dom.mjs'),html,inv,proj]);await fs.writeFile(path.join(dir,'source.json'),source.stdout);assert(source.stdout,source.stderr);const result=JSON.parse(source.stdout);
 assert.equal(result.status,c.expected,c.name+': '+source.stdout);if(c.code)assert(result.issues.some(x=>x.code===c.code),c.name+': '+source.stdout);if(c.observation)assert(result.observations.some(x=>x.code===c.observation),c.name+': '+source.stdout);
 if(['visible_two_slides','display_contents','hidden_empty_blocks','marker_reset','numbered_reset','custom_approved'].includes(c.name)){
  const delivery=run(process.execPath,[path.join(here,'check_delivery.mjs'),html,proj]);await fs.writeFile(path.join(dir,'delivery.json'),delivery.stdout);assert(delivery.stdout,delivery.stderr);const d=JSON.parse(delivery.stdout);
  if(['visible_two_slides','display_contents'].includes(c.name))assert.equal(d.status,'pass');
  if(c.name==='hidden_empty_blocks')assert.equal(d.status,'review');
  if(['marker_reset','numbered_reset'].includes(c.name))assert(d.issues.some(x=>x.code==='list-marker-missing'),delivery.stdout);
  if(c.name==='custom_approved')assert.equal(d.status,'review');
 }
 if(['visible_two_slides','hidden_empty_blocks','marker_reset'].includes(c.name)){
  const agg=run(process.execPath,[path.join(here,'check_acceptance.mjs'),html,inv,proj,path.join(dir,'acceptance'),'--kind','editable']);await fs.writeFile(path.join(dir,'acceptance-stdout.json'),agg.stdout);assert(agg.stdout,agg.stderr);const result=JSON.parse(agg.stdout);
  if(c.name==='visible_two_slides')assert.notEqual(result.status,'fail',agg.stdout);
  else assert.equal(result.status,'fail',agg.stdout);
 }
 results.push({name:c.name,status:result.status,issues:result.issues.map(x=>x.code),observations:result.observations.map(x=>x.code)});console.log(c.name+' PASS');
}
await fs.writeFile(path.join(out,'summary.json'),JSON.stringify(results,null,2));
