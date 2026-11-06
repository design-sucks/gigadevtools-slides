/* Aggregate independent gates without treating a self-consistent project as source proof. */
import fs from 'node:fs/promises';import path from 'node:path';import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
const [html,inventory,project,out,...args]=process.argv.slice(2);
if(!html||!inventory||!project||!out||args.length%2||args.some((x,i)=>i%2===0&&!['--source','--kind','--transformations','--off-canvas','--source-alpha'].includes(x)))throw Error('Usage: node check_acceptance.mjs deck.html inventory.json project.json EMPTY_QA_DIR [--source source.pptx] [--kind editable|viewing] [--transformations changes.json] [--off-canvas reviewed-omissions.json] [--source-alpha reviewed-runs.json]');
const options=Object.fromEntries(Array.from({length:args.length/2},(_,i)=>[args[i*2],args[i*2+1]]));const kind=options['--kind']||'editable';if(!['editable','viewing'].includes(kind))throw Error('Invalid delivery kind');
await fs.mkdir(out,{recursive:true});if((await fs.readdir(out)).length)throw Error('QA directory must be empty');const here=path.dirname(fileURLToPath(import.meta.url));
const run=async(name,command,arguments_)=>{const r=spawnSync(command,arguments_,{encoding:'utf8',maxBuffer:128*1024*1024});let data;try{data=JSON.parse(r.stdout)}catch{data={status:'error',error:(r.stderr||r.stdout||`exit ${r.status}`).slice(0,3000)}}await fs.writeFile(path.join(out,name+'.json'),JSON.stringify(data,null,2));return data};
const node=process.execPath;
const delivery=await run('delivery',node,[path.join(here,'check_delivery.mjs'),html,project]);
const sourceArgs=[path.join(here,'check_source_dom.mjs'),html,inventory,project,'--mode',kind];if(options['--source'])sourceArgs.push('--source',options['--source']);if(options['--transformations'])sourceArgs.push('--transformations',options['--transformations']);if(options['--off-canvas'])sourceArgs.push('--off-canvas',options['--off-canvas']);if(options['--source-alpha'])sourceArgs.push('--source-alpha',options['--source-alpha']);
const source=await run('source-dom',node,sourceArgs);
const objects=await run('source-objects',node,[path.join(here,'check_source_objects.mjs'),html,inventory,project]);
const contrast=await run('contrast',node,[path.join(here,'check_text_contrast.mjs'),html]);
const portability=await run('portability','python3',[path.join(here,'check_portability.py'),html]);
// A raw delivery failure may be reclassified only for exact omissions independently
// verified against the original PPTX and the actual DOM. Preserve the raw report.
const reviewed=(source.status==='review' && source.sourceHashVerified===true && source.offCanvasManifestSha256 && !(source.issues??[]).length)
 ? (source.observations??[]).filter(x=>x.code==='source-off-canvas-reviewed'&&x.mapping?.disposition==='omit'&&x.mapping?.targetId===null) : [];
const alphaReviewed=(source.status==='review' && source.sourceHashVerified===true && source.sourceAlphaManifestSha256 && !(source.issues??[]).length)
 ? (source.observations??[]).filter(x=>x.code==='source-alpha-reviewed'&&x.mapping?.disposition==='preserve-transparent') : [];
const adjustedDeliveryIssues=[],unadjustedDeliveryIssues=[];
for(const issue of delivery.issues??[]){
 const proof=reviewed.find(x=>issue.code==='source-target'&&issue.found===0&&issue.slide===x.slideId&&issue.sourceId===x.sourceId) || alphaReviewed.find(x=>issue.code==='source-text-invisible'&&issue.slide===x.slideId&&issue.sourceId===x.sourceId);
 if(proof)adjustedDeliveryIssues.push({issue,sourceDisposition:proof});else unadjustedDeliveryIssues.push(issue);
}
const deliveryStatus=(delivery.status==='fail'&&adjustedDeliveryIssues.length&&!unadjustedDeliveryIssues.length)?'review':delivery.status;
const effectiveDelivery={...delivery,status:deliveryStatus};
const errors=[effectiveDelivery,source,objects,contrast,portability].some(x=>x.status==='error');
const failures=[effectiveDelivery,source,objects,contrast,portability].some(x=>x.status==='fail');
const result={status:errors?'error':failures?'fail':'review',kind,sourceHash:source.sourceHashVerified?'pass':'not_checked',content:kind==='viewing'&&source.acceptance?.content==='fail'?'not_checked':source.acceptance?.content||'not_checked',structure:source.acceptance?.structure||'not_checked',editability:kind==='viewing'?'not_applicable':source.acceptance?.editability||'not_checked',deliveryCheck:deliveryStatus,rawDeliveryCheck:delivery.status,reviewedDeliveryAdjustments:adjustedDeliveryIssues,sourceObjects:objects.status,contrast:contrast.status,portability:portability.status,visual:'not_checked',mediaPlayback:'not_checked',shellRegression:'not_checked',nativePowerPoint:'not_checked',reports:Object.fromEntries(['delivery','source-dom','source-objects','contrast','portability'].map(n=>[n,path.resolve(out,n+'.json')])),limitations:['A review or pass in a component is not final visual, interactive-editing, media, shell-regression or native-PowerPoint acceptance.','A viewing delivery requires an explicit choice to forgo editability when it was originally requested.']};
// Source checks establish a narrow lower bound, not the overall design, editing,
// shell or media experience. Errors are not converted into successful reviews.
const bad=x=>x==='fail'||x==='error';
result.matrix={
 content:bad(source.status)||bad(source.acceptance?.content)?'fail':source.status==='pass'||source.status==='review'?'review':'not-run',
 structure:bad(source.status)||bad(objects.status)||bad(source.acceptance?.structure)?'fail':source.status&&objects.status?'review':'not-run',
 editability:kind==='viewing'?'not-run':bad(source.status)||bad(source.acceptance?.editability)?'fail':source.status?'review':'not-run',
 design:'not-run',shell:'not-run',media:'not-run'
};
result.limitations.push('Matrix review is not pass: manual design, complete source meaning, interaction, shell and playback evidence are not evaluated here.');
await fs.writeFile(path.join(out,'acceptance.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));process.exitCode=errors?2:failures?1:0;
