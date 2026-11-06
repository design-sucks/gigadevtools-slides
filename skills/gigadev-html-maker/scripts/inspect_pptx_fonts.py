"""Inspect PPTX embedded EOT headers without claiming decoded font or glyph identity."""
import argparse, hashlib, json, posixpath, struct
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

P='http://schemas.openxmlformats.org/presentationml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'

def inspect(data):
 if len(data)<82:raise ValueError('EOT header truncated')
 total,size,version,flags=struct.unpack_from('<IIII',data)
 if total!=len(data) or size>total-82 or data[34:36]!=b'LP':raise ValueError('Invalid EOT length or magic')
 pos=82;names=[]
 for _ in range(4):
  if pos+2>total-size:raise ValueError('EOT name length truncated')
  n=struct.unpack_from('<H',data,pos)[0];pos+=2
  if n%2 or pos+n+2>total-size:raise ValueError('Invalid EOT name length')
  names.append(data[pos:pos+n].decode('utf-16le'));pos+=n+2
 payload=data[total-size:];signature=payload[:4].hex()
 return {'format':'EOT','version':f'0x{version:08x}','flags':f'0x{flags:08x}',
  'compressedMTX':bool(flags&4),'fontDataBytes':size,'fontDataSignatureHex':signature,
  'headerFamily':names[0],'headerStyle':names[1],'headerVersion':names[2],'headerFullName':names[3],
  'headerWeight':struct.unpack_from('<I',data,28)[0],'headerItalic':bool(data[27]),'headerFsType':struct.unpack_from('<H',data,32)[0],
  'status':'unsupported-mtx' if flags&4 else 'unverified-uncompressed',
  'reason':'MTX-compressed EOT is not a browser-loadable sfnt and is not decoded by this skill' if flags&4 else 'Payload and license require independent font parsing before use'}

def inspect_pptx(path):
 faces=[]
 with ZipFile(path) as z:
  root=ET.fromstring(z.read('ppt/presentation.xml'));rels=ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
  mapping={x.get('Id'):x.get('Target') for x in rels if x.get('TargetMode')!='External'}
  for font in root.findall('{%s}embeddedFontLst/{%s}embeddedFont'%(P,P)):
   name=font.find('{%s}font'%P);family=name.get('typeface') if name is not None else None
   for child in font:
    rid=child.get('{%s}id'%R)
    if not rid:continue
    target=mapping.get(rid,'');part=target[1:] if target.startswith('/') else posixpath.normpath(posixpath.join('ppt',target))
    result={'declaredFamily':family,'declaredFace':child.tag.rsplit('}',1)[-1],'relationshipId':rid,'part':part}
    try:
     data=z.read(part);result.update(sha256=hashlib.sha256(data).hexdigest(),**inspect(data))
    except (KeyError,ValueError,UnicodeError,struct.error) as e:result.update(status='unsupported-or-invalid',reason=str(e))
    faces.append(result)
 return {'source':str(Path(path).resolve()),'faces':faces,'limitations':['EOT header identity is not proof of decoded sfnt identity, matching face, font licensing or actual browser glyph rendering.','No font is extracted or connected without a supported verified payload and permission.']}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('pptx');a=p.parse_args();print(json.dumps(inspect_pptx(a.pptx),ensure_ascii=False,indent=2))
