"""Classify only a narrow video-only timing tree for a reviewed static frame.

No claim about interactive PowerPoint behavior or other timing dialects.
"""
from source_dispositions import NS

P='{%s}'%NS['p']
def need(ok,msg):
    if not ok: raise ValueError('static timing unresolved: '+msg)

# Strict structural allowlist: unfamiliar tags, children and attributes fail.
GRAMMAR={
 'timing':(set(),{('tnLst',)}),'tnLst':(set(),{('par',)}),'par':(set(),{('cTn',)}),
 'cTn':({'id','dur','restart','nodeType','fill','presetID','presetClass','presetSubtype','evtFilter','repeatCount','display'}, {('stCondLst','childTnLst'),('childTnLst',),('stCondLst','endSync','childTnLst'),('stCondLst',),()}),
 'childTnLst':(set(),{('seq','video'),('seq','video','seq'),('seq','seq','video'),('par',),('cmd',)}),
 'seq':({'concurrent','nextAc'},{('cTn','nextCondLst'),('cTn','prevCondLst','nextCondLst')}),
 'stCondLst':(set(),{('cond',),('cond','cond')}),'cond':({'evt','delay'},{(),('tgtEl',),('tn',)}),
 'tn':({'val'},{()}),'cmd':({'type','cmd'},{('cBhvr',)}),'cBhvr':(set(),{('cTn','tgtEl')}),
 'tgtEl':(set(),{('spTgt',),('sldTgt',)}),'spTgt':({'spid'},{()}),
 'prevCondLst':(set(),{('cond',)}),'nextCondLst':(set(),{('cond',)}),'sldTgt':(set(),{()}),
 'endSync':({'evt','delay'},{('rtn',)}),'rtn':({'val'},{()}),'video':(set(),{('cMediaNode',)}),
 'cMediaNode':({'vol','mute'},{('cTn','tgtEl')})}

def classify(tree, target_id, allow_transition=False):
    transition=tree.find('p:transition',NS)
    if transition is not None:
        need(allow_transition and set(transition.attrib)<= {'spd'} and transition.get('spd') in (None,'slow','med','fast') and len(transition)==1 and transition[0].tag==P+'wipe' and not transition[0].attrib and len(transition[0])==0,'transition is not reviewed simple wipe')
    timing=tree.find('p:timing',NS)
    need(timing is not None,'no supported video timing')
    ids=set(); refs=[]; shape_targets=[]; parents={c:p for p in timing.iter() for c in p}
    for x in timing.iter():
        need(x.tag.startswith(P),'foreign timing namespace')
        name=x.tag[len(P):];need(name in GRAMMAR,'unknown timing element '+name)
        attrs,children=GRAMMAR[name];need(set(x.attrib)<=attrs and tuple(c.tag[len(P):] if c.tag.startswith(P) else '?' for c in x) in children,'unsupported '+name+' structure')
        if name=='cTn':
            ident=x.get('id');need(ident and ident.isdigit() and ident not in ids,'missing/duplicate time node ID');ids.add(ident)
            for k in ('dur','repeatCount'):
                v=x.get(k);need(v is None or v=='indefinite' or v.isdigit(),'unknown '+k)
            for k,allowed in {'nodeType':{'tmRoot','mainSeq','afterEffect','withEffect','interactiveSeq','clickEffect'},'presetClass':{'mediacall'},'presetID':{'1','2'},'presetSubtype':{'0'},'fill':{'hold'},'restart':{'never','whenNotActive'},'evtFilter':{'cancelBubble'},'display':{'0'}}.items():
                need(x.get(k) is None or x.get(k) in allowed,'unsupported '+k)
        elif name=='tn':refs.append(x.get('val'))
        elif name=='spTgt':shape_targets.append(x.get('spid'))
        elif name=='sldTgt':
            tgt=parents.get(x);cond=parents.get(tgt);container=parents.get(cond)
            need(tgt is not None and cond is not None and container is not None and cond.tag==P+'cond' and container.tag in (P+'prevCondLst',P+'nextCondLst') and cond.get('evt') in ('onPrev','onNext'),'slide target outside navigation condition')
        elif name=='cmd':need(x.get('type')=='call' and x.get('cmd') in ('playFrom(0.0)','togglePause'),'unsupported command')
        elif name=='seq':need(x.get('concurrent')=='1' and x.get('nextAc')=='seek','unsupported sequence')
        elif name=='cond':need(x.get('evt') in (None,'onBegin','onClick','onPrev','onNext') and (x.get('delay') in (None,'indefinite') or x.get('delay','').isdigit()),'unsupported condition')
        elif name=='endSync':need(x.get('evt')=='end' and x.get('delay')=='0','unsupported end sync')
        elif name=='rtn':need(x.get('val')=='all','unsupported runtime node')
        elif name=='cMediaNode':need(set(x.attrib)<= {'mute','vol'} and x.get('mute') in (None,'0','1') and (x.get('vol') is None or x.get('vol').isdigit()),'unsupported media options')
    need(all(r in ids for r in refs),'dangling timing dependency')
    need(shape_targets and len(set(shape_targets))==1 and str(target_id) not in shape_targets,'other or reviewed shape timing target')
    video_id=shape_targets[0];pictures=tree.findall('p:cSld/p:spTree/p:pic',NS)
    matches=[p for p in pictures if p.find('p:nvPicPr/p:cNvPr',NS) is not None and p.find('p:nvPicPr/p:cNvPr',NS).get('id')==video_id and p.find('p:nvPicPr/p:nvPr/a:videoFile',NS) is not None]
    need(len(matches)==1 and len(timing.findall('.//p:video',NS))==1 and timing.findall('.//p:cmd',NS),'target is not exactly one direct video')
    return {'kind':'video-only-static-frame','videoTargetId':video_id,'commands':[x.get('cmd') for x in timing.findall('.//p:cmd',NS)],'timeNodeReferences':refs,'transition':'wipe' if transition is not None else None,'limitation':'No interactive animation transfer or intermediate transition state is verified.'}
