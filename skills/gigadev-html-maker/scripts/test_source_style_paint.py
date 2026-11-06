import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('source_style', ROOT / 'source_style.py')
style = importlib.util.module_from_spec(spec)
spec.loader.exec_module(style)

class StyleGateTests(unittest.TestCase):
    def colors(self, markup):
        return style.authored_paint(markup)[1]

    def test_paint_literals(self):
        markup = '''<style>.x { color:#AEB8C8; background:linear-gradient(#111, rgba(99,175,252,1), rgb(16 173 216)); }</style>
        <p style="color:#abc"></p><svg><line stroke="rgba(12,52,234,1)"/><stop stop-color="#cA61dA"/><path fill="#d243ea"/></svg>'''
        self.assertTrue({'#AEB8C8','#111111','#63AFFC','#10ADD8','#AABBCC','#0C34EA','#CA61DA','#D243EA'} <= self.colors(markup))

    def test_non_evidence(self):
        markup = '''<!-- <p style="color:#123456"></p> --><script>"<i style='color:#123456'>"</script>
        <style>/* .x {color:#123456} */ .x { content:"#123456"; background:url(#123456); color:rgba(18,52,86,0) }</style>
        <p data-x="#123456">#123456</p><svg><path d="#123456"/></svg>'''
        self.assertNotIn('#123456',self.colors(markup))

    def test_nested_url_not_evidence(self):
        payload = 'url(data:image/svg+xml,<svg fill=rgb(18,52,86)>#123456</svg>)'
        for markup in (f'<style>.x{{background:{payload}}}</style>', f'<p style="background:{payload}"></p>',
                       "<style>.x{background:url('data:(#123456)');color:#abcdef}</style>"):
            self.assertNotIn('#123456', self.colors(markup))
        self.assertIn('#ABCDEF', self.colors("<style>.x{background:url('data:(#123456)');color:#abcdef}</style>"))

    def test_invalid_and_boundary(self):
        self.assertNotIn('#123456',self.colors('<p style="color:rgb(18,52,342);background:#12345678"></p>'))
        self.assertNotIn('#123456',self.colors('<p style="color:rgba(18,52,86,2)"></p>'))

    def test_token_rgb_declaration(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'style-inventory.json').write_text(json.dumps({'colors':[{'id':'e','role':'text','resolvedBase':'#63AFFC'}],'graphics':[]}))
            (p/'deck.json').write_text(json.dumps({'slides':[]}))
            (p/'dec.json').write_text(json.dumps({'mode':'preserve-design','palette':[{'sourceEvidence':'e','role':'text','target':'--brand','targetColor':'#63AFFC','decision':'retained'}],'graphics':[]}))
            (p/'index.html').write_text(''); (p/'theme.json').write_text(json.dumps({'css':':root{--brand:rgb(99,175,252)} p{color:var(--brand)}'}))
            self.assertEqual('pass',style.check(p,p/'dec.json',p/'index.html',p/'theme.json')['status'])

    def test_gate_missing_and_authored(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'style-inventory.json').write_text(json.dumps({'colors':[{'id':'e','role':'text','resolvedBase':'#123456'}],'graphics':[]}))
            (p/'deck.json').write_text(json.dumps({'slides':[{'html':'<p style="color:#123456">x</p>'}]}))
            (p/'dec.json').write_text(json.dumps({'mode':'preserve-design','palette':[{'sourceEvidence':'e','role':'text','target':'#123456','targetColor':'#123456','decision':'retained'}],'graphics':[]}))
            (p/'index.html').write_text('')
            self.assertEqual('pass',style.check(p,p/'dec.json',p/'index.html')['status'])
            (p/'deck.json').write_text(json.dumps({'slides':[{'html':'','blocks':[{'color':'#123456'}]}]}))
            self.assertIn('palette targetColor not used in CSS declaration: #123456',style.check(p,p/'dec.json',p/'index.html')['errors'])

    def test_shell_excluded_and_slide_paint(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'style-inventory.json').write_text(json.dumps({'colors':[{'id':'e','role':'text','resolvedBase':'#9DEDA5'}],'graphics':[]}))
            (p/'deck.json').write_text(json.dumps({'slides':[{'html':''}]}))
            (p/'dec.json').write_text(json.dumps({'mode':'preserve-design','palette':[{'sourceEvidence':'e','role':'text','target':'#9DEDA5','targetColor':'#9DEDA5','decision':'retained'}],'graphics':[]}))
            h=p/'index.html'; shell='<style>:root{--sk-accent:#9DEDA5} .ui{color:var(--sk-accent)}</style><div class="ui" style="color:#9DEDA5"></div>'
            h.write_text(shell)
            self.assertEqual('fail',style.check(p,p/'dec.json',h)['status'])
            for slide in ['<div class="gd-content"><svg><path fill="#9DEDA5"/></svg></div>', '<div class="gd-slide-background" style="background:#9DEDA5"></div>']:
                h.write_text(shell+slide)
                self.assertEqual('pass',style.check(p,p/'dec.json',h)['status'])
            h.write_text(shell)
            (p/'deck.json').write_text(json.dumps({'slides':[{'html':'','background':{'type':'color','value':'#9DEDA5'}}]}))
            self.assertEqual('pass',style.check(p,p/'dec.json',h)['status'])

if __name__ == '__main__': unittest.main()
