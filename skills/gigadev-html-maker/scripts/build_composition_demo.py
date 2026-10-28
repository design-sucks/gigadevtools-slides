"""Build a reproducible neutral library fixture in a new project directory."""
from pathlib import Path
import argparse,copy,json,shutil
from compositions import ROOT,catalog
from build import build

def main():
 p=argparse.ArgumentParser();p.add_argument('out',help='New directory, not an existing project');p.add_argument('--variant',choices=['normal','headings','uneven'],default='normal');a=p.parse_args();out=Path(a.out).resolve()
 if out.exists():raise ValueError('Use a new fixture directory')
 out.mkdir(parents=True);shutil.copytree(ROOT/'media',out/'media');(out/'fonts').mkdir();shutil.copy2(ROOT.parent/'fonts/SBSansDisplay-ExtendedSemibold.otf',out/'fonts/SBSansDisplay-ExtendedSemibold.otf')
 rows=[]
 for c in catalog()['compositions']:
  d=json.loads((ROOT/c['example']).read_text());variants=[('regular',d)]
  if a.variant=='headings':
   short=copy.deepcopy(d);short['title']='Одна мысль'
   long=copy.deepcopy(d);long['title']='Как организовать совместную работу и проверить результат в сложных условиях без потери важного'
   variants=[('short',short),('regular',d),('long',long)]
  elif a.variant=='uneven':
   if c['id']not in ['agenda','problem-cards','role-process','architecture','feature-map','maturity']:continue
   d=copy.deepcopy(d)
   for i,item in enumerate(d['items']):item['body']='Кратко.'if i%2 else('Важный контекст, ограничения и проверка результата. '*10)[:min(c['itemBodyMax'],150)].rsplit(' ',1)[0]+'.'
   variants=[('uneven',d)]
  for suffix,data in variants:rows.append({'id':'library-'+c['id']+'-'+suffix,'label':c['name'],'section':'Композиции','topic':c['name'],'composition':{'id':c['id'],'version':c['version'],'data':data}})
 deck={'schema':1,'purpose':'composition-library-demo','title':'Библиотека композиций','version':1,'proofreadingStatus':'reviewed','slides':rows}
 theme=json.loads((ROOT.parent/'base-theme.json').read_text());theme.pop('cssFile',None);theme['themes']=['dark','light'];theme['fonts']=[{'family':'SB Sans Display Extended','weight':600,'path':'fonts/SBSansDisplay-ExtendedSemibold.otf'}];theme['css']=':root{--cp-heading-font:"SB Sans Display",sans-serif}.gd-content{display:block}'
 (out/'deck.json').write_text(json.dumps(deck,ensure_ascii=False,indent=2)+'\n');(out/'theme.json').write_text(json.dumps(theme,ensure_ascii=False,indent=2)+'\n');build(out/'deck.json',out/'Library_v01.html',out/'theme.json')
if __name__=='__main__':main()
