#!/usr/bin/env python3
"""Inspect explicitly supplied sfnt resources and resolve PPTX requirements without copying fonts."""
import argparse, hashlib, json, struct, unicodedata
from pathlib import Path


def norm(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value)).casefold().split())


def read_sfnt(path):
    data = path.read_bytes()
    def bounds(offset, length):
        if offset < 0 or length < 0 or offset + length > len(data):
            raise ValueError('Truncated font table')
    bounds(0, 12)
    if data[:4] not in (b'OTTO', b'\x00\x01\x00\x00', b'true'):
        raise ValueError('Only standalone OTF/TTF sfnt files are supported')
    count = struct.unpack_from('>H', data, 4)[0]
    bounds(12, count * 16)
    tables = {}
    for i in range(count):
        tag, _, off, length = struct.unpack_from('>4sIII', data, 12 + i * 16)
        bounds(off, length)
        if tag in tables: raise ValueError('Duplicate font table')
        tables[tag] = (off, length)
    if b'fvar' in tables: raise ValueError('Variable font faces require independent instance resolution')
    if b'name' not in tables or b'OS/2' not in tables: raise ValueError('Missing name or OS/2 table')
    off, size = tables[b'name']
    if size < 6: raise ValueError('Truncated name table')
    _, names_count, strings_off = struct.unpack_from('>HHH', data, off)
    if 6 + 12 * names_count > size or strings_off > size: raise ValueError('Invalid name table')
    names = {}
    for i in range(names_count):
        platform, encoding, language, nameid, length, start = struct.unpack_from('>HHHHHH', data, off + 6 + i * 12)
        if nameid not in (1, 2, 4, 6, 16, 17): continue
        if strings_off + start + length > size: raise ValueError('Invalid name record')
        raw = data[off + strings_off + start:off + strings_off + start + length]
        try: value = raw.decode('utf-16be' if platform in (0, 3) else 'mac_roman' if platform == 1 else 'ascii').strip('\x00 ')
        except (UnicodeError, LookupError): continue
        if value and value not in names.setdefault(str(nameid), []): names[str(nameid)].append(value)
    os2, size = tables[b'OS/2']
    if size < 64: raise ValueError('Truncated OS/2 table')
    weight = struct.unpack_from('>H', data, os2 + 4)[0]
    fs_type = struct.unpack_from('>H', data, os2 + 8)[0]
    selection = struct.unpack_from('>H', data, os2 + 62)[0]
    if not 1 <= weight <= 1000 or not names.get('1') or not names.get('6'): raise ValueError('Incomplete font identity')
    return {'path':str(path.resolve()), 'sha256':hashlib.sha256(data).hexdigest(), 'names':names,
            'weight':weight, 'italic':bool(selection & 1), 'fsType':fs_type, 'fsTypeHex':f'0x{fs_type:04x}',
            'postscriptName':names['6'][0], 'rights':'local-use-authorized; redistribution-and-embedding-not-authorized',
            'licenseNote':'OS/2 fsType is technical metadata, not a license or grant of rights.'}


def resolve(requirement, resources, prefer_origin=None):
    family=requirement.get('family'); bold=requirement.get('bold'); italic=requirement.get('italic')
    if not family or family.startswith('+'): return {'status':'unresolved-source-family','candidates':[]}
    matches=[]
    for face in resources:
        if face.get('declaredIdentityStatus')=='mismatch': continue
        n=face['names']; wanted=norm(family)
        family_match=wanted in {norm(x) for k in ('1','16') for x in n.get(k,[])}
        full_match=wanted in {norm(x) for k in ('4','6') for x in n.get(k,[])}
        if not (family_match or full_match): continue
        # An exact full name can identify Light/Semibold even when the source family
        # doesn't carry a numeric weight. Family-level requests need explicit style.
        specific_name=full_match and (not family_match or (n.get('16') and wanted not in {norm(x) for x in n['16']}))
        if specific_name:
            if bold is True and face['weight'] < 700: continue
            if italic is not None and bool(italic)!=face['italic']: continue
        else:
            if bold is None or italic is None: continue
            if face['weight'] != (700 if bold else 400) or face['italic'] != bool(italic): continue
        matches.append(face)
    candidates=[{'postscriptName':x['postscriptName'],'sha256':x['sha256'],'origin':x['origin'],'path':x['path']} for x in matches]
    pool=[x for x in matches if x['origin']==prefer_origin] if prefer_origin else matches
    if len(pool)==1:
        selected=pool[0]
        return {'status':'exact-face-candidate','selectionPolicy':('explicit-prefer-'+prefer_origin if prefer_origin else 'unique-exact-face'), 'postscriptName':selected['postscriptName'],'sha256':selected['sha256'],'path':selected['path'],'origin':selected['origin'],'weight':selected['weight'],'italic':selected['italic'],'candidates':candidates}
    return {'status':'ambiguous-exact-faces' if matches else 'external-or-unresolved','candidates':candidates,'selectionPolicy':('explicit-prefer-'+prefer_origin if prefer_origin else 'none')}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight',required=True,help='preflight.py JSON; source effective requirements')
    parser.add_argument('--font-dir',required=True,action='append',help='explicit directory containing the authorized files; pair each with a manifest')
    parser.add_argument('--resource-manifest',action='append',help='JSON allowlist paired with --font-dir; entries may record origin and declaredFamily')
    parser.add_argument('--prefer-origin',choices=['local','embedded'],help='explicit tie resolution; absent means ambiguous rather than silent substitution')
    parser.add_argument('--private-css',help='write a new local-only stylesheet with uniquely named candidate faces')
    args=parser.parse_args()
    if args.resource_manifest and len(args.font_dir)!=len(args.resource_manifest): raise SystemExit('Pair each --font-dir with exactly one --resource-manifest')
    roots=[Path(x).resolve(strict=True) for x in args.font_dir]
    if any(not root.is_dir() for root in roots): raise SystemExit('--font-dir must be a directory')
    candidates=[]
    for i,root in enumerate(roots):
        if args.resource_manifest:
            spec=json.loads(Path(args.resource_manifest[i]).read_text())
            if not isinstance(spec.get('files'),list) or not spec['files']: raise SystemExit('Manifest requires a nonempty files array')
            entries=[{'path':x} if isinstance(x,str) else x for x in spec['files']]
        else: entries=[{'path':p.name} for p in sorted(root.iterdir()) if p.is_file() and p.suffix.lower() in ('.ttf','.otf')]
        for entry in entries:
            if not isinstance(entry,dict) or not isinstance(entry.get('path'),str) or not entry['path']: raise SystemExit('Invalid manifest entry')
            origin=entry.get('origin','local')
            if origin not in ('local','embedded'): raise SystemExit('Unknown resource origin')
            if origin=='embedded' and (not entry.get('declaredFamily') or entry.get('declaredFace') not in ('regular','bold','italic','boldItalic')): raise SystemExit('Embedded entries require PPTX declaredFamily and declaredFace')
            relative=Path(entry['path'])
            if relative.is_absolute(): raise SystemExit('Manifest file paths must be relative to --font-dir')
            target=(root/relative).resolve(strict=True)
            if root not in target.parents or not target.is_file(): raise SystemExit('Manifest entry escapes font directory or is not a file')
            candidates.append((target,entry))
    if len({p for p,_ in candidates})!=len(candidates): raise SystemExit('Duplicate font path')
    resources=[];errors=[]
    for f,entry in candidates:
        try:
            face=read_sfnt(f);face['origin']=entry.get('origin','local')
            if face['origin']=='embedded':
                face['declaredFamily']=entry['declaredFamily'];face['declaredFace']=entry['declaredFace']
                names={norm(x) for k in ('1','4','16') for x in face['names'].get(k,[])}
                expected={'regular':(400,False),'bold':(700,False),'italic':(400,True),'boldItalic':(700,True)}[entry['declaredFace']]
                face['declaredIdentityStatus']='match' if norm(entry['declaredFamily']) in names and (face['weight'],face['italic'])==expected else 'mismatch'
                face['rights']='decoded-private-resource; redistribution-and-embedding-not-authorized'
                face['decoderStatus']='decoded-unverified; sfnt metadata inspected separately'
            resources.append(face)
        except (OSError,ValueError,struct.error) as e: errors.append({'path':str(f),'error':str(e)})
    preflight=json.loads(Path(args.preflight).read_text());sources=[]
    for source in preflight.get('sources',[]):
        fonts=source.get('fonts',{});requirements=fonts.get('effectiveRequirements',[])
        resolved=[{'requirement':req,'resolution':resolve(req,resources,args.prefer_origin)} for req in requirements]
        sources.append({'source':source.get('path'), 'requirements':resolved, 'embeddedDeclarations':fonts.get('embedded',[])})
    if args.private_css and not errors:
        selected={}
        for source in sources:
            for item in source['requirements']:
                r=item['resolution']
                if r['status']=='exact-face-candidate':
                    alias='gdprivate-'+r['sha256'][:16];r['cssFamilyAlias']=alias
                    selected[alias]=r
        css='/* PRIVATE local font references. Do not publish or package without separate rights review. */\n'
        for alias,r in sorted(selected.items()):
            css+='@font-face{font-family:'+json.dumps(alias)+';src:url('+json.dumps(Path(r['path']).as_uri())+');font-weight:'+str(r['weight'])+';font-style:'+('italic' if r['italic'] else 'normal')+';}\n'
        with open(args.private_css,'x') as f:f.write(css)
    print(json.dumps({'resources':resources,'errors':errors,'sources':sources,'limitations':['Exact identity and OS/2 metadata only; alias mapping, unresolved source style, language coverage, shaping and actual browser glyph use require review.','Candidates from local and decoded-embedded sources remain distinct; neither proves that a browser used it.','No fonts are copied, embedded, packaged, or licensed by this command.']},ensure_ascii=False,indent=2))
    if errors: raise SystemExit(1)
if __name__=='__main__':main()
