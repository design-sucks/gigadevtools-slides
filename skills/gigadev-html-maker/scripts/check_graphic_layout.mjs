/* Check explicitly annotated diagram relationships in the rendered Maker DOM. */
import fs from 'node:fs/promises';import path from 'node:path';import {createHash} from 'node:crypto';import {fileURLToPath,pathToFileURL} from 'node:url';import {createRequire} from 'node:module';
const [html]=process.argv.slice(2);if(!html)throw Error('Usage: node check_graphic_layout.mjs deck.html');
const here=path.dirname(fileURLToPath(import.meta.url));let config={};try{config=JSON.parse(await fs.readFile(path.join(here,'../runtime.local.json'),'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;}
const modules=process.env.HTML_MAKER_NODE_MODULES||config.nodeModules;const require=modules?createRequire(path.join(modules,'package.json')):createRequire(import.meta.url);const {chromium}=require('playwright');const browser=await chromium.launch({headless:true,...(process.env.HTML_MAKER_CHROME==='bundled'?{}:{channel:'chrome'})});
try{const page=await browser.newPage({viewport:{width:1920,height:1080},serviceWorkers:'block'});await page.route(/^https?:/,r=>r.abort());await page.goto(pathToFileURL(path.resolve(html)).href);await page.waitForFunction(()=>window.GigaDevDeck&&window.SalesKitMotion);const order=await page.evaluate(()=>GigaDevDeck.getState().order);const results=[];
for(const [index,id] of order.entries()){
 await page.evaluate(i=>{goTo(i);SalesKitMotion.finish()},index);await page.waitForFunction(i=>cur===i,index);
 const result=await page.evaluate(id=>{
  const slide=document.querySelector(`#slides > [data-sk-id="${CSS.escape(id)}"]`),content=slide.querySelector('.gd-content');const scale=content.getBoundingClientRect().width/content.offsetWidth||1;const issues=[],observations=[];
  const lookup=id=>content.querySelector(`[data-diagram-node="${CSS.escape(id)}"]`);
  const center=box=>({x:(box.left+box.right)/2,y:(box.top+box.bottom)/2});
  const distanceToBox=(p,b)=>Math.hypot(Math.max(b.left-p.x,0,p.x-b.right),Math.max(b.top-p.y,0,p.y-b.bottom))/scale;
  const labels=[...content.querySelectorAll('[data-diagram-label-for]')], edges=[...content.querySelectorAll('[data-diagram-edge-from][data-diagram-edge-to]')];
  const nodes=[...content.querySelectorAll('[data-diagram-node]')];
  for(const label of labels){const node=lookup(label.dataset.diagramLabelFor);if(!node){issues.push({code:'missing-node',target:label.dataset.diagramLabelFor});continue;}
   for(const marker of nodes){if((label.dataset.allowNodeOverlap||'').split(/\s+/).includes(marker.dataset.diagramNode))continue;const a=label.getBoundingClientRect(),b=marker.getBoundingClientRect();if(a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top)issues.push({code:'node-label-overlap',label:label.dataset.diagramLabelFor,node:marker.dataset.diagramNode});}
   if(!label.hasAttribute('data-anchor-dx')||!label.hasAttribute('data-anchor-dy')||!label.hasAttribute('data-anchor-tolerance')){observations.push({code:'label-anchor-unchecked',target:label.dataset.diagramLabelFor});continue;}
   const a=center(label.getBoundingClientRect()),b=center(node.getBoundingClientRect()),dx=(a.x-b.x)/scale,dy=(a.y-b.y)/scale,ex=Number(label.dataset.anchorDx),ey=Number(label.dataset.anchorDy),tol=Number(label.dataset.anchorTolerance);
   if(![dx,dy,ex,ey,tol].every(Number.isFinite)||tol<0){issues.push({code:'invalid-label-contract',target:label.dataset.diagramLabelFor});continue;}
   const axis=label.dataset.anchorAxis||'both';if(!['x','y','both'].includes(axis)){issues.push({code:'invalid-label-axis',target:label.dataset.diagramLabelFor});continue;}
   const error=axis==='x'?Math.abs(dx-ex):axis==='y'?Math.abs(dy-ey):Math.hypot(dx-ex,dy-ey);if(error>tol)issues.push({code:'label-anchor-offset',target:label.dataset.diagramLabelFor,axis,error,tolerance:tol,actual:[dx,dy],expected:[ex,ey]});
  }
  for(const edge of edges){const from=lookup(edge.dataset.diagramEdgeFrom),to=lookup(edge.dataset.diagramEdgeTo);if(!from||!to){issues.push({code:'missing-edge-node',from:edge.dataset.diagramEdgeFrom,to:edge.dataset.diagramEdgeTo});continue;}
   if(typeof edge.getTotalLength!=='function'||!edge.getScreenCTM()){observations.push({code:'edge-geometry-unavailable'});continue;}
   const length=edge.getTotalLength(),matrix=edge.getScreenCTM(),point=t=>{const p=edge.getPointAtLength(t*length),q=new DOMPoint(p.x,p.y).matrixTransform(matrix);return {x:q.x,y:q.y}};
   const tolerance=Number(edge.dataset.endpointTolerance||8);for(const [target,pos] of [[from,point(0)],[to,point(1)]]){const d=distanceToBox(pos,target.getBoundingClientRect());if(d>tolerance)issues.push({code:'detached-edge',node:target.dataset.diagramNode,distance:d,tolerance});}
   for(const label of labels){if((edge.dataset.allowLabelOverlap||'').split(/\s+/).includes(label.dataset.diagramLabelFor))continue;const box=label.getBoundingClientRect();let hit=false;for(let i=0;i<=100;i++){const p=point(i/100);if(p.x>=box.left&&p.x<=box.right&&p.y>=box.top&&p.y<=box.bottom){hit=true;break;}}if(hit)issues.push({code:'edge-label-overlap',label:label.dataset.diagramLabelFor,from:edge.dataset.diagramEdgeFrom,to:edge.dataset.diagramEdgeTo});}
  }
  return {slide:id,labels:labels.length,edges:edges.length,issues,observations};
 },id);results.push(result);
}
const issues=results.flatMap(s=>s.issues.map(i=>({slide:s.slide,...i})));const annotated=results.some(x=>x.labels||x.edges);console.log(JSON.stringify({status:issues.length?'fail':'review',htmlSha256:createHash('sha256').update(await fs.readFile(html)).digest('hex'),slides:results,limitations:['Only explicitly annotated relationships are checked; even with no reported errors the deck remains review because annotation coverage is not proven.','Path collision is sampled and can miss short intersections; visual review remains required.']},null,2));process.exitCode=issues.length?1:0;
}finally{await browser.close()}
