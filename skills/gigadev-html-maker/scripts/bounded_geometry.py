#!/usr/bin/env python3
"""Guarded translation of sibling authored HTML elements after text reconciliation."""
import argparse, hashlib, json, math, os, pathlib, re, subprocess, tempfile
from html.parser import HTMLParser

class Scan(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=False); self.html=html; self.stack=[]; self.found=[]; self.line_offsets=[0]
        for m in re.finditer('\n', html): self.line_offsets.append(m.end())
    def handle_starttag(self, tag, attrs):
        pos=self.line_offsets[self.getpos()[0]-1]+self.getpos()[1]; raw=self.get_starttag_text(); attr=dict(attrs)
        if attr.get('data-source-id'): self.found.append((attr['data-source-id'],tag,attr,tuple(self.stack),pos,raw))
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}: self.stack.append((tag,pos,attr))
    def handle_startendtag(self,tag,attrs): self.handle_starttag(tag,attrs); self.handle_endtag(tag)
    def handle_endtag(self,tag):
        if self.stack and self.stack[-1][0]==tag: self.stack.pop()

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def fail(s): raise ValueError(s)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('project');p.add_argument('baseline');p.add_argument('saved');p.add_argument('spec');p.add_argument('out');a=p.parse_args()
    spec=json.loads(pathlib.Path(a.spec).read_text()); project=pathlib.Path(a.project).resolve(); out=pathlib.Path(a.out).resolve()
    if out.parent!=project.parent or out.exists(): fail('Output must be new and beside project')
    required={'projectSha256','baselineSha256','savedSha256','slide','problem','targets','dx','dy'}
    if not required <= set(spec) or set(spec)-required-{'widths','relations'}: fail('Unsupported or missing spec fields')
    if any(sha(f)!=spec[k] for f,k in [(project,'projectSha256'),(a.baseline,'baselineSha256'),(a.saved,'savedSha256')]): fail('Stale input hash')
    ids=spec['targets']; dx=spec['dx'];dy=spec['dy']
    if not isinstance(spec['problem'],str) or not spec['problem'].strip() or not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)) or not all(isinstance(x,str) and re.fullmatch(r'[A-Za-z0-9_-]+',x) for x in ids): fail('Invalid targets or problem')
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or abs(x)>1920 for x in (dx,dy)): fail('Unsupported displacement')
    widths=spec.get('widths',{}); relations=spec.get('relations',[])
    if not isinstance(widths,dict) or any(k not in ids or isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<v<=1920 for k,v in widths.items()): fail('Invalid requested width')
    if not isinstance(relations,list) or any(not isinstance(r,list) or len(r)!=2 or r[0]==r[1] or any(x not in ids for x in r) for r in relations): fail('Relations must name two selected targets')
    if any(x in widths for r in relations for x in r): fail('Resizing a linked target is unsupported')
    fd,tmp=tempfile.mkstemp(prefix='.geometry-reconcile-',suffix='.json',dir=project.parent);os.close(fd);os.unlink(tmp)
    try:
        cmd=['node',str(pathlib.Path(__file__).with_name('reconcile_edits.mjs')),str(pathlib.Path(a.baseline).resolve()),str(pathlib.Path(a.saved).resolve()),str(project),tmp]
        result=subprocess.run(cmd,capture_output=True,text=True)
        if result.returncode: fail('Reconciliation failed: '+result.stdout[-4000:]+result.stderr[-2000:])
        probe=subprocess.run(['node',str(pathlib.Path(__file__).with_name('check_geometry_context.mjs')),str(pathlib.Path(a.saved).resolve()),spec['slide'],*ids],capture_output=True,text=True)
        if probe.returncode: fail('Rendered coordinate context rejected: '+probe.stderr[-2000:])
        data=json.loads(pathlib.Path(tmp).read_text()); slides=[s for s in data['slides'] if s['id']==spec['slide']]
        if len(slides)!=1 or not isinstance(slides[0].get('html'),str): fail('Slide missing, ambiguous or not authored HTML')
        slide=slides[0]; source=slide['html']; scan=Scan(source);scan.feed(source)
        selected=[]
        for ident in ids:
            hits=[x for x in scan.found if x[0]==ident]
            if len(hits)!=1: fail('Missing or ambiguous target: '+ident)
            selected.append(hits[0])
        parents=[tuple((tag,pos) for tag,pos,_ in x[3]) for x in selected]
        if not parents[0] or any(x!=parents[0] for x in parents): fail('Targets must share one authored parent')
        # No transformed or SVG coordinate contexts: the translation is in parent CSS pixels.
        for x in selected:
            if x[1] not in {'div','p','img','table'} or any(tag in {'svg','foreignobject'} or re.search(r'(?:^|;)\s*(?:transform|translate|rotate|scale|zoom)\s*:',attr.get('style',''),re.I) for tag,_,attr in x[3]): fail('Unsupported coordinate context')
        edits=[];changes=[]
        for ident,tag,attr,stack,pos,raw in selected:
            style=attr.get('style',''); pieces=style.split(';'); props={}
            for item in pieces:
                if ':' in item:
                    k,v=item.split(':',1); k=k.strip().lower();props.setdefault(k,[]).append(v.strip())
            if props.get('position')!=['absolute'] or any(k in props for k in ('transform','translate','rotate','scale','zoom','right','bottom','inset')): fail('Unsupported positioned target: '+ident)
            before={};after={}
            for k,delta in [('left',dx),('top',dy)]:
                vals=props.get(k,[])
                if len(vals)!=1 or not re.fullmatch(r'-?(?:\d+(?:\.\d*)?|\.\d+)px',vals[0]): fail('Expected explicit pixel '+k+' on '+ident)
                before[k]=float(vals[0][:-2]);after[k]=round(before[k]+delta,6)
            if ident in widths:
                vals=props.get('width',[])
                if len(vals)!=1 or not re.fullmatch(r'(?:\d+(?:\.\d*)?|\.\d+)px',vals[0]): fail('Expected explicit pixel width on '+ident)
                before['width']=float(vals[0][:-2]);after['width']=widths[ident]
            def replace_prop(m):
                k=m.group(1).lower();return m.group(1)+m.group(2)+format(after[k],'.6f').rstrip('0').rstrip('.')+'px' if k in after else m.group(0)
            newstyle=re.sub(r'(?i)([a-z-]+)(\s*:\s*)([^;]*)',replace_prop,style)
            # Require quoted style and preserve all other bytes, including inline text.
            sm=re.search(r'\bstyle\s*=\s*(["\'])(.*?)\1',raw,re.S|re.I)
            if not sm or sm.group(2)!=style: fail('Unsupported style encoding')
            newraw=raw[:sm.start(2)]+newstyle+raw[sm.end(2):];edits.append((pos,pos+len(raw),newraw));changes.append({'sourceId':ident,'before':before,'after':after})
        for start,end,raw in sorted(edits,reverse=True): source=source[:start]+raw+source[end:]
        slide['html']=source
        payload=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
        if any(sha(f)!=spec[k] for f,k in [(project,'projectSha256'),(a.baseline,'baselineSha256'),(a.saved,'savedSha256')]): fail('Input changed during operation')
        fd,staged=tempfile.mkstemp(prefix='.geometry-output-',suffix='.tmp',dir=project.parent)
        try:
            with os.fdopen(fd,'wb') as f:
                f.write(payload);f.flush();os.fsync(f.fileno())
            os.link(staged,out) # atomic create; refuses existing destination
        finally:
            os.unlink(staged)
        by_id={c['sourceId']:c for c in changes}; measured=[]
        for first,second in relations:
            a,b=by_id[first],by_id[second]
            offset=lambda state: {k:round(b[state][k]-a[state][k],6) for k in ('left','top')}
            measured.append({'targets':[first,second],'beforeOffset':offset('before'),'afterOffset':offset('after')})
        print(json.dumps({'status':'applied','problem':spec['problem'],'slide':spec['slide'],'projectBefore':spec['projectSha256'],'baseline':spec['baselineSha256'],'saved':spec['savedSha256'],'projectAfter':hashlib.sha256(payload).hexdigest(),'changes':changes,'relations':measured,'coordinateSystem':'shared authored parent, CSS pixels','reconciliation':json.loads(result.stdout)},ensure_ascii=False,indent=2))
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
if __name__=='__main__':
    try: main()
    except Exception as e:
        import sys
        print(json.dumps({'status':'refused','reason':str(e)},ensure_ascii=False),file=sys.stderr);sys.exit(1)
