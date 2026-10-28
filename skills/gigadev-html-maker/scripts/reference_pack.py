"""Small reference index and explicit-palette study generator (stdlib only).
Generated studies remain marked sample-only; this does not redesign a real deck.
"""
from pathlib import Path
import argparse,html,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]/'assets/reference-pack'
ROLES=('bg','ink','muted','line','surface','surfaceSecondary','accent','accentSoft','onAccent','series2','series3')
def catalog():return json.loads((ROOT/'catalog.json').read_text())
def theme_css(palette):
 missing=set(ROLES)-set(palette)
 if missing:raise ValueError('Explicit project paint roles required: '+', '.join(sorted(missing)))
 for key in ROLES:
  if not re.fullmatch(r'#[0-9a-fA-F]{6}',str(palette[key])):raise ValueError('Paint roles must be #RRGGBB: '+key)
 rows=[]
 for item in json.loads((ROOT/'paint-roles.json').read_text()).values():
  rgb=tuple(int(palette[item['role']][i:i+2],16) for i in (1,3,5));a=item['alpha']
  rows.append(item['token']+':'+('rgba('+','.join(map(str,rgb))+','+str(a)+')' if a<1 else palette[item['role']])+';')
 return ':root{'+''.join(rows)+'}'
def study(ident,palette,out):
 row=next((x for x in catalog()['compositions'] if x['id']==ident),None)
 if not row:raise ValueError('Unknown reference: '+ident)
 out=Path(out)
 if out.exists():raise ValueError('Use a new output directory')
 css=theme_css(palette);text=(ROOT/row['html']).read_text()
 # Substitute known paint strings in a single pass; never alter embedded asset bytes.
 paints=json.loads((ROOT/'paint-roles.json').read_text());keys=sorted(paints,key=len,reverse=True)
 pattern=re.compile('|'.join(re.escape(x)for x in keys))
 data=[]
 def hold(m):data.append(m[0]);return '__GD_DATA_'+str(len(data)-1)+'__'
 text=re.sub(r'data:[^\"\')\s]+',hold,text)
 text=pattern.sub(lambda m:'var('+paints[m[0]]['token']+')',text)
 for i,value in enumerate(data):text=text.replace('__GD_DATA_'+str(i)+'__',value)
 text=text.replace('../fonts.css','fonts.css').replace('<body ', '<style>'+css+'</style><body ',1)
 out.mkdir(parents=True);(out/'index.html').write_text(text);shutil.copy2(ROOT/'fonts.css',out/'fonts.css')
 (out/'study.json').write_text(json.dumps({'reference':ident,'revision':catalog()['version'],'sampleOnly':True,'palette':palette,'warning':'Study only. Replace instructional text, synthetic data, sample graphics and navigation; adapt source content to the accepted Maker shell. Embedded sample artwork may have locked colors; do not reuse it as project branding.'},ensure_ascii=False,indent=2)+'\n')
 return out/'index.html'
def main():
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True);l=s.add_parser('list');l.add_argument('--family');a=s.add_parser('show');a.add_argument('id');a=s.add_parser('study');a.add_argument('id');a.add_argument('--palette',required=True);a.add_argument('--out',required=True);a=p.parse_args()
 if a.command=='list':
  for row in catalog()['compositions']:
   if not a.family or a.family in row['family']:print(row['id']+' | '+row['family']+' | '+row['name']+' | '+row['useWhen'])
 elif a.command=='show':
  row=next(x for x in catalog()['compositions']if x['id']==a.id);print(json.dumps({**row,'html':str(ROOT/row['html']),'preview':str(ROOT/row['preview'])},ensure_ascii=False,indent=2))
 else:print(study(a.id,json.loads(Path(a.palette).read_text()),a.out))
if __name__=='__main__':main()
