"""Targeted real-source and negative tests: python3 test_static_timing.py source.pptx."""
import copy, pathlib, sys
from xml.etree import ElementTree as E
from source_dispositions import NS, SourceVerifier
from source_shape import appearance
from source_static_timing import classify, P

v=SourceVerifier(pathlib.Path(sys.argv[1]));cases={24:['46'],25:['3','5'],26:['4','5','7'],27:['3','5','6'],29:['21'],30:['2','4'],31:['2','3']};passed=0
def rejected(fn):
 try:fn()
 except ValueError:return
 raise AssertionError('unsafe timing/color was accepted')
for slide,ids in cases.items():
 for oid in ids:
  part,shape=v.shape(slide,oid);tree=v.cache[part];proof=classify(tree,oid,True);assert proof['videoTargetId']!=oid
  assert appearance(v,part,shape,'lastClr')['fillRGBA']==[255,255,255,.35]
  rejected(lambda:appearance(v,part,shape));passed+=1
part,_=v.shape(24,'46');base=v.cache[part]
def mutate(fn):
 tree=copy.deepcopy(base);fn(tree);rejected(lambda:classify(tree,'46',True))
mutate(lambda t:t.find('.//p:spTgt',NS).set('spid','46'))
mutate(lambda t:t.find('.//p:tn',NS).set('val','999'))
mutate(lambda t:t.find('.//p:cmd',NS).set('cmd','unexpected()'))
mutate(lambda t:t.find('.//p:cmd',NS).append(E.Element(P+'anim')))
mutate(lambda t:t.find('.//p:cBhvr/p:tgtEl/p:spTgt',NS).__setattr__('tag',P+'sldTgt'))
mutate(lambda t:t.find('.//p:cTn',NS).set('unexpected','1'))
tree=copy.deepcopy(base);E.SubElement(tree,P+'transition').append(E.Element(P+'wipe'));rejected(lambda:classify(tree,'46',False))
part,_=v.shape(29,'21');assert classify(v.cache[part],'21',True)['transition']=='wipe';rejected(lambda:classify(v.cache[part],'21',False))
v.close();print(f'PASS {passed} real targets, 8 timing negatives and 14 explicit fallback negatives')
