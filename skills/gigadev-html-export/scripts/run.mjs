// Bootstrap uses only Node's standard library; it never installs dependencies.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.dirname(here),args=process.argv.slice(2);
const value=n=>{const i=args.indexOf(n);return i<0?undefined:args[i+1]};
if(args.includes('--help')){console.log('node scripts/run.mjs --source deck.html --out NEW_DIRECTORY [--format pptx|pdf|both] [--groups auto|profile.json] [--inspect] [--cache-dir DIRECTORY] [--no-cache] [--no-slide-cache]\nnode scripts/run.mjs --doctor [--format pdf] [--pdf-mode raster]\nnode scripts/run.mjs --compare --source EXPORT_DIR --powerpoint-pdf proof.pdf --out REVIEW_DIR [--only-outliers]\nOptional host runtime config: --runtime config.json (or runtime.local.json beside SKILL.md).');process.exit(0);}
const configFile=value('--runtime')||path.join(root,'runtime.local.json');
const config=fs.existsSync(configFile)?JSON.parse(fs.readFileSync(configFile,'utf8')):{};
const runtime=path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies');
const compare=args.includes('--compare'),format=value('--format')||'pptx',raster=value('--pdf-mode')==='raster';
const wanted=compare?[]:['playwright','pptxgenjs','jszip','sharp'];
const canResolve=(directory,packages)=>{try{const req=createRequire(directory?path.join(path.resolve(directory),'package.json'):import.meta.url);for(const name of packages)req.resolve(name);return true}catch{return false}};
const pick=(items,test)=>items.find(v=>v!==undefined&&test(v));
const nodes=pick([process.env.HTML_EXPORT_NODE_MODULES,config.nodeModules,'',path.join(runtime,'node/node_modules')],v=>canResolve(v,wanted));
const fonts=pick([process.env.HTML_EXPORT_FONT_MODULES,config.fontModules,nodes],v=>canResolve(v,['fonteditor-core','svgpath']));
const pythonPackages=compare||raster?['pypdf','fontTools','pymupdf','PIL']:format==='pdf'?['pypdf']:['pypdf','fontTools'];
const pythonCode='import importlib,sys;[importlib.import_module(x) for x in sys.argv[1:]]';
const python=pick([process.env.HTML_EXPORT_PYTHON,config.python,process.env.VIRTUAL_ENV&&path.join(process.env.VIRTUAL_ENV,process.platform==='win32'?'Scripts/python.exe':'bin/python'),path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python'),path.join(runtime,'python/bin/python3'),'python3','python'],v=>spawnSync(v,['-c',pythonCode,...pythonPackages],{stdio:'ignore'}).status===0);
let chromeExecutable=null;
if(!compare&&nodes!==undefined){
 const req=createRequire(nodes?path.join(nodes,'package.json'):import.meta.url);
 if((process.env.HTML_EXPORT_CHROME||config.chrome)==='bundled')chromeExecutable=req('playwright').chromium.executablePath();
 else if(process.platform==='darwin')chromeExecutable=pick(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',path.join(os.homedir(),'Applications/Google Chrome.app/Contents/MacOS/Google Chrome')],fs.existsSync);
 else if(process.platform==='win32')chromeExecutable=pick([process.env.PROGRAMFILES,process.env['PROGRAMFILES(X86)'],process.env.LOCALAPPDATA].filter(Boolean).map(p=>path.join(p,'Google/Chrome/Application/chrome.exe')),fs.existsSync);
 else{const r=spawnSync('which',['google-chrome','google-chrome-stable'],{encoding:'utf8'});chromeExecutable=r.stdout?.trim().split('\n')[0]||null;}
}
const errors=[];
if(value('--runtime')&&!fs.existsSync(configFile))errors.push('Explicit runtime config does not exist.');
if(process.env.HTML_EXPORT_NODE_MODULES&&!canResolve(process.env.HTML_EXPORT_NODE_MODULES,wanted))errors.push('Explicit HTML_EXPORT_NODE_MODULES is invalid.');
if(process.env.HTML_EXPORT_FONT_MODULES&&!compare&&format!=='pdf'&&!canResolve(process.env.HTML_EXPORT_FONT_MODULES,['fonteditor-core','svgpath']))errors.push('Explicit HTML_EXPORT_FONT_MODULES is invalid.');
if(process.env.HTML_EXPORT_PYTHON&&spawnSync(process.env.HTML_EXPORT_PYTHON,['-c',pythonCode,...pythonPackages],{stdio:'ignore'}).status!==0)errors.push('Explicit HTML_EXPORT_PYTHON is invalid.');
if(!compare&&(!chromeExecutable||!fs.existsSync(chromeExecutable)))errors.push('Chrome is missing; install Chrome or Playwright Chromium and set HTML_EXPORT_CHROME=bundled.');
if(!compare&&nodes===undefined)errors.push('Node dependencies missing; install package.json or configure nodeModules.');if(!compare&&format!=='pdf'&&fonts===undefined)errors.push('Font dependencies missing; configure fontModules or install package.json.');if(!python)errors.push('Python dependencies missing: '+pythonPackages.join(', '));
const env={...process.env};if(nodes)env.HTML_EXPORT_NODE_MODULES=nodes;if(fonts)env.HTML_EXPORT_FONT_MODULES=fonts;if(python)env.HTML_EXPORT_PYTHON=python;if(config.chrome&&!env.HTML_EXPORT_CHROME)env.HTML_EXPORT_CHROME=config.chrome;
const result={status:errors.length?'blocked':'ready',node:process.execPath,nodeModules:nodes||'(skill-local)',fontModules:fonts??null,python:python||null,pythonPackages,chrome:env.HTML_EXPORT_CHROME||'installed Chrome',chromeExecutable,config:fs.existsSync(configFile)?configFile:null,errors};
if(args.includes('--doctor')||errors.length){console.log(JSON.stringify(result));process.exitCode=errors.length?1:0;}
else{
 const forwarded=args.filter((v,i)=>v!=='--compare'&&v!=='--runtime'&&(i===0||args[i-1]!=='--runtime'));
 const cmd=compare?python:process.execPath,script=path.join(here,compare?'compare.py':'export.mjs');
 const child=spawnSync(cmd,[script,...forwarded],{env,stdio:'inherit'});if(child.error)throw child.error;process.exitCode=child.status??1;
}
