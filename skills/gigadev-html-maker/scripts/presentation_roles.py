"""Reviewed separation of source chrome/background paint from editable content."""
import json, re, sys
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

def norm(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()

def block_text(block):
    return norm(' '.join(p.get('text', '') for p in block.get('paragraphs', [])))

def chrome_entries(slide, canvas=None):
    entries = slide.get('sourceChrome', [])
    if not isinstance(entries, list):
        raise ValueError('sourceChrome must be an array')
    blocks = {b['id']: b for b in slide.get('blocks', []) + slide.get('metadata', [])}
    seen, roles = set(), set()
    for entry in entries:
        if not isinstance(entry, dict): raise ValueError('sourceChrome entries must be objects')
        sid, role = entry.get('sourceId'), entry.get('role')
        if role not in ('navigation', 'page-number') or role in roles or sid in seen:
            raise ValueError('sourceChrome requires unique IDs and at most one entry per role')
        block = blocks.get(sid)
        if not block or block.get('kind') not in ('text', 'metadata') or entry.get('reviewed') is not True or not norm(entry.get('reason')):
            raise ValueError('Source chrome needs a reviewed source text object and a reason')
        text = block_text(block)
        if not text or norm(entry.get('originalText')) != text:
            raise ValueError('Source chrome originalText must match the unchanged source block')
        if any(run.get('link') for p in block.get('paragraphs', []) for run in p.get('runs', [])):
            raise ValueError('Source chrome must not discard a link')
        if any(p.get('effectiveList', {}).get('kind') in ('ul', 'ol') for p in block.get('paragraphs', [])):
            raise ValueError('A source list is content, not chrome')
        if role == 'page-number' and not re.fullmatch(r'\d{1,3}', text):
            raise ValueError('Source page number must contain only a short integer')
        if role == 'navigation' and len(text) > 180:
            raise ValueError('Long prose cannot be source navigation')
        # Known direct source geometry guards against classifying a content title/value.
        if canvas and block.get('shapePropertiesXml') and block.get('kind') != 'metadata':
            node = ET.fromstring(block['shapePropertiesXml'])
            off = next((e for e in node.iter() if e.tag.endswith('}off')), None)
            ext = next((e for e in node.iter() if e.tag.endswith('}ext')), None)
            height = canvas.get('heightEMU', 0)
            if not off is None and not ext is None and height:
                y, h = int(off.get('y', 0)), int(ext.get('cy', 0))
                if h > height * .1 or (role == 'navigation' and y > height * .13) or (role == 'page-number' and y < height * .82):
                    raise ValueError('Source chrome must be a small header/footer object, not body content')
        seen.add(sid); roles.add(role)
    return entries

class Nodes(HTMLParser):
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.markup, self.stack, self.nodes = markup, [], []
        self.lines = [0]
        for m in re.finditer('\n', markup): self.lines.append(m.end())
        self.feed(markup)
    def source_offset(self):
        line, column = self.getpos(); return self.lines[line-1] + column
    def handle_starttag(self, tag, attrs):
        node = {'tag':tag, 'attrs':dict(attrs), 'start':self.source_offset(), 'end':self.source_offset()+len(self.get_starttag_text()), 'text':'', 'children':[]}
        self.nodes.append(node)
        for parent in self.stack: parent['children'].append(node)
        if tag not in self.VOID: self.stack.append(node)
        if tag == 'br': self.handle_data(' ')
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1]['tag'] == tag: self.stack.pop()
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i]['tag'] == tag:
                end = self.markup.find('>', self.source_offset()) + 1
                for n in self.stack[i:]: n['end'] = end
                del self.stack[i:]; break
    def handle_data(self, value):
        for node in self.stack: node['text'] += value

def prepare(slide, markup, canvas=None, final=False):
    entries = chrome_entries(slide, canvas)
    if entries and (slide.get('header','full')=='none' or (any(e['role']=='navigation' for e in entries) and slide.get('header','full')!='full')):
        raise ValueError('Reviewed source chrome requires its canonical show/export header')
    bg = slide.get('background') or {}
    background_ids = [v['sourceId'] for v in [bg, *bg.get('layers', [])] if v.get('sourceId')]
    declared = {b['id']: b for b in slide.get('blocks', [])}
    roles = {e['sourceId']:e for e in entries}
    if len(set(background_ids)) != len(background_ids) or set(background_ids) & set(roles):
        raise ValueError('A source object cannot serve two presentation roles')
    for sid in background_ids:
        if sid not in declared or declared[sid].get('kind') not in ('image','geometry'):
            raise ValueError('Background sourceId must reference a source image/geometry')
    if bg.get('sourceId') and declared[bg['sourceId']].get('kind') == 'image' and bg.get('asset') != declared[bg['sourceId']].get('asset'):
        raise ValueError('Background asset must match the reviewed source image')
    parsed, remove = Nodes(markup), []
    for sid in [*background_ids, *roles]:
        matches = [n for n in parsed.nodes if n['attrs'].get('data-source-id') == sid]
        if len(matches) > 1: raise ValueError('Ambiguous source role target: ' + sid)
        if not matches: continue  # New authored bodies may already omit reviewed chrome/paint.
        node = matches[0]
        if any(n['attrs'].get('data-source-id') for n in node['children']):
            raise ValueError('A presentation role must not remove other source targets')
        if sid in roles:
            if node['tag'] in ('h1','h2') or norm(node['text']) != norm(roles[sid]['originalText']):
                raise ValueError('A content heading or changed text cannot be silently removed as chrome')
        remove.append((node['start'],node['end']))
    for start,end in sorted(remove,reverse=True): markup = markup[:start] + markup[end:]
    if final:
        retained = {n['attrs'].get('data-source-id') for n in Nodes(markup).nodes}
        for block in slide.get('blocks', []):
            if block.get('backgroundCandidate') and block['id'] not in background_ids and block['id'] in retained:
                decision = slide.get('sourceImageRoles', {}).get(block['id'], {})
                if decision.get('role') != 'illustration' or decision.get('reviewed') is not True or not norm(decision.get('reason')):
                    raise ValueError(f'{slide["id"]}: full-canvas source image {block["id"]} is still inside content; use background.sourceId or a reviewed illustration decision')
            text = block_text(block)
            if block.get('kind') == 'text' and block['id'] not in roles and canvas and block.get('shapePropertiesXml'):
                n=ET.fromstring(block['shapePropertiesXml']);off=next((e for e in n.iter() if e.tag.endswith('}off')),None);ext=next((e for e in n.iter() if e.tag.endswith('}ext')),None)
                if off is not None and ext is not None:
                    h=canvas.get('heightEMU',0);w=canvas.get('widthEMU',0);y=int(off.get('y',0));x=int(off.get('x',0));height=int(ext.get('cy',0))
                    candidate=h and height<h*.1 and ((y<h*.13 and 0<len(text)<=180) or (y>h*.82 and x>w*.75 and re.fullmatch(r'\d{1,3}',text)))
                    decision=slide.get('sourceChromeDecisions',{}).get(block['id'],{})
                    if candidate and block['id'] in retained and not (decision.get('role')=='content' and decision.get('reviewed') is True and norm(decision.get('reason'))):
                        raise ValueError(f'{slide["id"]}: source header/footer {block["id"]} needs sourceChrome classification or an explicit reviewed content decision')
    return markup

def audit(source, project):
    rows=[]
    for slide in project['slides']:
        original=next((s for s in source['slides'] if s.get('sourceNumber')==slide.get('sourceNumber')),None)
        if not original:
            if slide.get('sourceChrome'): raise ValueError('Source chrome has no matching independent source slide')
            continue
        original_blocks={b['id']:b for b in original.get('blocks', [])+original.get('metadata', [])}
        # Validate source location/kind using the independent extraction too,
        # rather than trusting derivative geometry as an omission licence.
        chrome_entries({**slide,'blocks':original.get('blocks',[]),'metadata':original.get('metadata',[])},source.get('source',{}).get('canvas'))
        for entry in chrome_entries(slide, source.get('source', {}).get('canvas')):
            b=original_blocks.get(entry['sourceId'])
            if not b or block_text(b)!=norm(entry['originalText']):raise ValueError('Source chrome differs from independent PPTX inventory')
            rows.append({'slide':original['sourceNumber'],'slideId':slide['id'],**entry})
    return rows

if __name__=='__main__':
    try:
        if sys.argv[1]=='--project-only':
            project=json.load(open(sys.argv[2])); rows=[]
            for slide in project['slides']:
                prepare(slide,slide.get('html',''),project.get('source',{}).get('canvas'))
                rows.extend({'slideId':slide['id'],**e} for e in chrome_entries(slide,project.get('source',{}).get('canvas')))
        else: rows=audit(json.load(open(sys.argv[1])),json.load(open(sys.argv[2])))
        print(json.dumps({'status':'pass','entries':rows}))
    except (ValueError,KeyError,TypeError) as error: print(json.dumps({'status':'fail','error':str(error)}));sys.exit(1)
