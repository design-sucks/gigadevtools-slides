import {randomUUID,createHash} from 'node:crypto';
import path from 'node:path';
export const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const A='http://schemas.openxmlformats.org/drawingml/2006/main',P='http://schemas.openxmlformats.org/presentationml/2006/main',R='http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const attrs=s=>Object.fromEntries([...s.matchAll(/([\w:]+)="([^"]*)"/g)].map(m=>[m[1],m[2]]));
export function color(value,opacity=1){
 if(!value||value==='none'||value==='transparent')return {color:'000000',transparency:100};
 let rgba;if(value.startsWith('#')){let h=value.slice(1);if(h.length===3)h=h.split('').map(x=>x+x).join('');rgba=[parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16),h.length===8?parseInt(h.slice(6,8),16)/255:1];}
 else if(value.startsWith('color(srgb'))rgba=value.replace(/color\(srgb\s+|\)/g,'').split(/[ /]+/).filter(Boolean).map((v,i)=>+v*(i<3?255:1));
 else{const m=value.match(/rgba?\(([^)]+)\)/);if(!m)throw Error('Unsupported computed color '+value);rgba=m[1].split(/[, /]+/).filter(Boolean).map(Number);}
 return {color:rgba.slice(0,3).map(v=>Math.round(Math.max(0,Math.min(255,v))).toString(16).padStart(2,'0')).join('').toUpperCase(),transparency:Math.round(100*(1-(rgba[3]??1)*opacity))};
}
export async function embedFonts(z,fonts){
 let pres=await z.file('ppt/presentation.xml').async('string'),rels=await z.file('ppt/_rels/presentation.xml.rels').async('string'),ct=await z.file('[Content_Types].xml').async('string');
 let list='';for(const [i,f] of fonts.entries()){z.file('ppt/fonts/font'+i+'.fntdata',f.data);list+=`<p:embeddedFont><p:font typeface="${esc(f.alias)}"/><p:regular r:id="rIdHtmlFont${i}"/></p:embeddedFont>`;rels=rels.replace('</Relationships>',`<Relationship Id="rIdHtmlFont${i}" Type="${R}/font" Target="fonts/font${i}.fntdata"/></Relationships>`);}
 if(fonts.length){pres=pres.replace(/\s(?:embedTrueTypeFonts|saveSubsetFonts)="[^"]*"/g,'').replace('<p:presentation ','<p:presentation embedTrueTypeFonts="1" saveSubsetFonts="0" ');pres=pres.replace('<p:defaultTextStyle>','<p:embeddedFontLst>'+list+'</p:embeddedFontLst><p:defaultTextStyle>');if(!ct.includes('Extension="fntdata"'))ct=ct.replace('</Types>','<Default Extension="fntdata" ContentType="application/x-fontdata"/></Types>');}
 z.file('ppt/presentation.xml',pres);z.file('ppt/_rels/presentation.xml.rels',rels);z.file('[Content_Types].xml',ct);
}
export async function normalizeParagraphs(z){
 for(const file of Object.keys(z.files).filter(n=>/^ppt\/slides\/slide\d+\.xml$/.test(n))){let xml=await z.file(file).async('string');xml=xml.replace(/<a:p>[\s\S]*?<\/a:p>/g,p=>{const props=p.match(/<a:pPr\b[\s\S]*?<\/a:pPr>/g)||[];if(props.some(v=>v!==props[0]))throw Error('Conflicting paragraph properties in '+file);return props.length?p.replace(/<a:pPr\b[\s\S]*?<\/a:pPr>/g,'').replace('<a:p>','<a:p>'+props[0]):p;});z.file(file,xml);}
}
export async function nativePaths(z,paths,svgpath){
 for(const entry of paths){
  const it=entry.item,m=it.matrix||[1,0,0,1,0,0],pt=(x,y)=>[Math.round((m[0]*x+m[2]*y+m[4]-it.x)*9525),Math.round((m[1]*x+m[3]*y+m[5]-it.y)*9525)],point=p=>`<a:pt x="${p[0]}" y="${p[1]}"/>`;
  let commands='';if(it.d){const segments=svgpath(it.d).abs().unshort().unarc().iterate((s,i,x,y)=>s[0]==='H'?[['L',s[1],y]]:s[0]==='V'?[['L',x,s[1]]]:undefined).segments;for(const s of segments){const c=s[0].toUpperCase();if(c==='M'||c==='L')commands+=`<a:${c==='M'?'moveTo':'lnTo'}>${point(pt(s[1],s[2]))}</a:${c==='M'?'moveTo':'lnTo'}>`;else if(c==='H'||c==='V')throw Error('SVG path normalization needs explicit H/V coordinates');else if(c==='C')commands+=`<a:cubicBezTo>${point(pt(s[1],s[2]))}${point(pt(s[3],s[4]))}${point(pt(s[5],s[6]))}</a:cubicBezTo>`;else if(c==='Q')commands+=`<a:quadBezTo>${point(pt(s[1],s[2]))}${point(pt(s[3],s[4]))}</a:quadBezTo>`;else if(c==='Z')commands+='<a:close/>';else throw Error('Unsupported SVG command '+c);}}
  else{for(const [i,p] of it.points.entries())commands+=`<a:${i?'lnTo':'moveTo'}>${point([Math.round((p[0]-it.x)*9525),Math.round((p[1]-it.y)*9525)])}</a:${i?'lnTo':'moveTo'}>`;if(it.tag==='polygon')commands+='<a:close/>';}
  const w=Math.max(1,Math.round(it.w*9525)),h=Math.max(1,Math.round(it.h*9525)),geometry=`<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/><a:rect l="0" t="0" r="r" b="b"/><a:pathLst><a:path w="${w}" h="${h}">${commands}</a:path></a:pathLst></a:custGeom>`;
  const file=`ppt/slides/slide${entry.slide}.xml`;let xml=await z.file(file).async('string');let found=false;xml=xml.replace(/<p:sp>[\s\S]*?<\/p:sp>/g,s=>{if(!s.includes(`name="${entry.name}"`))return s;found=true;return s.replace(/<a:prstGeom\b[\s\S]*?<\/a:prstGeom>/,geometry);});if(!found)throw Error('Missing native path '+entry.name);z.file(file,xml);
 }
}
const group='<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>';
const relations=body=>`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${body}</Relationships>`;
const rel=(id,type,target)=>`<Relationship Id="${id}" Type="${R}/${type}" Target="${target}"/>`;
export async function promoteLayouts(z,{count,numberNames}){
 const layouts=new Map(),rows=[];
 for(let i=1;i<=count;i++){
  const file=`ppt/slides/slide${i}.xml`,rf=`ppt/slides/_rels/slide${i}.xml.rels`;let xml=await z.file(file).async('string'),rels=await z.file(rf).async('string');
  let bg=xml.match(/<p:bg>[\s\S]*?<\/p:bg>/)?.[0]||'<p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>';
  const embeds=[...bg.matchAll(/r:embed="([^"]+)"/g)],media=[];
  for(const m of embeds){const r=[...rels.matchAll(/<Relationship\b[^>]*\/>/g)].map(x=>attrs(x[0])).find(r=>r.Id===m[1]);if(!r)throw Error('Background rel missing');const part=path.posix.normalize(path.posix.join('ppt/slides',r.Target)),bytes=await z.file(part).async('nodebuffer'),hash=createHash('sha256').update(bytes).digest('hex'),target='ppt/media/shared-background-'+hash.slice(0,16)+path.posix.extname(part);z.file(target,bytes);const id='rIdBackground'+media.length;bg=bg.replaceAll(`r:embed="${m[1]}"`,`r:embed="${id}"`);media.push({id,target,hash});}
  let number=null;const name=numberNames[i-1];
  if(name){const shapes=xml.match(/<p:sp>[\s\S]*?<\/p:sp>/g)||[];number=shapes.find(s=>s.includes(`name="${esc(name)}"`));if(!number)throw Error('Missing source number on '+i);const nv=id=>`<p:nvSpPr><p:cNvPr id="${id}" name="Slide Number"/><p:cNvSpPr/><p:nvPr><p:ph type="sldNum" sz="quarter" idx="10"/></p:nvPr></p:nvSpPr>`;const layoutShape=number.replace(/<p:nvSpPr>[\s\S]*?<\/p:nvSpPr>/,nv(2));const style=number.match(/<a:rPr\b[^>]*>[\s\S]*?<\/a:rPr>/)?.[0]||number.match(/<a:rPr\b[^>]*\/>/)?.[0]||'<a:rPr/>';
   const field=`<a:fld id="{${randomUUID().toUpperCase()}}" type="slidenum">${style}<a:pPr/><a:t>${i}</a:t></a:fld>`;
   const cached=layoutShape.replace(/<a:r>[\s\S]*?<\/a:r>/,field);number={source:number,layout:cached,key:cached.replace(/id="\{[^}]+\}"/g,'id="FIELD"').replace(/<a:t>\d+<\/a:t>/g,'<a:t>N</a:t>')};
   const slideShape=cached.replace(/<p:cNvPr id="2"/,'<p:cNvPr id="'+attrs(number.source.match(/<p:cNvPr\b[^>]*>/)[0]).id+'"').replace(/<p:spPr>[\s\S]*?<\/p:spPr>/,'<p:spPr/>');xml=xml.replace(number.source,slideShape);
  }
  const key=bg+'|'+media.map(m=>m.hash).join('|')+'|'+(number?.key||'');let l=layouts.get(key);if(!l){l={index:layouts.size+1,bg,media,number:number?.layout||'',slides:[]};layouts.set(key,l);}l.slides.push(i);
  xml=xml.replace(/<p:bg>[\s\S]*?<\/p:bg>/,'');rels=rels.replace(/<Relationship\b[^>]*\/>/g,r=>attrs(r).Type.endsWith('/slideLayout')?r.replace(/Target="[^"]+"/,`Target="../slideLayouts/slideLayout${l.index}.xml"`):r);z.file(file,xml);z.file(rf,rels);rows.push({slide:i,layout:l.index,nativeNumber:!!number});
 }
 const ns=`xmlns:a="${A}" xmlns:r="${R}" xmlns:p="${P}"`;
 const mp='ppt/slideMasters/slideMaster1.xml';let master=await z.file(mp).async('string');master=master.replace(/<p:sldLayoutIdLst>[\s\S]*?<\/p:sldLayoutIdLst>/,`<p:sldLayoutIdLst>${[...layouts.values()].map(l=>`<p:sldLayoutId id="${2147483648+l.index}" r:id="rIdLayout${l.index}"/>`).join('')}</p:sldLayoutIdLst>`);master=master.replace(/<p:hf\b[^>]*\/>/,'<p:hf sldNum="1" hdr="0" ftr="0" dt="0"/>');z.file(mp,master);
 const mr='ppt/slideMasters/_rels/slideMaster1.xml.rels';let mrel=await z.file(mr).async('string');mrel=mrel.replace(/<Relationship\b[^>]*\/>/g,r=>attrs(r).Type.endsWith('/slideLayout')?'':r).replace('</Relationships>',[...layouts.values()].map(l=>rel('rIdLayout'+l.index,'slideLayout',`../slideLayouts/slideLayout${l.index}.xml`)).join('')+'</Relationships>');z.file(mr,mrel);
 for(const file of Object.keys(z.files))if(/^ppt\/slideLayouts\/(?:_rels\/)?slideLayout\d+\.xml(?:\.rels)?$/.test(file))z.remove(file);
 for(const l of layouts.values()){
  z.file(`ppt/slideLayouts/slideLayout${l.index}.xml`,`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout ${ns} type="blank" preserve="1"><p:cSld name="HTML Layout ${l.index}">${l.bg}<p:spTree>${group}${l.number}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr><p:hf sldNum="1" hdr="0" ftr="0" dt="0"/></p:sldLayout>`);
  z.file(`ppt/slideLayouts/_rels/slideLayout${l.index}.xml.rels`,relations(rel('rIdMaster','slideMaster','../slideMasters/slideMaster1.xml')+l.media.map(m=>rel(m.id,'image','../media/'+path.posix.basename(m.target))).join('')));
 }
 let ct=await z.file('[Content_Types].xml').async('string');ct=ct.replace(/<Override\b[^>]*\/>/g,r=>attrs(r).PartName.startsWith('/ppt/slideLayouts/')?'':r).replace('</Types>',[...layouts.values()].map(l=>`<Override PartName="/ppt/slideLayouts/slideLayout${l.index}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>`).join('')+'</Types>');ct=ct.replace(/<Override\b[^>]*\/>/g,r=>z.file(attrs(r).PartName.replace(/^\//,''))?r:'');z.file('[Content_Types].xml',ct);
 return {masters:1,layouts:layouts.size,nativeNumbers:rows.filter(r=>r.nativeNumber).length,slides:rows};
}

// Reuse identical media bytes across slide/layout relationships. This changes
// package references only; every image's placement, crop and paint stay local.
export async function deduplicateMedia(z){
 const files=Object.keys(z.files).filter(n=>n.startsWith('ppt/media/')&&!z.files[n].dir).sort(),seen=new Map(),mapping=new Map();let rawBytesSaved=0;
 for(const file of files){const data=await z.file(file).async('nodebuffer'),hash=createHash('sha256').update(data).digest('hex');if(seen.has(hash)){mapping.set(file,seen.get(hash));rawBytesSaved+=data.length;}else seen.set(hash,file);}
 for(const file of Object.keys(z.files).filter(n=>n.endsWith('.rels'))){const folder=file==='_rels/.rels'?'':path.posix.dirname(file).replace(/\/_rels$/,'');let xml=await z.file(file).async('string');xml=xml.replace(/<Relationship\b[^>]*\/>/g,r=>{const a=attrs(r);if(a.TargetMode==='External')return r;const resolved=a.Target.startsWith('/')?a.Target.slice(1):path.posix.normalize(path.posix.join(folder,a.Target)),target=mapping.get(resolved);return target?r.replace(/Target="[^"]+"/,`Target="${esc(path.posix.relative(folder,target))}"`):r;});z.file(file,xml);}
 for(const file of mapping.keys())z.remove(file);
 const ct=await z.file('[Content_Types].xml').async('string');z.file('[Content_Types].xml',ct.replace(/<Override\b[^>]*\/>/g,r=>mapping.has(attrs(r).PartName?.replace(/^\//,''))?'':r));
 return {before:files.length,after:files.length-mapping.size,duplicateFilesRemoved:mapping.size,rawBytesSaved};
}
