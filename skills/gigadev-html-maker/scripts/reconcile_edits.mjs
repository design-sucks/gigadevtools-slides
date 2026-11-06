/* Three-way merge of leaf text edits from saved HTML back to an authored project. */
import fs from 'node:fs/promises';import path from 'node:path';import {fileURLToPath,pathToFileURL} from 'node:url';import {createRequire} from 'node:module';
const [baseline,edited,projectFile,out]=process.argv.slice(2);if(!baseline||!edited||!projectFile||!out||process.argv.length!==6)throw Error('Usage: node reconcile_edits.mjs baseline.html edited.html project.json NEW-project.json');
if(path.dirname(path.resolve(projectFile))!==path.dirname(path.resolve(out)))throw Error('Output must remain beside the project so its asset paths remain valid');
try{await fs.access(out);throw Error('Output already exists');}catch(e){if(e.code!=='ENOENT')throw e;}
const here=path.dirname(fileURLToPath(import.meta.url));let config={};try{config=JSON.parse(await fs.readFile(path.join(here,'../runtime.local.json'),'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;}
const modules=process.env.HTML_MAKER_NODE_MODULES||config.nodeModules;const require=modules?createRequire(path.join(modules,'package.json')):createRequire(import.meta.url);const {chromium}=require('playwright');const browser=await chromium.launch({headless:true,...(process.env.HTML_MAKER_CHROME==='bundled'?{}:{channel:'chrome'})});
try {
 const snapshot=async file=>{const page=await browser.newPage({serviceWorkers:'block'});await page.route(/^https?:/,r=>r.abort());await page.goto(pathToFileURL(path.resolve(file)).href);await page.waitForFunction(()=>window.SalesKitUI&&window.GigaDevDeck);const data=await page.evaluate(()=>({state:SalesKitUI.getState(),slides:[...document.querySelectorAll('#slides > .slide[data-sk-id]')].map(s=>{const content=s.querySelector('.gd-content'),copy=content.cloneNode(true);for(const node of copy.querySelectorAll('[data-source-id]'))if(!node.querySelector('[data-source-id]'))node.innerHTML='__GD_EDITABLE_LEAF__';for(const node of copy.querySelectorAll('[data-eid],[contenteditable]')){node.removeAttribute('data-eid');node.removeAttribute('contenteditable');}return {id:s.dataset.skId,unmapped:copy.innerHTML,targets:[...content.querySelectorAll('[data-source-id]')].map(n=>({id:n.dataset.sourceId,html:n.innerHTML,hasChildren:!!n.querySelector('[data-source-id]')}))}})}));await page.close();return data;};
 const original=await snapshot(baseline),saved=await snapshot(edited),project=JSON.parse(await fs.readFile(projectFile,'utf8'));const conflicts=[],changes=[];
 const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
 const stateFields=[['order',project.order||project.slides.map(s=>s.id)],['title',project.title||path.parse(projectFile).name],['fileStem',project.fileStem||original.state.fileStem],['settings',project.restoredSettings||{...original.state.settings,...(typeof project.motion==='boolean'?{motion:project.motion}:{})}],['preparation',project.preparationChanges||[]],['history',project.restoredHistory||[]],['version',project.version||1]];
 for(const [field,current] of stateFields){const before=original.state[field],after=saved.state[field];if(same(before,after))continue;
  if(!same(current,before)&&!same(current,after)){conflicts.push({code:'concurrent-state-change',field,before,after,current});continue;}
  if(field==='settings')project.restoredSettings=after;else if(field==='preparation')project.preparationChanges=after;else if(field==='history')project.restoredHistory=after;else project[field]=after;
  changes.push({kind:'state',field,before,after});
 }
 const baseSlides=new Map(original.slides.map(s=>[s.id,s]));const savedSlides=new Map(saved.slides.map(s=>[s.id,s]));
 const modifications=[];
 for(const slide of project.slides){const base=baseSlides.get(slide.id),current=savedSlides.get(slide.id);if(!base||!current){conflicts.push({code:'missing-slide',slide:slide.id});continue;}if(base.unmapped!==current.unmapped)conflicts.push({code:'unmapped-or-layout-change',slide:slide.id});const byId=new Map();for(const x of current.targets){const list=byId.get(x.id)||[];list.push(x);byId.set(x.id,list);}
  for(const target of base.targets){if(target.hasChildren)continue;const matches=byId.get(target.id)||[];if(matches.length!==1){conflicts.push({code:'missing-or-ambiguous-target',slide:slide.id,sourceId:target.id});continue;}if(target.html===matches[0].html)continue;
   if(typeof slide.html!=='string'&&!slide.composition){conflicts.push({code:'unsupported-slide-source',slide:slide.id,sourceId:target.id});continue;}
   modifications.push({slide:slide.id,sourceId:target.id,before:target.html,after:matches[0].html});
  }
 }
 const apply=await browser.newPage();const merged=await apply.evaluate(({project,modifications})=>{
  const conflicts=[],changes=[];
    const parse=html=>{const template=document.createElement('template');template.innerHTML=html;const runs=[];const visit=(n,style={})=>{if(n.nodeType===Node.TEXT_NODE){if(n.data)runs.push({...style,text:n.data});return true;}if(n.nodeType!==Node.ELEMENT_NODE)return false;const tag=n.tagName.toLowerCase();if(tag==='br'){if(n.attributes.length)return false;runs.push({...style,text:'\n'});return true;}if(!['strong','b','em','i','a','span'].includes(tag))return false;const next={...style};if(['strong','b'].includes(tag))next.bold=true;if(['em','i'].includes(tag))next.italic=true;if(tag==='a'){const href=n.getAttribute('href');if(n.attributes.length!==1||!href||!/^(https?:\/\/|mailto:|tel:|#)/.test(href)||next.link)return false;next.link=href;}else if(n.attributes.length)return false;return [...n.childNodes].every(c=>visit(c,next));};return [...template.content.childNodes].every(n=>visit(n))?runs:null;};
    // Structural containers may contain editable descendants; their structure and attributes must remain unchanged.
    const prepare=(before,after)=>{const structural=new Set(['ul','ol','li','table','thead','tbody','tfoot','tr','td','th','caption','p','div','blockquote','figcaption']);
     const wrap=html=>{const t=document.createElement('template');t.innerHTML=html;return t};const a=wrap(before),b=wrap(after);
     // Editor-generated text wrappers are not part of authored HTML. Preserve their identity while validating, then unwrap.
     const wrappers=root=>[...root.querySelectorAll('span.sk-edit-fragment')];const aw=wrappers(a.content),bw=wrappers(b.content);
     const signature=nodes=>nodes.map(n=>[...n.attributes].map(x=>[x.name,x.value]).sort((x,y)=>x[0].localeCompare(y[0])));
     if(JSON.stringify(signature(aw))!==JSON.stringify(signature(bw)))return null;
     for(const n of [...aw,...bw]){if(n.className!=='sk-edit-fragment'||!n.dataset.eid||[...n.attributes].some(x=>!['class','data-eid'].includes(x.name)))return null;n.replaceWith(...n.childNodes);}
     const shape=root=>{const all=[...root.querySelectorAll('*')].filter(n=>structural.has(n.localName));return all.map(n=>({tag:n.localName,attrs:[...n.attributes].filter(a=>!['contenteditable','spellcheck','data-sk-editing'].includes(a.name)).map(a=>[a.name,a.value]).sort((a,b)=>a[0].localeCompare(b[0])),parent:all.indexOf(n.parentElement?.closest([...structural].join(',')))}));};
     if(JSON.stringify(shape(a.content))!==JSON.stringify(shape(b.content)))return null;
     // An authored wrapper outside the ordinary inline allowlist is trusted only
     // at the same place with exactly the same attributes as in the baseline.
     // Its ancestors are anchored too, so moving it into a new wrapper fails.
     const attrs=n=>[...n.attributes].filter(x=>!['data-eid','contenteditable','spellcheck','data-sk-editing'].includes(x.name)).map(x=>[x.name,x.value]).sort((x,y)=>x[0].localeCompare(y[0]));
     const safeInline=n=>{const tag=n.localName,at=attrs(n);if(tag==='br')return at.length===0;if(!['strong','b','em','i','a','span'].includes(tag))return false;if(tag!=='a')return at.length===0;return at.length===1&&at[0][0]==='href'&&/^(https?:\/\/|mailto:|tel:|#)/.test(at[0][1]);};
     const skeleton=root=>{let valid=true;const visit=n=>{if(n.nodeType===Node.TEXT_NODE)return [];if(n.nodeType!==Node.ELEMENT_NODE){valid=false;return [];}const children=[...n.childNodes].flatMap(visit);if(!structural.has(n.localName)&&n.querySelector([...structural].join(',')))valid=false;const alphaSibling=n.localName==='span'&&[...n.parentNode.children].some(s=>s.hasAttribute('data-source-alpha-run'));const anchored=structural.has(n.localName)||!safeInline(n)||children.length>0||alphaSibling;if(!anchored)return [];const record={tag:n.localName,attrs:attrs(n),children};if(n.hasAttribute('data-source-alpha-run')||['script','style','iframe','object','embed'].includes(n.localName))record.fixedHTML=n.innerHTML;return [record];};const result=[...root.childNodes].flatMap(visit);return valid?result:null;};
     const beforeShape=skeleton(a.content),afterShape=skeleton(b.content);if(!beforeShape||!afterShape||JSON.stringify(beforeShape)!==JSON.stringify(afterShape))return null;
     // A marker can separate bare text nodes, which are absent from the element
     // skeleton. Editing one side is safe; changes on both sides are ambiguous
     // with moving the marker and must not be written. Existing element siblings
     // must likewise remain on their original side of each marker.
     const markerContexts=root=>[...root.querySelectorAll('[data-source-alpha-run]')].map(marker=>{const siblings=[...marker.parentNode.childNodes],index=siblings.indexOf(marker);const side=nodes=>({text:nodes.filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.data).join(''),elements:nodes.filter(n=>n.nodeType===Node.ELEMENT_NODE).map(n=>JSON.stringify([n.localName,attrs(n)]))});return [side(siblings.slice(0,index)),side(siblings.slice(index+1))];});
     const priorContexts=markerContexts(a.content),nextContexts=markerContexts(b.content);if(priorContexts.length!==nextContexts.length)return null;
     const subsequence=(oldValues,newValues)=>{let i=0;for(const value of newValues)if(value===oldValues[i])i++;return i===oldValues.length;};
     for(let i=0;i<priorContexts.length;i++){const old=priorContexts[i],next=nextContexts[i];if(old[0].text!==next[0].text&&old[1].text!==next[1].text)return null;for(let side=0;side<2;side++)if(!subsequence(old[side].elements,next[side].elements))return null;}
     // Existing safe hrefs must survive in order; newly inserted safe links are allowed.
     const links=root=>[...root.querySelectorAll('a')].filter(safeInline).map(n=>n.getAttribute('href'));const previousLinks=links(a.content),nextLinks=links(b.content);let linkIndex=0;for(const href of nextLinks)if(href===previousLinks[linkIndex])linkIndex++;if(linkIndex!==previousLinks.length)return null;
     // Validate every new/unanchored inline subtree with the existing formatting
     // rules, including safe links and prohibition of nested links.
     const check=parent=>{for(const child of parent.children){if(structural.has(child.localName)){if(!check(child))return false;}else if(child.querySelector([...structural].join(',')))return false;}
      const inline=document.createElement('div');for(const child of parent.childNodes)if(!(child.nodeType===Node.ELEMENT_NODE&&structural.has(child.localName)))inline.append(child.cloneNode(true));
      for(const n of [...inline.querySelectorAll('*')])if(!safeInline(n)){for(const at of [...n.attributes])n.removeAttribute(at.name);if(!['strong','b','em','i','a','span','br'].includes(n.localName))n.replaceWith(...n.childNodes);else if(n.localName==='a')n.replaceWith(...n.childNodes);}
      return !!parse(inline.innerHTML);};
     if(!check(b.content))return null;
     for(const t of [a,b])for(const n of t.content.querySelectorAll('[data-eid],[contenteditable],[spellcheck],[data-sk-editing]'))for(const attr of ['data-eid','contenteditable','spellcheck','data-sk-editing'])n.removeAttribute(attr);
     return {before:a.innerHTML,after:b.innerHTML};};
  for(const slide of project.slides){const edits=modifications.filter(x=>x.slide===slide.id);if(!edits.length)continue;
   if(slide.composition){
    const objects=[];const walk=x=>{if(Array.isArray(x))x.forEach(walk);else if(x&&typeof x==='object'){if(x.sourceId)objects.push(x);Object.values(x).forEach(walk);}};walk(slide.composition.data);
    const render=value=>{const root=document.createElement('span');for(const r of value.runs?.length?value.runs:[{text:value.text||''}]){let n=document.createTextNode(r.text||'');if(r.link||r.href){const a=document.createElement('a');a.href=r.link||r.href;a.append(n);n=a;}if(r.bold){const b=document.createElement('strong');b.append(n);n=b;}if(r.italic){const i=document.createElement('em');i.append(n);n=i;}root.append(n);}return root.innerHTML.replace(/\n/g,'<br>');};

    for(const edit of edits){const found=objects.filter(x=>x.sourceId===edit.sourceId);if(found.length!==1||found[0].href){conflicts.push({code:'composition-target-unsupported-or-ambiguous',...edit});continue;}const value=found[0],current=render(value);if(current!==edit.before&&current!==edit.after){conflicts.push({code:'concurrent-edit',...edit,current});continue;}const runs=parse(edit.after);if(!runs){conflicts.push({code:'unsupported-inline-markup',...edit});continue;}if(current===edit.before){value.text=runs.map(r=>r.text).join('');value.runs=runs;changes.push(edit);}}
    continue;
   }
   const template=document.createElement('template');template.innerHTML=slide.html;
   for(const edit of edits){const safe=prepare(edit.before,edit.after);if(!safe){conflicts.push({code:'unsupported-inline-markup',...edit});continue;}const nodes=template.content.querySelectorAll(`[data-source-id="${CSS.escape(edit.sourceId)}"]`);if(nodes.length!==1){conflicts.push({code:'project-target-missing-or-ambiguous',...edit});continue;}const node=nodes[0];if(node.innerHTML!==safe.before&&node.innerHTML!==safe.after){conflicts.push({code:'concurrent-edit',...edit,current:node.innerHTML});continue;}if(node.innerHTML===safe.before){node.innerHTML=safe.after;changes.push(edit);}}
   slide.html=template.innerHTML;
  }
  return {project,conflicts,changes};
 },{project,modifications});await apply.close();conflicts.push(...merged.conflicts);changes.push(...merged.changes);
 if(conflicts.length){console.log(JSON.stringify({status:'conflict',conflicts,changes:[],limitations:['No project file was written. Resolve state and text conflicts before rebuilding.']},null,2));process.exitCode=1;}
 else{await fs.writeFile(out,JSON.stringify(merged.project,null,2),{flag:'wx'});console.log(JSON.stringify({status:'merged',out:path.resolve(out),changes,limitations:['Leaf text and safe inline formatting are merged on authored slides and identified structured composition text. Verify editability and render after rebuilding.','Order, identity, settings, preparation and history are reconciled; layout changes and unsupported composition markup require separate reconciliation.']},null,2));}
}finally{await browser.close()}
