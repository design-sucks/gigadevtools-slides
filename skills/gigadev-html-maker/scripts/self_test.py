"""Regression fixture: nested text, table, chart, metadata, notes and validation."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import json
from extract_pptx import extract
from build import build

def run():
 with TemporaryDirectory(prefix='gd-html-maker-') as tmp:
  r=Path(tmp);ppt=r/'Fixture.pptx'
  a='http://schemas.openxmlformats.org/drawingml/2006/main';p='http://schemas.openxmlformats.org/presentationml/2006/main';c='http://schemas.openxmlformats.org/drawingml/2006/chart';rel='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
  para=lambda t:f'<a:p><a:r><a:t>{t}</a:t></a:r></a:p>'
  shape=lambda i,t:f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="Object {i}"/></p:nvSpPr><p:txBody>{para(t)}</p:txBody></p:sp>'
  body=shape(1,'Точное название')+'<p:grpSp><p:nvGrpSpPr><p:cNvPr id="2" name="Group"/></p:nvGrpSpPr>'+shape(3,'Вложенная подпись 12,5%')+'</p:grpSp>'
  body+='<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="4" name="Table"/></p:nvGraphicFramePr><a:graphic><a:graphicData><a:tbl><a:tr><a:tc><a:txBody>'+para('Категория')+'</a:txBody></a:tc><a:tc><a:txBody>'+para('Значение')+'</a:txBody></a:tc></a:tr><a:tr><a:tc><a:txBody>'+para('A')+'</a:txBody></a:tc><a:tc><a:txBody>'+para('42')+'</a:txBody></a:tc></a:tr></a:tbl></a:graphicData></a:graphic></p:graphicFrame>'
  body+='<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="5" name="Chart"/></p:nvGraphicFramePr><a:graphic><a:graphicData><c:chart r:id="chart1"/></a:graphicData></a:graphic></p:graphicFrame>'
  body+='<p:sp><p:nvSpPr><p:cNvPr id="6" name="Number"/></p:nvSpPr><p:txBody><a:p><a:fld type="slidenum"><a:t>7</a:t></a:fld></a:p></p:txBody></p:sp>'
  with ZipFile(ppt,'w') as z:
   z.writestr('ppt/presentation.xml',f'<p:presentation xmlns:p="{p}" xmlns:r="{rel}"><p:sldIdLst><p:sldId id="256" r:id="s1"/></p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/></p:presentation>')
   z.writestr('ppt/_rels/presentation.xml.rels','<Relationships><Relationship Id="s1" Target="slides/slide1.xml" Type="x/slide"/></Relationships>')
   z.writestr('ppt/slides/slide1.xml',f'<p:sld xmlns:p="{p}" xmlns:a="{a}" xmlns:c="{c}" xmlns:r="{rel}"><p:cSld><p:spTree>{body}</p:spTree></p:cSld></p:sld>')
   z.writestr('ppt/slides/_rels/slide1.xml.rels','<Relationships><Relationship Id="chart1" Target="../charts/chart1.xml" Type="x/chart"/><Relationship Id="notes1" Target="../notesSlides/notesSlide1.xml" Type="x/notesSlide"/></Relationships>')
   z.writestr('ppt/charts/chart1.xml',f'<c:chartSpace xmlns:c="{c}"><c:chart><c:plotArea><c:barChart><c:ser><c:tx><c:v>Показатель</c:v></c:tx><c:cat><c:strCache><c:pt idx="0"><c:v>A</c:v></c:pt></c:strCache></c:cat><c:val><c:numCache><c:pt idx="0"><c:v>12.50</c:v></c:pt></c:numCache></c:val></c:ser></c:barChart></c:plotArea></c:chart></c:chartSpace>')
   z.writestr('ppt/notesSlides/notesSlide1.xml',f'<p:notes xmlns:p="{p}" xmlns:a="{a}">'+shape(1,'Внутренняя заметка')+'</p:notes>')
  deck=extract(ppt,r/'project');s=deck['slides'][0];assert s['sourceNumber']==1
  nested=next(b for b in s['blocks'] if b.get('paragraphs',[{}])[0].get('text')=='Вложенная подпись 12,5%');assert nested['group']=='s1-o2'
  table=next(b for b in s['blocks'] if b['kind']=='table');assert table['rows'][1][1][0]['text']=='42'
  chart=next(b for b in s['blocks'] if b['kind']=='chart');assert chart['series'][0]['values']==['12.50'];assert s['metadata'][0]['paragraphs'][0]['text']=='7';assert 'Внутренняя заметка' in s['notes']
  result=build(r/'project/deck.json',r/'result.html');assert '12.50' in result and '12,5%' in result;assert 'Внутренняя заметка' not in result;assert '@@GD_' not in result
  deck['order']=['missing'];(r/'project/deck.json').write_text(json.dumps(deck))
  try:build(r/'project/deck.json',r/'invalid.html')
  except ValueError:pass
  else:raise AssertionError('Unknown order id accepted')
 print('PASS nested source text, exact table/chart values, page metadata, private notes and invalid-order rejection')
if __name__=='__main__':run()
