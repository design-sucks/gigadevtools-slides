"""Fast source/package checks. No browser and no private machine configuration."""
from pathlib import Path
import hashlib, json, re, subprocess
ROOT = Path(__file__).resolve().parents[1]
TOP = {'README.md', 'README.ru.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'SECURITY.md', 'releases.json', '.gitignore', '.gitattributes', 'skills', 'examples', 'docs', 'scripts', 'tests', '.github'}
SKIP = {'.git', 'node_modules', '__pycache__', '.venv', 'build', 'dist', '.cache'}
FORBIDDEN = {'runtime.local.json', '.DS_Store', '.env'}

def source_files():
    result = []
    for p in sorted(ROOT.rglob('*')):
        rel = p.relative_to(ROOT)
        if p.is_file() and rel.parts[0] in TOP and not SKIP.intersection(rel.parts) and p.suffix not in {'.pyc', '.pyo'}:
            result.append(p)
    return result

def check():
    release = json.loads((ROOT/'releases.json').read_text())
    for name, version in release['skills'].items():
        folder = ROOT/'skills'/name
        pkg = json.loads((folder/'package.json').read_text())
        skill = (folder/'SKILL.md').read_text()
        assert pkg['name'] == name and pkg['version'] == version, f'Package version mismatch: {name}'
        assert re.search(r'^name: '+re.escape(name)+r'$', skill, re.M), f'Skill name mismatch: {name}'
        assert re.search(r'^  version: "'+re.escape(version)+r'"$', skill, re.M), f'Skill version mismatch: {name}'
        lock = json.loads((folder/'package-lock.json').read_text())
        assert lock['packages']['']['version'] == version
        for doc in ['LICENSE', 'THIRD_PARTY_NOTICES.md']:
            assert (folder/doc).exists()
    deck = json.loads((ROOT/'examples/shell-demo/project/deck.json').read_text())
    assert deck['version'] == release['demo']['version'] == 1 and len(deck['slides']) == 13
    assets = ROOT/'skills/gigadev-html-maker/assets'
    baseline = json.loads((assets/'baseline-v17_2.json').read_text())['modules']
    for name, digest in baseline.items():
        assert hashlib.sha256((assets/name).read_bytes()).hexdigest() == digest, f'Runtime baseline changed: {name}; review intended changes'
    for face in json.loads((assets/'fonts/manifest.json').read_text())['faces']:
        assert hashlib.sha256((assets/face['path']).read_bytes()).hexdigest() == face['sha256']
    files = source_files()
    assert files
    for p in files:
        rel = p.relative_to(ROOT)
        assert p.name not in FORBIDDEN and not p.name.startswith('.env.'), f'Host-only file: {rel}'
        if p.suffix in {'.md', '.json', '.py', '.js', '.mjs', '.yml', '.html'}:
            assert not re.search('/'+'Users'+r'/[A-Za-z0-9_.-]+/', p.read_text()), f'Personal absolute path: {rel}'
        if p.suffix == '.md':
            for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', p.read_text()):
                if '://' in target or target.startswith(('#', 'mailto:')):
                    continue
                target = target.split('#')[0].strip('<>')
                if target:
                    assert (p.parent/target).exists(), f'Broken local link: {rel} -> {target}'
        if p.suffix in {'.js', '.mjs'}:
            subprocess.run(['node', '--check', str(p)], check=True, capture_output=True)
    assert (ROOT/'docs/index.html').read_bytes() == (ROOT/'examples/shell-demo/index.html').read_bytes()
    print(json.dumps({'status':'pass', 'release':release['release'], 'sourceFiles':len(files), 'runtime':'unchanged v17.2', 'fontScope':'third-party corporate pilot, not MIT'}))
    return files

if __name__ == '__main__':
    check()
