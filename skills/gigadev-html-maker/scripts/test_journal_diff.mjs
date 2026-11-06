/* Real journal display and persistence checks; no production files are mutated. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const here=path.dirname(fileURLToPath(import.meta.url)),out=path.resolve(process.argv[2]||'');
if(!process.argv[2])throw Error('Usage: node scripts/test_journal_diff.mjs NEW_QA_DIRECTORY');
await fs.mkdir(out,{recursive:true});assert.equal((await fs.readdir(out)).length,0);
const cases=[
 ['word','Можно исправеть текст.','Можно исправить текст.'],
 ['quotes','Название "Отчёт".','Название «Отчёт».'],
 ['dash','Результат - готов.','Результат — готов.'],
 ['spaces','Текст,  затем вывод.','Текст, затем вывод.'],
 ['nbsp','В работе','В\u00a0работе'],
 ['insert','Есть результат.','Есть хороший результат.'],
 ['delete','Это лишнее слово.','Это слово.'],
 ['emoji','Команда 👩‍💻 готова.','Команда 👨‍💻 готова.'],
 ['newline','Один\nДва','Один Два'],
 ['same','Без изменений.','Без изменений.'],
 ['unsafe','Текст <img src=x onerror=alert(1)>','Текст <svg onload=alert(1)>'],
 ['long','А'.repeat(1500)+' конец','Б'.repeat(1500)+' конец']
];
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const deck={title:'Проверка подсветки журнала',version:1,cssIsolation:'strict',proofreadingStatus:'has_proposals',slides:[{id:'probe',label:'Правки текста',html:`<h1>Правки текста</h1><p data-source-id="target">${escape(cases[0][1])}</p>`}],preparationChanges:cases.map(([id,before,after],i)=>({id,slide:'probe',...(i===0?{sourceId:'target'}:{}),actor:'llm',kind:i===0?'text':'layout',status:i===0?'pending':'applied',title:id,before,after}))};
await fs.writeFile(path.join(out,'deck.json'),JSON.stringify(deck));
const theme={name:'Diff fixture',themes:['light','dark'],primary:'light',builtinFonts:true,css:'h1{font:600 60px var(--gd-display-font)}p{font:400 38px var(--gd-font)}'};
await fs.writeFile(path.join(out,'theme.json'),JSON.stringify(theme));
const html=path.join(out,'Journal.html'),built=spawnSync('python3',[path.join(here,'build.py'),path.join(out,'deck.json'),html,'--theme',path.join(out,'theme.json'),'--typography','off'],{encoding:'utf8'});assert.equal(built.status,0,built.stderr);
const modules=process.env.HTML_MAKER_NODE_MODULES,req=modules?createRequire(path.join(modules,'package.json')):createRequire(import.meta.url),{chromium}=req('playwright');
const browser=await chromium.launch({headless:true,...(process.env.HTML_MAKER_CHROME==='bundled'?{}:{channel:'chrome'})});
const checks=[],errors=[];
try{
 const ctx=await browser.newContext({viewport:{width:1440,height:1000}});await ctx.route(/^https?:/,r=>r.abort());const page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));await page.goto(pathToFileURL(html).href);await page.waitForFunction(()=>window.GigaDevJournal);
 for(const theme of ['light','dark']){
  if(await page.evaluate(()=>SalesKitUI.getState().settings.theme)!==theme)await page.locator('#sk-theme').click();
  for(const view of ['slide','full']){
   await page.evaluate(view=>GigaDevJournal.open('preparation',view),view);
   const data=await page.locator('#sk-preparation-changes .sk-revision-change').evaluateAll(rows=>rows.map(row=>{
    const read=sel=>{const node=row.querySelector(sel)?.cloneNode(true);if(!node)return null;node.querySelector('b')?.remove();for(const w of node.querySelectorAll('[data-original]'))w.textContent=w.dataset.original;return node.textContent;};
    return {id:row.querySelector('h3,summary')?.textContent,before:read('.sk-before'),after:read('.sk-after'),deleted:[...row.querySelectorAll('del')].map(n=>n.textContent),inserted:[...row.querySelectorAll('ins')].map(n=>n.textContent),unsafe:row.querySelectorAll('.sk-revision-compare img,.sk-revision-compare svg').length};
   }));
   assert.equal(data.length,cases.length);
   for(let i=0;i<cases.length;i++){assert.equal(data[i].before,cases[i][1],cases[i][0]);assert.equal(data[i].after,cases[i][2],cases[i][0]);assert.equal(data[i].unsafe,0);if(cases[i][1]!==cases[i][2])assert(data[i].deleted.length+data[i].inserted.length>0);else assert.equal(data[i].deleted.length+data[i].inserted.length,0);}
   assert.equal(data[0].deleted.join(''),'е');assert.equal(data[0].inserted.join(''),'и');
   assert(await page.locator('#sk-preparation-changes .sk-diff-space').count()>0);
   await page.screenshot({path:path.join(out,`${theme}-${view}.png`)});await page.locator('#sk-journal-close').click();
  }
 }
 checks.push('12 exact-string cases in both themes and views, Unicode/emoji, changed whitespace, no interpreted markup, bounded long diff');
 assert.equal((await page.evaluate(()=>SalesKitUI.decidePreparation('word','accept'))).ok,true);
 assert.equal(await page.locator('[data-source-id="target"]').textContent(),cases[0][2]);
 assert.equal((await page.evaluate(()=>SalesKitUI.decidePreparation('word','reject'))).ok,true);
 assert.equal(await page.locator('[data-source-id="target"]').textContent(),cases[0][1]);
 checks.push('accept/reject retains exact source text');
 await page.evaluate(()=>SalesKitUI.decidePreparation('word','accept'));
 const saved=await page.evaluate(()=>SalesKitUI.exportDocument('work'));assert.equal(typeof saved,'string');const savedFile=path.join(out,'Saved.html');await fs.writeFile(savedFile,saved);const reopened=await ctx.newPage();await reopened.goto(pathToFileURL(savedFile).href);await reopened.waitForFunction(()=>window.GigaDevJournal);assert.equal(await reopened.locator('[data-source-id="target"]').textContent(),cases[0][2]);await reopened.evaluate(()=>GigaDevJournal.open('preparation','full'));assert(await reopened.locator('#sk-preparation-changes ins').count()>0);const snapshot=await reopened.evaluate(()=>SalesKitUI.journalSnapshot());const entry=snapshot.preparation.find(c=>c.id==='word');assert.equal(entry.before,cases[0][1]);assert.equal(entry.after,cases[0][2]);assert.equal(entry.reviewState,'accepted');
 checks.push('saved/reopened exact before/after and decisions; highlights regenerated');
 await reopened.locator('#sk-journal-close').click();await reopened.locator('#editBtn').click();const target=reopened.locator('[data-source-id="target"]');await target.click();await reopened.keyboard.press('ControlOrMeta+a');await reopened.keyboard.insertText(cases[0][2]+' Новый вывод.');await reopened.locator('#sk-text-done').click();await reopened.evaluate(()=>GigaDevJournal.open('editor','full'));assert(await reopened.locator('#sk-current-changes ins').count()>0);await reopened.locator('#sk-journal-close').click();await reopened.locator('#editBtn').click();await reopened.locator('#editUndo').click();assert.equal(await target.textContent(),cases[0][2]);await reopened.locator('#editRedo').click();assert.equal(await target.textContent(),cases[0][2]+' Новый вывод.');await reopened.locator('#sk-text-done').click();
 const userSaved=await reopened.evaluate(()=>SalesKitUI.exportDocument('work'));const userFile=path.join(out,'UserSaved.html');await fs.writeFile(userFile,userSaved);const userPage=await ctx.newPage();await userPage.goto(pathToFileURL(userFile).href);await userPage.waitForFunction(()=>window.GigaDevJournal);await userPage.evaluate(()=>GigaDevJournal.open('editor','full'));assert(await userPage.locator('#sk-saved-history ins').count()>0);checks.push('real user edit, current and saved history highlighting, undo/redo');

 assert.deepEqual(errors,[]);await fs.writeFile(path.join(out,'result.json'),JSON.stringify({status:'pass',checks,pageErrors:errors},null,2));console.log(JSON.stringify({status:'pass',checks}));
}finally{await browser.close();}
