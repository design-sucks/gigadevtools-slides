"""Verify manually reviewed, explicitly transparent PPTX runs; no inheritance inference."""
import argparse, json, re, posixpath
from pathlib import Path
from xml.etree import ElementTree as ET
from source_dispositions import A, NS, SourceVerifier, file_digest
from source_shape import appearance
from source_static_timing import classify as classify_static_timing
from source_gradient_svg import resolve as resolve_gradient, render_svg


def require(condition, message):
    if not condition:
        raise ValueError(message)



def inherited_text_style(verifier, slide_part):
    """Inspect the non-placeholder defaults; missing or ambiguous relations stay unresolved."""
    def related(part, suffix):
        relpath=posixpath.join(posixpath.dirname(part),'_rels',posixpath.basename(part)+'.rels')
        root=ET.fromstring(verifier.zip.read(relpath))
        matches=[x for x in root if x.get('Type','').endswith('/'+suffix) and x.get('TargetMode')!='External']
        require(len(matches)==1,'text style inheritance relationship unresolved: '+suffix)
        target=matches[0].get('Target','')
        return target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(part),target))
    layout=related(slide_part,'slideLayout');master=related(layout,'slideMaster')
    root=ET.fromstring(verifier.zip.read(master))
    styles=[verifier.presentation.find('p:defaultTextStyle',NS),root.find('p:txStyles/p:otherStyle',NS)]
    require(all(x is not None for x in styles),'inherited non-placeholder text styles unresolved')
    forbidden={'ln','effectLst','effectDag','scene3d','sp3d','highlight','uFill','uFillTx','uLn','uLnTx'}
    for style in styles:
        for node in style.iter():
            require(node.tag.rsplit('}',1)[-1] not in forbidden,'inherited outline/effect/highlight unresolved')
            require(node.get('u','none')=='none' and node.get('strike','noStrike')=='noStrike','inherited underline/strike unresolved')


def verify(source, inventory, project, manifest_path):
    manifest=json.loads(manifest_path.read_text())
    sha=inventory.get('source',{}).get('sha256')
    require(source is not None and file_digest(source)==sha, 'original PPTX hash mismatch or unavailable')
    require(manifest.get('sourceSha256')==sha and project.get('source',{}).get('sha256')==sha, 'manifest/project source hash mismatch')
    entries=manifest.get('dispositions')
    require(isinstance(entries,list) and entries, 'nonempty dispositions list required')
    verifier=SourceVerifier(source); results=[]; seen=set()
    try:
        for entry in entries:
            n=entry.get('slide'); sid=entry.get('sourceId'); pi=entry.get('paragraphIndex'); ri=entry.get('runIndex')
            key=(n,sid,pi,ri)
            require(type(n) is int and isinstance(sid,str) and type(pi) is int and pi>=0 and type(ri) is int and ri>=0 and key not in seen,'invalid or duplicate run identity')
            seen.add(key)
            require(entry.get('reviewed') is True and entry.get('disposition')=='preserve-transparent' and isinstance(entry.get('reason'),str) and entry['reason'].strip(),'reviewed preserve-transparent disposition and reason required')
            slides=[s for s in inventory.get('slides',[]) if s.get('sourceNumber')==n]
            require(len(slides)==1,'source slide missing or ambiguous'); slide=slides[0]
            blocks=[b for b in slide.get('blocks',[]) if b.get('id')==sid]
            require(len(blocks)==1 and blocks[0].get('kind')=='text','source text block missing or ambiguous'); block=blocks[0]
            dest=[s for s in project.get('slides',[]) if s.get('id')==slide.get('id') and s.get('sourceNumber')==n]
            require(len(dest)==1 and [b for b in dest[0].get('blocks',[]) if b.get('id')==sid]==[block], 'project source block or mapping differs')
            src=block.get('source') or {}; oid=src.get('objectId')
            require(isinstance(oid,str) and sid==f's{n}-o{oid}' and src.get('slide')==n and block.get('group') is None,'source identity/group unresolved')
            part,shape=verifier.shape(n,oid)
            require(part==src.get('part')==entry.get('sourcePart'),'source XML part mismatch')
            tree=verifier.cache[part]
            static_review=entry.get('staticReview');timing_proof=None
            if tree.find('p:timing',NS) is not None or tree.find('p:transition',NS) is not None:
                require(isinstance(static_review,dict) and static_review.get('reviewed') is True and static_review.get('mode')=='static-frame-after-transition' and static_review.get('systemColorPolicy')=='lastClr' and static_review.get('animationNotVerified') is True and isinstance(static_review.get('reason'),str) and static_review['reason'].strip() and isinstance(entry.get('shapeReview'),dict),'explicit static-frame lastClr review and separate shape review required')
                timing_proof=classify_static_timing(tree,oid,allow_transition=True)
            inherited_text_style(verifier,part)
            shape_proof=None
            complex_shape=shape.find('p:style',NS) is not None or bool(shape.findall('p:spPr/a:ln',NS))
            if complex_shape and isinstance(entry.get('shapeReview'),dict):
                review=entry['shapeReview']
                require(review.get('reviewed') is True and review.get('targetId')==sid and isinstance(review.get('reason'),str) and review['reason'].strip(),'specific reviewed source shape mapping required')
                cr=review.get('candidateRender');ch=review.get('candidateRenderSha256');html_hash=review.get('htmlSha256')
                require(isinstance(cr,str) and re.fullmatch(r'[0-9a-f]{64}',str(ch or '')) and re.fullmatch(r'[0-9a-f]{64}',str(html_hash or '')),'candidate render and HTML hashes required for source shape')
                cp=(manifest_path.parent/cr).resolve();require(cp.is_file() and file_digest(cp)==ch,'candidate render missing or hash mismatch')
                if review.get('kind')=='source-gradient-svg-v1':
                    require(timing_proof is None,'gradient static timing combination unsupported')
                    gradient=resolve_gradient(verifier,n,oid)
                    shape_proof={'kind':'source-gradient-svg-v1','sourceGradient':gradient.to_dict(),'expectedSvg':render_svg(gradient),'htmlSha256':html_hash,'candidateRender':str(cp),'candidateRenderSha256':ch,'reason':review['reason']}
                else:
                    require(review.get('kind') in (None,'solid-shape-v1'),'unknown shape review kind')
                    shape_proof={'sourceAppearance':appearance(verifier,part,shape,system_color_policy='lastClr' if timing_proof else None),'htmlSha256':html_hash,'candidateRender':str(cp),'candidateRenderSha256':ch,'reason':review['reason']}
                require(not any(shape.findall('p:txBody//a:'+x,NS) for x in ('ln','effectLst','effectDag','scene3d','sp3d','highlight','uFill','uFillTx','uLn','uLnTx')),'text outline or effect unresolved')
            else:
                require(shape.find('p:style',NS) is None and shape.find('p:nvSpPr/p:nvPr/p:ph',NS) is None,'shape style/placeholder inheritance unresolved')
                require(not any(shape.findall('.//a:'+x,NS) for x in ('ln','effectLst','effectDag','scene3d','sp3d','highlight','uFill','uFillTx','uLn','uLnTx')),'shape/text outline or effect unresolved')
            require(not any(x.get('u','none')!='none' or x.get('strike','noStrike')!='noStrike' for x in shape.iter()),'shape underline/strike unresolved')
            paragraphs=block.get('paragraphs',[]); xml_paras=shape.findall('p:txBody/a:p',NS)
            # Exact paragraph and run stream; do not infer fields, line breaks or inherited runs.
            require(len(xml_paras)==len(paragraphs),'paragraph stream differs from original')
            source_runs=[]
            for paragraph,xp in zip(paragraphs,xml_paras):
                xr=[x for x in xp if x.tag in (f'{{{A}}}r',f'{{{A}}}fld',f'{{{A}}}br')]
                runs=paragraph.get('runs',[])
                require(len(xr)==len(runs),'run stream differs from original')
                texts=[('\n' if x.tag==f'{{{A}}}br' else (x.findtext('a:t',default='',namespaces=NS))) for x in xr]
                require(texts==[r.get('text','') for r in runs] and paragraph.get('text','')==''.join(texts),'run text/order differs from original')
                source_runs.append(xr)
            require(pi<len(source_runs) and ri<len(source_runs[pi]),'run index outside source')
            run=source_runs[pi][ri]; text=paragraphs[pi]['runs'][ri].get('text')
            require(run.tag==f'{{{A}}}r' and isinstance(text,str) and text and entry.get('sourceText')==text,'run type or text differs')
            fill=run.find('a:rPr/a:solidFill',NS)
            require(fill is not None and len(fill)==1 and fill[0].tag in [f'{{{A}}}{x}' for x in ('schemeClr','srgbClr','prstClr','sysClr','scrgbClr','hslClr')],'run has no explicit supported solid fill')
            alphas=[x for x in fill[0] if x.tag==f'{{{A}}}alpha']
            require(len(alphas)==1 and alphas[0].get('val')=='0' and not any(x.tag in (f'{{{A}}}alphaMod',f'{{{A}}}alphaOff') for x in fill[0]),'run is not explicitly alpha=0')
            require(not any(run.findall('.//a:'+x,NS) for x in ('ln','effectLst','effectDag','scene3d','sp3d')),'run outline/effect unresolved')
            render=entry.get('sourceRender'); rh=entry.get('sourceRenderSha256')
            require(isinstance(render,str) and re.fullmatch(r'[0-9a-f]{64}',str(rh or '')) is not None,'source render and SHA-256 required')
            rp=(manifest_path.parent/render).resolve();require(rp.is_file() and file_digest(rp)==rh,'source render missing or hash mismatch')
            observation={'code':'source-alpha-reviewed','slide':n,'slideId':slide.get('id'),'sourceId':sid,'sourcePart':part,'paragraphIndex':pi,'runIndex':ri,'sourceText':text,'reason':entry['reason'],'sourceRender':str(rp),'sourceRenderSha256':rh,'mapping':{'disposition':'preserve-transparent','targetId':sid},'review':'Only direct fill and checked non-placeholder default text styles are established; human must verify rendering, provenance and subsequent reveal state.'}
            if timing_proof:observation['staticReview']={'contract':static_review,'timing':timing_proof,'limitation':'Static fallback only; OS system color and animation are not verified.'}
            if shape_proof:observation['code']='source-alpha-shape-conditional';observation['shapeProof']=shape_proof;observation['review']='Conditional: source shape properties resolved; exact HTML DOM shape and both render reviews still required.'
            results.append(observation)
    finally:
        verifier.close()
    return results


def main():
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('inventory',type=Path);p.add_argument('project',type=Path);p.add_argument('manifest',type=Path);a=p.parse_args()
    try:
        entries=verify(a.source,json.loads(a.inventory.read_text()),json.loads(a.project.read_text()),a.manifest.resolve())
        print(json.dumps({'status':'review','manifestSha256':file_digest(a.manifest),'observations':entries},ensure_ascii=False))
    except (ValueError, OSError, KeyError, ET.ParseError, IndexError) as e:
        print(json.dumps({'status':'fail','error':str(e)},ensure_ascii=False));return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
