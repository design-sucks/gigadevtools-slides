from pathlib import Path
import sys,json,re,tempfile,hashlib
s=Path(__file__).resolve().parents[1];sys.path.insert(0,str(s/'scripts'))
from reference_pack import catalog,theme_css,study,ROOT
from build import build
assert len(catalog()['compositions'])==24
for x in catalog()['compositions']:
 p=ROOT/x['html'];assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'];assert '@font-face'not in p.read_text();assert (ROOT/x['preview']).exists();assert 'data-gd-reference-only="true"'in p.read_text()
palette=dict(bg='#141A24',ink='#F1F4FA',muted='#ADB9CC',line='#45546B',surface='#293547',surfaceSecondary='#18202B',accent='#8CA5FF',accentSoft='#23314D',onAccent='#080F20',series2='#64D7CF',series3='#C5A2F2')
try:theme_css({'bg':'#000000'})
except ValueError:pass
else:raise AssertionError('Implicit fallback palette')
with tempfile.TemporaryDirectory()as tmp:
 p=Path(tmp);out=study('ref-14',palette,p/'blue');text=out.read_text();css=re.findall('<style>(.*?)</style>',text,re.S);assert '#9de5ae'not in ''.join(css).lower();assert 'rgba(241,244,250,0.55)'in text
 deck=p/'deck.json';deck.write_text(json.dumps({'title':'Guard','slides':[{'id':'test','html':'<div data-gd-reference-only="true">sample</div>'}]}))
 try:build(deck,p/'bad.html')
 except ValueError as e:assert 'Reference sample' in str(e)
 else:raise AssertionError('Unedited reference accepted')
print('PASS24 reference hashes/previews, deduplicated fonts, explicit palette and alpha, original-green removal from CSS, sample delivery guard')
