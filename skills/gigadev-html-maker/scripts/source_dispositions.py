"""Validate narrow, explicitly reviewed omissions of source PPTX text below a slide.

This is not a PPTX renderer; all other geometry is deliberately unresolved.
"""
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import posixpath
import re

P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS={'p':P,'a':A}


def normalized(value):
    return re.sub(r'\s+', ' ', value or '').strip()


def original_text(shape):
    paragraphs=[]
    for paragraph in shape.findall('p:txBody/a:p',NS):
        parts=[]; has_text=False
        for child in paragraph:
            if child.tag==f'{{{A}}}br':
                parts.append('\n');continue
            text=child.find('a:t',NS)
            if text is not None:
                has_text=True;parts.append(text.text or '')
        if has_text:paragraphs.append(''.join(parts))
    return ' '.join(paragraphs)


def file_digest(path):
    digest=sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            digest.update(chunk)
    return digest.hexdigest()


class SourceVerifier:
    def __init__(self,path):
        self.zip=ZipFile(path)
        self.presentation=ET.fromstring(self.zip.read('ppt/presentation.xml'))
        rel=ET.fromstring(self.zip.read('ppt/_rels/presentation.xml.rels'))
        mapping={e.get('Id'):e.get('Target','') for e in rel if e.get('TargetMode')!='External'}
        self.slides=[]
        for entry in self.presentation.findall('p:sldIdLst/p:sldId',NS):
            target=mapping[entry.get(f'{{{R}}}id')]
            self.slides.append(target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('ppt',target)))
        size=self.presentation.find('p:sldSz',NS)
        self.canvas={'width':int(size.get('cx')),'height':int(size.get('cy'))}
        self.cache={}
    def close(self):self.zip.close()
    def shape(self,number,object_id):
        if not 1<=number<=len(self.slides):raise ValueError('source slide does not exist')
        part=self.slides[number-1]
        if part not in self.cache:self.cache[part]=ET.fromstring(self.zip.read(part))
        tree=self.cache[part]
        # Direct slide shapes only: grouped / nested text is deliberately unresolved.
        shapes=[]
        for shape in tree.findall('.//p:sp',NS):
            nv=shape.find('p:nvSpPr/p:cNvPr',NS)
            if nv is not None and nv.get('id')==object_id:shapes.append(shape)
        direct=tree.findall('p:cSld/p:spTree/p:sp',NS)
        if len(shapes)!=1 or shapes[0] not in direct:raise ValueError('source object is missing, grouped or ambiguous')
        return part,shapes[0]


def validate_disposition(entry, slide, block, project, project_slide, verifier, manifest_dir, source_sha, source_canvas):
    """Return verified evidence, or raise ValueError; never infer an approval."""
    def require(condition,message):
        if not condition:raise ValueError(message)
    n=slide.get('sourceNumber');sid=block.get('id');src=block.get('source') or {}
    require(entry.get('disposition')=='omit' and entry.get('reviewed') is True,'explicit reviewed omit disposition required')
    require(isinstance(entry.get('reason'),str) and entry['reason'].strip(),'review reason required')
    require(entry.get('slide')==n and entry.get('sourceId')==sid,'slide/source ID mismatch')
    require(project_slide.get('id')==slide.get('id') and project_slide.get('sourceNumber')==n,'project slide mapping differs from independent inventory')
    require(project.get('source',{}).get('sha256')==source_sha,'project source hash differs')
    same=[b for b in project_slide.get('blocks',[]) if b.get('id')==sid]
    require(len(same)==1 and same[0]==block,'project source block is missing or altered')
    object_id=src.get('objectId')
    require(isinstance(object_id,str) and sid==f's{n}-o{object_id}' and src.get('slide')==n,'source object identity mismatch')
    require(block.get('group') is None,'grouped geometry unresolved')
    part,shape=verifier.shape(n,object_id)
    require(src.get('part')==part,'source slide part mismatch')
    text=' '.join(p.get('text','') for p in block.get('paragraphs',[]))
    require(isinstance(entry.get('sourceText'),str) and entry['sourceText']==text,'recorded source text does not exactly match inventory')
    require(bool(normalized(text)) and normalized(original_text(shape))==normalized(text),'PPTX text differs from independent inventory')
    xf=shape.find('p:spPr/a:xfrm',NS)
    require(xf is not None,'source transform is unavailable')
    require(xf.get('rot','0')=='0' and xf.get('flipH','0') in ('0','false') and xf.get('flipV','0') in ('0','false'),'rotated/flipped source geometry unresolved')
    off=xf.find('a:off',NS);ext=xf.find('a:ext',NS)
    require(off is not None and ext is not None,'source geometry is incomplete')
    try:box={'x':int(off.get('x')),'y':int(off.get('y')),'width':int(ext.get('cx')),'height':int(ext.get('cy'))}
    except (TypeError,ValueError):raise ValueError('source geometry is invalid')
    require(box['width']>0 and box['height']>0,'source geometry is empty')
    transform=block.get('transform') or {};attrs=transform.get('attributes') or {}
    children={k:v for child in transform.get('children',[]) for k,v in child.items()}
    require(attrs==dict(xf.attrib) and children.get('off')==dict(off.attrib) and children.get('ext')==dict(ext.attrib),'PPTX transform differs from independent inventory')
    require(entry.get('geometryEMU')==box and entry.get('canvasEMU')==verifier.canvas,'recorded geometry/canvas differs from PPTX')
    require(source_canvas=={'widthEMU':verifier.canvas['width'],'heightEMU':verifier.canvas['height']},'independent inventory canvas differs from PPTX')
    require(project.get('source',{}).get('canvas')==source_canvas,'project canvas differs from PPTX')
    require(box['y']>verifier.canvas['height'],'source is not fully below the canvas')
    body=shape.find('p:txBody/a:bodyPr',NS)
    require(body is not None and body.get('anchor','t')=='t' and body.get('vert','horz')=='horz' and body.get('rot','0')=='0','text orientation/anchor unresolved')
    try:require(int(body.get('tIns','0'))>=0,'negative top inset unresolved')
    except ValueError:raise ValueError('text inset is invalid or unresolved')
    require(not any(shape.findall('.//a:'+tag,NS) for tag in ('effectLst','effectDag','scene3d','sp3d','prstTxWarp')),'text or shape effects/warp unresolved')
    render=entry.get('sourceRender');render_hash=entry.get('sourceRenderSha256')
    require(isinstance(render,str) and render.strip() and re.fullmatch(r'[0-9a-fA-F]{64}',str(render_hash or '')),'render path and SHA-256 required')
    path=(manifest_dir/render).resolve()
    require(path.is_file() and file_digest(path)==render_hash.lower(),'source render is unavailable or hash differs')
    return {'code':'source-off-canvas-reviewed','slide':n,'sourceId':sid,'slideId':slide.get('id'),
            'sourceText':text,'geometryEMU':box,'canvasEMU':verifier.canvas,
            'mapping':{'disposition':'omit','targetId':None},'reason':entry['reason'],
            'sourcePart':part,'sourceRender':str(path),'sourceRenderSha256':render_hash.lower(),
            'review':'required: rendered-page provenance and visual absence must be verified by a human'}


def scan_saved_html(path, wanted):
    """Stream inert HTML and find matching source IDs, including excluded slides."""
    from html.parser import HTMLParser
    class Scanner(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True);self.matches=[]
        def handle_starttag(self, tag, attrs):
            attrs=dict(attrs);source_id=attrs.get('data-source-id')
            if source_id in wanted:self.matches.append({'sourceId':source_id,'tag':tag})
        def handle_startendtag(self, tag, attrs):self.handle_starttag(tag,attrs)
    scanner=Scanner()
    with Path(path).open('r',encoding='utf8') as stream:
        for chunk in iter(lambda:stream.read(256*1024),''):scanner.feed(chunk)
    scanner.close()
    return scanner.matches


if __name__=='__main__':
    import argparse
    import json
    parser=argparse.ArgumentParser(description='Inert streamed source-ID scan of saved HTML')
    parser.add_argument('html',type=Path);parser.add_argument('manifest',type=Path)
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text())
    wanted={entry.get('sourceId') for entry in manifest.get('dispositions',[]) if isinstance(entry,dict) and isinstance(entry.get('sourceId'),str)}
    print(json.dumps(scan_saved_html(args.html,wanted),ensure_ascii=False))
