"""Build standalone skill ZIPs and a clean bundle from an explicit allowlist."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import hashlib, json
from check_release import ROOT, check, SKIP, FORBIDDEN

def add(z, path, archive_path):
    info = ZipInfo(Path(archive_path).as_posix(), (1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = ZIP_DEFLATED
    z.writestr(info, path.read_bytes())

def main():
    files = check()
    release = json.loads((ROOT/'releases.json').read_text())
    out = ROOT/'dist'
    out.mkdir(exist_ok=True)
    made = []
    for skill in release['skills']:
        archive = out/(skill+'.zip')
        prefix = Path('skills')/skill
        with ZipFile(archive, 'w', ZIP_DEFLATED) as z:
            for p in files:
                rel = p.relative_to(ROOT)
                if rel.is_relative_to(prefix):
                    add(z, p, Path(skill)/rel.relative_to(prefix))
        made.append(archive)
    bundle = out/'gigadevtools-slides.zip'
    with ZipFile(bundle, 'w', ZIP_DEFLATED) as z:
        for p in files:
            add(z, p, p.relative_to(ROOT))
    made.append(bundle)
    for archive in made:
        with ZipFile(archive) as z:
            assert z.testzip() is None
            assert all(not SKIP.intersection(Path(n).parts) and Path(n).name not in FORBIDDEN for n in z.namelist())
            assert any(n.endswith('/SKILL.md') for n in z.namelist())
    manifest = {'release':release, 'artifacts':{p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes':p.stat().st_size} for p in made}}
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (out/'SHA256SUMS').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in made+[out/'manifest.json'])+'\n')
    print(json.dumps({'status':'packaged', 'archives':[p.name for p in made]}))

if __name__ == '__main__':
    main()
