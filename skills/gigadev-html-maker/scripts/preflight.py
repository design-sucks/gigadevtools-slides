#!/usr/bin/env python3
"""Read-only source inventory and decision prompts for Maker; never builds a deck."""
from __future__ import annotations
import argparse
import difflib
import hashlib
import json
import posixpath
import re
import sys
import subprocess
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile
from pptx_text_styles import build_context, styles, resolve_run

NS = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'p14':'http://schemas.microsoft.com/office/powerpoint/2010/main'}
RID = '{%s}id' % NS['r']


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def local(tag):
    return tag.rsplit('}', 1)[-1]


def local_font_matches(sources):
    """Inspect installed font metadata on macOS; no files are copied or licensed."""
    if sys.platform != 'darwin':
        return {'status':'not-checked','reason':'Local font discovery is currently implemented for macOS only.'}
    try:
        result = subprocess.run(['/usr/sbin/system_profiler','SPFontsDataType','-json'],capture_output=True,text=True,check=True,timeout=30)
        font_files = json.loads(result.stdout).get('SPFontsDataType',[])
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        return {'status':'not-checked','reason':str(e)}
    index = {}
    def key(value): return re.sub(r'[^\w]+','',value.casefold())
    for item in font_files:
        if item.get('enabled') == 'no': continue
        for face in item.get('typefaces',[]):
            if face.get('enabled') == 'no': continue
            entry={'family':face.get('family'),'fullName':face.get('fullname'),'style':face.get('style'),'path':item.get('path'),'embeddingFlag':face.get('embeddable')}
            for name in (face.get('family'),face.get('fullname'),face.get('_name')):
                if name:index.setdefault(key(name),[]).append(entry)
    for source in sources:
        if source.get('sourceType') != 'pptx': continue
        fonts=source['fonts'];faces=set(fonts['explicitSlideFaces']) | set(fonts.get('themeFaceNames',[])) | {r['family'] for r in fonts.get('effectiveRequirements',[]) if r.get('family')}
        fonts['localMatches']={name:index.get(key(name),[]) for name in sorted(faces) if not name.startswith('+')}
        fonts['localMatchStatus']='checked'
    return {'status':'checked','limitations':['Exact face/family names only; aliases and unresolved inherited fonts require review.','An embedding flag does not grant redistribution or embedding rights.']}


def relationships(z, part):
    name = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
    if name not in z.namelist():
        return {}
    out = {}
    for e in ET.fromstring(z.read(name)):
        target = e.get('Target', '')
        external = e.get('TargetMode') == 'External'
        target = target if external else (target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(part), target)))
        out[e.get('Id')] = {'target': target, 'type': e.get('Type', '').rsplit('/', 1)[-1], 'external': external}
    return out


def font_records(counter,examples):
    return [{'family':k[0], 'declared':k[1], 'source':k[2], 'sizePt':k[3], 'bold':k[4], 'italic':k[5], 'runs':v, 'examples':examples.get(k,[])} for k,v in sorted(counter.items(),key=lambda x:repr(x[0]))]


def inspect_pptx(path):
    with ZipFile(path) as z:
        names = set(z.namelist())
        pres = ET.fromstring(z.read('ppt/presentation.xml'))
        rels = relationships(z, 'ppt/presentation.xml')
        ids = pres.findall('p:sldIdLst/p:sldId', NS)
        id_to_num = {e.get('id'): i for i, e in enumerate(ids, 1)}
        sections = []
        for section in pres.findall('.//p14:section', NS):
            members = [id_to_num[e.get('id')] for e in section.findall('.//p14:sldId', NS) if e.get('id') in id_to_num]
            sections.append({'name': section.get('name', ''), 'slides': members})
        size = pres.find('p:sldSz', NS)
        canvas = {'widthEMU': int(size.get('cx')), 'heightEMU': int(size.get('cy'))} if size is not None else None
        embedded_fonts = []
        for entry in pres.findall('p:embeddedFontLst/p:embeddedFont', NS):
            face = entry.find('p:font', NS)
            variants = []
            for variant in entry:
                rid = variant.get(RID)
                if rid:
                    rel = rels.get(rid, {})
                    variants.append({'style': local(variant.tag), 'part': rel.get('target'), 'availableInPackage': rel.get('target') in names})
            embedded_fonts.append({'family': face.get('typeface') if face is not None else None, 'variants': variants})
        declared_faces = Counter()
        for slide_id in ids:
            part = rels[slide_id.get(RID)]['target']
            tree = ET.fromstring(z.read(part))
            for e in tree.iter():
                if local(e.tag) in ('latin','ea','cs') and e.get('typeface'):
                    declared_faces[e.get('typeface')] += 1
        slides = []
        theme_faces=set()
        effective_requirements=Counter()
        requirement_examples={}
        for num, slide_id in enumerate(ids, 1):
            part = rels[slide_id.get(RID)]['target']
            tree = ET.fromstring(z.read(part))
            rr = relationships(z, part)
            def first_related(rels, kind):
                return next((r['target'] for r in rels.values() if r['type']==kind and not r['external'] and r['target'] in names),None)
            layout_part=first_related(rr,'slideLayout')
            master_part=first_related(relationships(z,layout_part),'slideMaster') if layout_part else None
            theme_part=first_related(relationships(z,master_part),'theme') if master_part else None
            theme_fonts={}
            if theme_part:
                theme=ET.fromstring(z.read(theme_part))
                for group,code in [('majorFont','mj'),('minorFont','mn')]:
                    for face,suffix in [('latin','lt'),('ea','ea'),('cs','cs')]:
                        font=theme.find('.//a:fontScheme/a:'+group+'/a:'+face,NS)
                        if font is not None and font.get('typeface'):
                            theme_fonts['+'+code+'-'+suffix]=font.get('typeface');theme_faces.add(font.get('typeface'))
            text_context=build_context(z,rr,lambda p:relationships(z,p),pres)
            slide_fonts=Counter()
            slide_examples={}
            for shape in tree.findall('.//p:sp',NS):
                ph=shape.find('./p:nvSpPr/p:nvPr/p:ph',NS)
                role=('title' if ph is not None and ph.get('type') in ('title','ctrTitle') else 'body' if ph is not None and ph.get('type') in ('body','subTitle') else 'text-object')
                nv=shape.find('./p:nvSpPr/p:cNvPr',NS)
                object_id=f's{num}-o{nv.get("id")}' if nv is not None and nv.get('id') else None
                for para in shape.findall('./p:txBody/a:p',NS):
                    pp=para.find('a:pPr',NS);level=int(pp.get('lvl','0')) if pp is not None else 0
                    chain=styles(text_context,shape,pp,level)
                    for run in para.findall('a:r',NS):
                        typography=resolve_run(chain,run.find('a:rPr',NS),text_context['themeTokens'])
                        prop=typography['properties'];face=prop.get('latin',{});size=prop.get('sizePt',{});bold=prop.get('bold',{});italic=prop.get('italic',{})
                        key=(face.get('family'),face.get('declared'),face.get('source'),size.get('value'),bold.get('value'),italic.get('value'))
                        slide_fonts[key]+=1;effective_requirements[key]+=1
                        example={'slide':num,'objectId':object_id,'role':role}
                        for mapping in (slide_examples,requirement_examples):
                            values=mapping.setdefault(key,[])
                            if example not in values and len(values)<4:values.append(example)
            strings = [e.text or '' for e in tree.findall('.//a:t', NS)]
            title_node = next((s for s in tree.findall('.//p:sp', NS) if any(ph.get('type') in ('title', 'ctrTitle') for ph in s.findall('.//p:ph', NS))), None)
            title = ' '.join(t.text or '' for t in title_node.findall('.//a:t', NS)) if title_node is not None else (strings[0] if strings else '')
            counts = Counter(local(e.tag) for e in tree.iter())
            assets = [r for r in rr.values() if r['type'] in ('image', 'video', 'media', 'audio')]
            video_ext = ('.mp4', '.mov', '.m4v', '.avi', '.wmv', '.webm', '.mpg', '.mpeg')
            videos = list({(r['target'], r['external']): r for r in assets if r['type'] == 'video' or Path(r['target'].lower()).suffix in video_ext}.values())
            vectors = [r['target'] for r in assets if Path(r['target'].lower()).suffix in ('.svg', '.emf', '.wmf')]
            svg_masks = []
            for name in vectors:
                if name.lower().endswith('.svg') and name in names:
                    data = z.read(name).lower()
                    if re.search(rb'<(?:[a-z0-9_-]+:)?(?:mask|clippath)\b', data):
                        svg_masks.append(name)
            timing = tree.find('p:timing', NS)
            events = sorted({e.get('evt') for e in timing.iter() if e.get('evt')}) if timing is not None else []
            bg = tree.find('p:cSld/p:bg', NS)
            colors = [e.get('val') for e in bg.findall('.//a:srgbClr', NS) if e.get('val')] if bg is not None else []
            slides.append({'number': num, 'id': slide_id.get('id'), 'part': part,
                'titleCandidate': title[:180], 'textCharacters': sum(len(s) for s in strings),
                'tables': counts['tbl'], 'charts': counts['chart'], 'groups': counts['grpSp'],
                'connectors': counts['cxnSp'], 'images': counts['pic'], 'vectorAssets': sorted(set(vectors)),
                'svgWithMaskOrClip': sorted(set(svg_masks)), 'cropElements': counts['srcRect'],
                'media': videos, 'timingPresent': timing is not None, 'timingEvents': events,
                'explicitBackgroundColors': colors, 'fontRequirements':font_records(slide_fonts,slide_examples), 'fontTheme':{'layoutPart':layout_part,'masterPart':master_part,'themePart':theme_part,'tokens':theme_fonts}, '_text': ' '.join(strings)})
        sequences = []
        for left, right in zip(slides, slides[1:]):
            a, b = left['_text'], right['_text']
            if min(len(a), len(b)) >= 40 and difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() >= .72:
                if sequences and sequences[-1][-1] == left['number']:
                    sequences[-1].append(right['number'])
                else:
                    sequences.append([left['number'], right['number']])
        for s in slides:
            del s['_text']
        return {'sourceType':'pptx', 'canvas':canvas, 'slideCount':len(slides), 'sections':sections,
                'fonts': {'explicitSlideFaces':dict(declared_faces), 'embedded':embedded_fonts,'themeFaceNames':sorted(theme_faces),'effectiveRequirements':font_records(effective_requirements,requirement_examples),
                          'limitations':['XML font declarations do not prove file availability or browser rendering.', 'Partial Latin run inheritance uses direct text, matching placeholder, master styles and theme tokens; unresolved styles and script-specific fonts require review.']},
                'slides':slides, 'possibleRevealSequences':sequences,
                'limitations':['Section titles and similar adjacent text are evidence, not confirmed navigation or reveal steps.',
                               'Background colors include explicit slide fills only; inherited fills and rendered appearance require visual review.',
                               'Media/timing co-occurrence does not establish their association or exact playback trigger.',
                               'SVG mask/clip detection covers embedded SVG only; other masks and effects require visual review.']}


def inspect_pdf(path):
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError('PDF preflight requires pypdf; use the bundled Python runtime or install pypdf.') from e
    try:
        reader = PdfReader(str(path))
    except Exception as e:
        raise ValueError('Cannot read PDF: ' + str(e)) from e
    if reader.is_encrypted and not reader.decrypt(''):
        raise ValueError('Encrypted PDF requires a readable, decrypted source.')
    try:
        import pypdfium2 as pdfium
        from PIL import Image  # pypdfium2's to_pil requires Pillow
        visual = pdfium.PdfDocument(str(path))
    except ImportError:
        visual = None
    pages = []
    for n, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ''
            extraction = 'ok'
        except Exception:
            text, extraction = '', 'failed'
        resources = page.get('/Resources') or {}
        if hasattr(resources, 'get_object'):
            resources = resources.get_object()
        xobjects = resources.get('/XObject') or {}
        if hasattr(xobjects, 'get_object'):
            xobjects = xobjects.get_object()
        image_count = sum(1 for obj in xobjects.values() if obj.get_object().get('/Subtype') == '/Image')
        chars = len(''.join(text.split()))
        kind = 'text-and-image' if chars >= 20 and image_count else 'text-present' if chars >= 20 else 'sparse-text-or-image' if chars else 'no-extractable-text'
        tone = 'not-assessed'
        if visual is not None:
            pdf_page = visual[n - 1]
            bitmap = pdf_page.render(scale=0.08)
            image = bitmap.to_pil().convert('RGB')
            pixels = list(image.get_flattened_data() if hasattr(image, 'get_flattened_data') else image.getdata())
            luminance = sum((0.2126*r + 0.7152*g + 0.0722*b) for r,g,b in pixels) / max(len(pixels), 1)
            tone = 'dark' if luminance < 85 else 'light' if luminance > 170 else 'mixed'
            bitmap.close()
            pdf_page.close()
        pages.append({'number': n, 'renderedToneCandidate':tone, 'widthPt': float(page.mediabox.width), 'heightPt': float(page.mediabox.height),
                      'extractableCharacters': chars, 'textExtraction': extraction,
                      'topLevelImageObjects': image_count, 'typeCandidate': kind})
    if visual is not None:
        visual.close()
    return {'sourceType':'pdf', 'slideCount':len(pages), 'slides':pages, 'sections':[],
            'limitations':['Page type is a heuristic, not OCR or visual verification; nested images, vector outlines and OCR layers may be misclassified.',
                           'Rendered tone is a low-resolution luminance heuristic, not a palette analysis; visually inspect examples.',
                           'PDF alone does not establish whether a blank or dark page contained video, animation or triggers.',
                           'Production conversion from PDF is not implemented by the Maker pipeline.']}


def question(key, prompt, default, examples=None):
    return {'key':key, 'question':prompt, 'recommendedDefault':default, 'exampleSlides':examples or []}


def build_report(paths, decisions):
    sources = []
    for path in paths:
        if not path.is_file():
            raise ValueError('Source not found: ' + str(path))
        kind = path.suffix.lower()
        if kind not in ('.pptx', '.pdf'):
            raise ValueError('Unsupported source: ' + str(path))
        source = inspect_pptx(path) if kind == '.pptx' else inspect_pdf(path)
        source.update(path=str(path.resolve()), name=path.name, sha256=digest(path))
        sources.append(source)
    pptx = [s for s in sources if s['sourceType'] == 'pptx']
    pdf = [s for s in sources if s['sourceType'] == 'pdf']
    pair = len(pptx) == len(pdf) == 1 and Path(pptx[0]['name']).stem.casefold() == Path(pdf[0]['name']).stem.casefold() and pptx[0]['slideCount'] == pdf[0]['slideCount']
    roles = ([{'path':pptx[0]['path'], 'proposedRole':'primary source'}, {'path':pdf[0]['path'], 'proposedRole':'visual reference'}] if pair else
             [{'path':s['path'], 'proposedRole':'primary source' if len(sources) == 1 else 'undetermined'} for s in sources])
    if 'sourceRoles' in decisions and not isinstance(decisions['sourceRoles'], dict):
        raise ValueError('sourceRoles must map every supplied filename or absolute path to its role.')
    if 'sourceRoles' in decisions:
        roles = [{'path':s['path'], 'explicitRole':decisions['sourceRoles'].get(s['path'], decisions['sourceRoles'].get(s['name'], 'unspecified'))} for s in sources] if isinstance(decisions['sourceRoles'], dict) else roles
    role_values = [(r, r.get('explicitRole', r.get('proposedRole', ''))) for r in roles]
    primary_roles = [r for r, value in role_values if isinstance(value, str) and value.strip().casefold() in ('primary source', 'primary content')]
    canonical_roles = all(isinstance(value, str) and value.strip().casefold() in ('primary source', 'primary content', 'visual reference') for _, value in role_values)
    primary = next((s for s in sources if len(primary_roles) == 1 and s['path'] == primary_roles[0]['path']), None) if canonical_roles else None
    unresolved = []
    def add(key, prompt, default, examples=None, condition=True):
        if condition and key not in decisions:
            unresolved.append(question(key, prompt, default, examples))
    # Multiple unrelated files can be inventoried, but their roles must be resolved before conversion.
    if isinstance(decisions.get('sourceRoles'), dict) and any(r.get('explicitRole') == 'unspecified' for r in roles):
        raise ValueError('sourceRoles must name every supplied file or be omitted.')
    add('sourceRoles', 'Какую роль играет каждый файл и какой источник главный?', 'Для пары одинакового имени и числа страниц: PPTX — основной, PDF — визуальная сверка.', condition=len(sources) > 1 and not pair)
    pdf_primary = primary is not None and primary['sourceType'] == 'pdf'
    sparse = [s['number'] for s in primary['slides'] if s['typeCandidate'] in ('sparse-text-or-image','no-extractable-text') or s['textExtraction'] != 'ok'] if pdf_primary else []
    pdf_question = ('Пришли план новой презентации или исходный PPTX для этого PDF.' if pptx else 'Можешь приложить исходный PPTX? Если его нет, пришли план презентации: основные тезисы по слайдам.')
    add('pdfEditableSource', pdf_question, 'PPTX для сохранения исходника; план для новой презентации. PDF можно использовать для визуальной сверки.', sparse[:8], pdf_primary)
    tones = [(s['number'], s['renderedToneCandidate']) for p in pdf for s in p['slides']]
    mixed_themes = any(t == 'light' for _,t in tones) and any(t == 'dark' for _,t in tones)
    counts = Counter(t for _,t in tones if t in ('light', 'dark'))
    dominant = counts.most_common()
    proposed_theme = (dominant[0][0] + ' shell; preserve source slide palette') if dominant and (len(dominant) == 1 or dominant[0][1] > dominant[1][1]) else 'one theme based on visually reviewed dominant content; preserve source slide palette'

    add('shellTheme', 'Какую тему оболочки выбрать для смешанных светлых и тёмных страниц: светлую или тёмную?', proposed_theme, [next(n for n,t in tones if t == 'light'), next(n for n,t in tones if t == 'dark')] if mixed_themes else [], mixed_themes and not pdf_primary)
    sequences = [seq for p in pptx for seq in p['possibleRevealSequences']]
    media = [s for p in pptx for s in p['slides'] if s['media']]
    complex_slides = [s['number'] for p in pptx for s in p['slides'] if s['svgWithMaskOrClip'] or s['connectors'] or s['tables']]
    add('fallbackPriority', 'Для сложных объектов что важнее: точный вид с фолбэком или полная редактируемость с риском расхождения?', 'Сохранить вид сложных зон и оставлять текст редактируемым там, где это надёжно.', complex_slides[:8], bool(complex_slides) and primary is not None and primary['sourceType'] == 'pptx' and decisions.get('editability') in ('all', 'strict', 'полная'))
    examples = []
    def sample(number, reason):
        existing = next((e for e in examples if e['slide'] == number), None)
        if existing:
            existing['reason'] += '; ' + reason
        else:
            examples.append({'slide':number, 'reason':reason})
    if primary and primary['slideCount']:
        sample(1, 'cover')
    if primary and primary['sourceType'] == 'pptx':
        slides = primary['slides']
        if slides:
            sample(max(slides, key=lambda s:s['textCharacters'])['number'], 'most text characters')
            for field, reason in (
                (lambda s: s['vectorAssets'] or s['svgWithMaskOrClip'] or s['connectors'], 'vector, mask or connector'),
                (lambda s: s['tables'], 'table'),
                (lambda s: s['media'], 'video')):
                candidates = [s for s in slides if field(s)]
                if candidates:
                    candidate = next((s for s in candidates if not any(e['slide'] == s['number'] for e in examples)), candidates[0])
                    sample(candidate['number'], reason)
    elif primary and primary['sourceType'] == 'pdf':
        pages = primary['slides']
        difficult = next((s for s in pages if s['textExtraction'] != 'ok' or s['extractableCharacters'] == 0), None)
        if difficult is None:
            difficult = next((s for s in pages if s['typeCandidate'] == 'sparse-text-or-image'), None)
        if difficult:
            sample(difficult['number'], 'no or little extractable text')
    return {'schemaVersion':1, 'sources':sources, 'sourceRoles':roles,
            'pairing':{'proposed':pair, 'basis':'same filename stem and page count' if pair else None,
                       'contentEquivalenceVerified':False},
            'brief':{'explicitDecisions':decisions, 'recommendedDefaults':{k:v for k,v in dict({'mode':'for tidy / presentation-ready requests: preserve strong compositions, adapt near-ready ones and redesign weak structures; follow explicit preservation requests; retain wording, facts, order and count', 'reveals':'preserve source steps and order', 'outputs':'offline HTML and editable project', 'slidePalette':'preserve source colors', 'shellTheme':proposed_theme}, **{q['key']:q['recommendedDefault'] for q in unresolved}).items() if k not in decisions},
                     'productionInput': ({'path':primary['path'], 'roleBasis':'explicit' if 'sourceRoles' in decisions else 'proposed'} if primary and not pdf_primary else None),
                     'productionRoute': ('request-pptx-or-outline' if pdf_primary else 'pptx' if primary else 'resolve-source-roles'), 'reviewSamples':examples, 'reviewSampleSource': (primary['path'] if primary else None), 'mediaTriggerReview': [{'source': p['path'], 'slides': [s['number'] for s in p['slides'] if s['media']]} for p in pptx if any(s['media'] for s in p['slides'])], 'pdfProductionStatus':'not implemented in Maker; do not imply PDF-to-HTML production support',
                     'pendingQuestions':unresolved},
            'notes':['Questions are recommendations to the agent; reconcile them against the complete user request before asking.',
                     'Slide candidates are heuristics. Visual inspection and human decisions are not replaced by this report.']}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('sources', nargs='+', type=Path, metavar='SOURCE')
    ap.add_argument('--decisions', type=Path, help='JSON object of already explicit decisions')
    ap.add_argument('--output', type=Path, help='write JSON report; default stdout')
    ap.add_argument('--thumbnails', type=Path, help='new directory for PDF review-page PNGs (requires pypdfium2)')
    ap.add_argument('--local-fonts', action='store_true', help='inspect local installed font metadata on macOS')
    args = ap.parse_args()
    try:
        decisions = json.loads(args.decisions.read_text(encoding='utf-8')) if args.decisions else {}
        if not isinstance(decisions, dict) or any(v is None for v in decisions.values()):
            raise ValueError('Decisions must be a JSON object with non-null values.')
        if args.output:
            output = args.output.resolve()
            protected = [p.resolve() for p in args.sources] + ([args.decisions.resolve()] if args.decisions else [])
            if output in protected:
                raise ValueError('Output must not overwrite an input file.')
            if output.exists():
                raise ValueError('Output already exists; choose a new path.')
        report = build_report(args.sources, decisions)
        if args.local_fonts:
            report['localFontDiscovery'] = local_font_matches(report['sources'])
        if args.thumbnails:
            try:
                import pypdfium2 as pdfium
                from PIL import Image
            except ImportError as e:
                raise RuntimeError('Thumbnails require pypdfium2 and Pillow.') from e
            if args.thumbnails.exists():
                raise ValueError('Thumbnail directory already exists; choose a new path.')
            args.thumbnails.mkdir(parents=True)
            selected = {sample['slide'] for sample in report['brief']['reviewSamples']}
            selected.update(n for q in report['brief']['pendingQuestions'] for n in q['exampleSlides'])
            for index, source in enumerate(report['sources'], 1):
                if source['sourceType'] != 'pdf':
                    continue
                doc = pdfium.PdfDocument(source['path'])
                rendered = []
                for number in sorted(selected):
                    if not 1 <= number <= len(doc):
                        continue
                    page = doc[number - 1]
                    bitmap = page.render(scale=0.5)
                    dest = args.thumbnails / f'source-{index}-page-{number:03}.png'
                    bitmap.to_pil().save(dest)
                    bitmap.close()
                    page.close()
                    rendered.append({'slide':number, 'path':str(dest.resolve())})
                doc.close()
                source['reviewThumbnails'] = rendered
        data = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            output = args.output.resolve()
            protected = [p.resolve() for p in args.sources] + ([args.decisions.resolve()] if args.decisions else [])
            if output in protected:
                raise ValueError('Output must not overwrite an input file.')
            if output.exists():
                raise ValueError('Output already exists; choose a new path.')
            with output.open('x', encoding='utf-8') as f:
                f.write(data)
        else:
            sys.stdout.write(data)
    except (OSError, ValueError, KeyError, ET.ParseError, RuntimeError, BadZipFile) as e:
        print('preflight: ' + str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
