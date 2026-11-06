#!/usr/bin/env python3
"""Rebuild an editable project with an explicit mapping into a NEW local-only HTML."""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from build import build
p=argparse.ArgumentParser(description=__doc__);p.add_argument('project');p.add_argument('out');p.add_argument('--font-map',required=True);p.add_argument('--selection',help='font_resources selection JSON for private aliases');p.add_argument('--theme');p.add_argument('--typography',choices=['off','review','apply'],default='off');p.add_argument('--final',action='store_true');p.add_argument('--composition-plan');p.add_argument('--external-media',action='store_true');a=p.parse_args()
out=Path(a.out).resolve();out.parent.mkdir(parents=True,exist_ok=True)
if out.exists():raise SystemExit('Use a new output HTML path')
media=out.parent/(out.stem+'_media')
if a.external_media and media.exists():raise SystemExit('Output media directory already exists')
# Check exact selected resources before any build, and again before applying them.
map_bytes=Path(a.font_map).read_bytes();map_digest=hashlib.sha256(map_bytes).hexdigest();selection_bytes=Path(a.selection).read_bytes() if a.selection else None;selection_digest=hashlib.sha256(selection_bytes).hexdigest() if selection_bytes else None
mapping=json.loads(map_bytes);targets=mapping.get('targets',[])
if not targets:raise SystemExit('No explicit target mappings')
selected={}
if a.selection:
    report=json.loads(selection_bytes)
    for source in report.get('sources',[]):
        for item in source.get('requirements',[]):
            r=item.get('resolution',{});alias=r.get('cssFamilyAlias')
            if r.get('status')=='exact-face-candidate' and alias:
                if alias in selected and selected[alias]!=r:raise SystemExit('Conflicting selected aliases')
                selected[alias]=r
ids=set();used_fonts={}
for item in targets:
    sid=item.get('sourceId','');family=item.get('family','')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',sid) or not re.fullmatch(r'[A-Za-z0-9 _-]+',family) or sid in ids:raise SystemExit('Invalid or duplicate target')
    ids.add(sid)
    if family.startswith('gdprivate-'):
        r=selected.get(family)
        if not r:raise SystemExit('Missing selected alias: '+family)
        file=Path(r['path']).resolve(strict=True)
        if hashlib.sha256(file.read_bytes()).hexdigest()!=r['sha256']:raise SystemExit('Selected font SHA-256 changed: '+family)
        used_fonts[file]=r['sha256']
        if item.get('weight')!=r['weight'] or item.get('fontStyle','normal')!=('italic' if r['italic'] else 'normal'):raise SystemExit('Mapped weight/style differs from selected face: '+family)
if a.final:
    if not a.composition_plan:raise SystemExit('Private final build requires --composition-plan')
    plan=json.loads(Path(a.composition_plan).read_text())
    map_sha=map_digest
    selection_sha=selection_digest
    for item in plan.get('slides',[]):
        review=item.get('visualReview',{})
        if review.get('privateFontMapSha256')!=map_sha or review.get('privateFontSelectionSha256')!=selection_sha:
            raise SystemExit('Final visual review must bind the exact private font map and selection hashes')
created_media=False
with tempfile.TemporaryDirectory(prefix='.gd-private-build-',dir=out.parent) as directory:
    temp=Path(directory);built=temp/out.name;mapped=temp/'mapped.html';staged_media=temp/(out.stem+'_media')
    build(a.project,built,theme=a.theme,typography=a.typography,final=a.final,composition_plan=a.composition_plan,external_media=a.external_media)
    cmd=[sys.executable,str(Path(__file__).resolve().parent/'font_preview.py'),str(built),a.font_map,str(mapped),'--base-dir',str(out.parent)]
    if a.selection:cmd.extend(['--selection',a.selection])
    result=subprocess.run(cmd,text=True,capture_output=True)
    if result.returncode:raise RuntimeError(result.stderr or result.stdout or 'font mapping failed')
    proof=json.loads(result.stdout)
    if hashlib.sha256(Path(a.font_map).read_bytes()).hexdigest()!=map_digest:raise RuntimeError('Font map changed during build')
    if a.selection and hashlib.sha256(Path(a.selection).read_bytes()).hexdigest()!=selection_digest:raise RuntimeError('Font selection changed during build')
    for file,digest in used_fonts.items():
        if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise RuntimeError('Selected font changed during build: '+str(file))
    try:
        if staged_media.exists():
            media.mkdir(exist_ok=False);created_media=True
            for f in staged_media.iterdir():
                if not f.is_file():raise RuntimeError('Unexpected staged media entry')
                shutil.move(str(f),str(media/f.name))
        os.link(mapped,out) # atomic creation; never replace an existing output
    except Exception:
        if created_media:shutil.rmtree(media)
        raise
    proof['project']=str(Path(a.project).resolve());proof['fontMap']=str(Path(a.font_map).resolve());proof['selection']=str(Path(a.selection).resolve()) if a.selection else None;proof['output']=str(out)
    proof['mediaDirectory']=str(media) if created_media else None
    proof['limitations'].append('Private build references local font files; their hashes are checked at build time and they must remain accessible and unchanged. No local font binaries were added to the project or packaged.')
    print(json.dumps(proof,ensure_ascii=False,indent=2))
