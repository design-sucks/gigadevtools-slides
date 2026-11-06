#!/usr/bin/env python3
"""Apply an explicit font mapping to a NEW private HTML preview; no font binaries are copied."""
import argparse, hashlib, json, os, re, subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('html');p.add_argument('mapping');p.add_argument('output');p.add_argument('--private-css');p.add_argument('--base-dir',help='media base directory for a staged private build');p.add_argument('--selection',help='font_resources selection JSON; verify hashes and generate local @font-face');a=p.parse_args()
src=Path(a.html).resolve(strict=True);out=Path(a.output).resolve();raw=src.read_text();mapping=json.loads(Path(a.mapping).read_text());targets=mapping.get('targets',[])
if not targets:raise SystemExit('No explicit target mappings')
if re.search(r'<base\b',raw,re.I):raise SystemExit('Existing base requires manual review')
ids=[];rules=[]
for item in targets:
    sid=item.get('sourceId','');family=item.get('family','');weight=item.get('weight');font_style=item.get('fontStyle')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',sid) or not re.fullmatch(r'[A-Za-z0-9 _-]+',family):raise SystemExit('Invalid sourceId or family')
    if sid in ids or len(re.findall(r'data-source-id=["\']'+re.escape(sid)+r'["\']',raw))!=1:raise SystemExit('Missing, duplicate or ambiguous target: '+sid)
    if weight is not None and (not isinstance(weight,int) or weight<1 or weight>1000):raise SystemExit('Invalid weight')
    if font_style not in (None,'normal','italic'):raise SystemExit('Invalid fontStyle')
    if not family.startswith('gdprivate-') and (weight is not None or font_style is not None):raise SystemExit('Bundled fallback must preserve per-run weight and style')
    if item.get('allowSyntheticStyle',False) not in (True,False):raise SystemExit('Invalid synthetic style policy')
    ids.append(sid);selector='[data-source-id="'+sid+'"]'
    rules.append(selector+','+selector+' *{font-family:'+json.dumps(family)+' !important;'+('font-weight:'+str(weight)+' !important;' if weight else '')+('font-style:'+font_style+' !important;' if font_style else '')+('font-synthesis:none !important;' if family.startswith('gdprivate-') else 'font-synthesis:style !important;' if item.get('allowSyntheticStyle') else '')+'}')
if a.private_css and a.selection:raise SystemExit('Choose --private-css or --selection')
css=Path(a.private_css).read_text() if a.private_css else ''
if a.selection:
    report=json.loads(Path(a.selection).read_text());selected={}
    for source in report.get('sources',[]):
        for item in source.get('requirements',[]):
            r=item.get('resolution',{});alias=r.get('cssFamilyAlias')
            if r.get('status')=='exact-face-candidate' and alias:
                if alias in selected and selected[alias]!=r:raise SystemExit('Conflicting selected aliases')
                selected[alias]=r
    used={item['family'] for item in targets if item['family'].startswith('gdprivate-')}
    for alias in sorted(used):
        if alias not in selected:raise SystemExit('Missing selected alias: '+alias)
        r=selected[alias];font=Path(r['path']).resolve(strict=True)
        if hashlib.sha256(font.read_bytes()).hexdigest()!=r['sha256']:raise SystemExit('Selected font SHA-256 changed: '+alias)
        if any(item['family']==alias and (item.get('weight')!=r['weight'] or item.get('fontStyle','normal')!=('italic' if r['italic'] else 'normal')) for item in targets):raise SystemExit('Mapped weight/style differs from selected face: '+alias)
        css+='@font-face{font-family:'+json.dumps(alias)+';src:url('+json.dumps(font.as_uri())+');font-weight:'+str(r['weight'])+';font-style:'+('italic' if r['italic'] else 'normal')+';}\n'
if any(item['family'].startswith('gdprivate-') for item in targets):
    if not (a.selection or a.private_css):raise SystemExit('Private alias needs a resource selection')
    check=subprocess.run(['node',str(Path(__file__).resolve().parent/'check_font_mapping_dom.mjs'),str(src),str(Path(a.mapping).resolve())],text=True,capture_output=True)
    if check.returncode:raise SystemExit('Cannot apply single-face mapping: '+(check.stderr or check.stdout).strip())
if re.search(r'</style',css,re.I):raise SystemExit('Invalid stylesheet')
if 'id="gd-private-font-map"' in raw:raise SystemExit('Private font mapping already exists')
base=Path(a.base_dir).resolve(strict=True) if a.base_dir else src.parent
if not base.is_dir():raise SystemExit('Invalid base directory')
map_json=json.dumps(mapping,ensure_ascii=False).replace('<','\\u003c')
insert='<base href="'+base.as_uri()+'/">\n<style data-gd-private-font-preview>\n'+css+'\n'+'\n'.join(rules)+'\n</style>\n<script type="application/json" id="gd-private-font-map">'+map_json+'</script>\n'
head=re.search(r'</head\s*>',raw,re.I);body=re.search(r'<body\b',raw,re.I)
if not head or not body or head.start()>body.start():raise SystemExit('Ambiguous HTML head')
new=re.sub(r'</head\s*>',lambda m:insert+m.group(),raw,count=1,flags=re.I)
with out.open('x') as f:f.write(new)
print(json.dumps({'status':'private-preview-created','source':str(src),'sourceSha256':hashlib.sha256(raw.encode()).hexdigest(),'output':str(out),'outputSha256':hashlib.sha256(new.encode()).hexdigest(),'targets':targets,'limitations':['Private local-only preview; mapping is explicit and not applied to the source project.','Rendered font, glyph coverage, line wrapping and layout require browser verification.','No font file was copied; redistribution requires separate rights review.']},ensure_ascii=False,indent=2))
