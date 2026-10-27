"""Build the authored demo and its exact Pages copy; no engine changes."""
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util, hashlib, re, sys
ROOT = Path(__file__).resolve().parents[1]

def rendered():
    spec = importlib.util.spec_from_file_location('maker_build', ROOT/'skills/gigadev-html-maker/scripts/build.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with TemporaryDirectory(prefix='gigadev-demo-') as tmp:
        html = module.build(ROOT/'examples/shell-demo/project/deck.json', Path(tmp)/'demo.html', ROOT/'examples/shell-demo/project/theme.json')
    canonical = re.sub(r'data-sk-doc="gd-[0-9a-f]{32}"', 'data-sk-doc="DEMO-ID"', html, count=1)
    identity = hashlib.sha256(canonical.encode()).hexdigest()[:32]
    return canonical.replace('data-sk-doc="DEMO-ID"', 'data-sk-doc="gd-'+identity+'"', 1)

def main():
    html = rendered()
    targets = [ROOT/'examples/shell-demo/index.html', ROOT/'docs/index.html']
    if '--check' in sys.argv:
        assert all(p.read_text() == html for p in targets), 'Generated demo stale: run python3 scripts/build_demo.py'
        print('PASS authored example and Pages copy are current')
    else:
        for p in targets:
            p.write_text(html)
        print('Built example and Pages copy with stable content-derived ID')

if __name__ == '__main__':
    main()
