"""Verify declared local HTML resources and external-media manifests; no browser decode."""
import argparse,hashlib,json,re,sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
class Refs(HTMLParser):
 def __init__(self):super().__init__();self.items=[];self.in_style=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);self.in_style=tag=='style' or self.in_style
  if tag in ('img','video','audio','source','script','iframe','embed') and a.get('src'):self.items.append(a['src'])
  if a.get('poster'):self.items.append(a['poster'])
  if tag=='link' and 'stylesheet' in (a.get('rel') or '') and a.get('href'):self.items.append(a['href'])
  if a.get('style'):self.css(a['style'])
 def handle_endtag(self,tag):
  if tag=='style':self.in_style=False
 def handle_data(self,data):
  if self.in_style:self.css(data)
 def css(self,data):
  self.items.extend(x.strip(' \t\r\n\'"') for x in re.findall(r'url\(([^)]*)\)',data,re.I))
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('html',type=Path);args=a.parse_args();file=args.html.resolve();root=file.parent;parser=Refs();parser.feed(file.read_text());issues=[];dirs=set();checked=0
 for ref in parser.items:
  if ref.startswith(('data:','#')):continue
  if ref.startswith('blob:'):issues.append({'code':'ephemeral-blob-resource','ref':ref});continue
  u=urlsplit(ref)
  if u.scheme or u.netloc:issues.append({'code':'remote-dependency','ref':ref});continue
  target=(root/unquote(u.path)).resolve()
  if not target.is_relative_to(root):issues.append({'code':'outside-package','ref':ref});continue
  if not target.is_file():issues.append({'code':'missing-resource','ref':ref});continue
  checked+=1
  if (target.parent/'manifest.json').is_file():dirs.add(target.parent)
 for directory in dirs:
  try:m=json.loads((directory/'manifest.json').read_text())
  except (OSError,ValueError) as e:issues.append({'code':'invalid-manifest','message':str(e)});continue
  for item in m.get('files',[]):
   target=(directory/item['path']).resolve()
   if not target.is_relative_to(directory) or not target.is_file():issues.append({'code':'missing-manifest-file','file':item['path']});continue
   h=hashlib.sha256()
   with target.open('rb') as f:
    for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
   if h.hexdigest()!=item.get('sha256'):issues.append({'code':'hash-mismatch','file':item['path']})
 report={'status':'fail' if issues else 'review','html':str(file),'checkedLocalReferences':checked,'mediaManifests':len(dirs),'issues':issues,'limitations':['Static resource and manifest check only: copy the complete package to a different directory and verify offline rendering, playback and save/reopen separately.','Dynamically constructed URLs, nested SVG dependencies and external hyperlinks require separate review.']}
 print(json.dumps(report,ensure_ascii=False,indent=2));return 1 if issues else 0
if __name__=='__main__':sys.exit(main())
