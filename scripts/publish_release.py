"""Publish the built manifest through GitHub's runner-local gh authentication."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def gh(*args):
 return subprocess.run(['gh',*args],cwd=ROOT,text=True,capture_output=True)
def main():
 release=json.loads((ROOT/'releases.json').read_text());tag=release['release'];state=release.get('releaseState','draft')
 assert state in {'draft','prerelease'},'Pilot releases must be draft or prerelease'
 files=[ROOT/'dist'/name for name in ['gigadev-html-maker.zip','gigadev-html-export.zip','gigadevtools-slides.zip','manifest.json','SHA256SUMS']]
 assert all(p.is_file()for p in files),'Build packages first'
 manifest=json.loads((ROOT/'dist/manifest.json').read_text());assert manifest['release']==release
 for p in files[:3]:assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['artifacts'][p.name]['sha256']
 if '--dry-run'in sys.argv:
  print(json.dumps({'tag':tag,'state':state,'assets':[p.name for p in files],'networkWrites':False}));return
 assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GH_TOKEN'),'Publish from GitHub Actions with its scoped token'
 assert os.environ.get('GITHUB_REF_NAME')=='main','Publish from main only'
 title='Corporate pilot · '+tag
 existing=gh('release','view',tag,'--json','isDraft,isPrerelease')
 if existing.returncode==0:
  info=json.loads(existing.stdout)
  if not info['isDraft']:
   print('Published release already exists; refusing to overwrite published assets');return
  upload=gh('release','upload',tag,*map(str,files),'--clobber')
  if upload.returncode:raise RuntimeError(upload.stderr)
  if state=='prerelease':
   edit=gh('release','edit',tag,'--draft=false','--prerelease','--title',title)
   if edit.returncode:raise RuntimeError(edit.stderr)
 else:
  args=['release','create',tag,'--target',os.environ['GITHUB_SHA'],'--title',title,'--notes-file',str(ROOT/'docs/pilot-release-notes.md'),'--draft'if state=='draft'else'--prerelease',*map(str,files)]
  created=gh(*args)
  if created.returncode:raise RuntimeError(created.stderr)
 print('Release packages uploaded: '+tag+' ('+state+')')
if __name__=='__main__':main()
