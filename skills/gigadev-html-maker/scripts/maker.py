"""Run Maker readiness, canonical builds and checks against the exact delivered HTML."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / 'scripts'


def sha256(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def run_json(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {'status': 'fail', 'message': (result.stderr or result.stdout).strip()[-5000:]}
    if result.returncode:
        raise StepFailure(command, result.returncode, payload)
    return payload


class StepFailure(Exception):
    def __init__(self, command, code, result):
        super().__init__('Command failed: ' + Path(command[1]).name)
        self.details = {'command': command, 'exitCode': code, 'result': result}


def readiness():
    if sys.version_info < (3, 10):
        raise ValueError('Python 3.10+ is required')
    node = shutil.which('node')
    if not node:
        raise ValueError('Node 20+ is required. See references/setup.md')
    version = subprocess.run([node, '--version'], capture_output=True, text=True, check=True).stdout.strip()
    if int(version.lstrip('v').split('.')[0]) < 20:
        raise ValueError('Node 20+ is required')
    pointer = json.loads((ROOT / 'assets/current-baseline.json').read_text())
    package = json.loads((ROOT / 'package.json').read_text())
    baseline_name = pointer['file']
    if Path(baseline_name).name != baseline_name or not baseline_name.startswith('baseline-release-'):
        raise ValueError('Invalid baseline pointer')
    if pointer['version'] != package['version']:
        raise ValueError('Package and baseline pointer versions differ')
    baseline = json.loads((ROOT / 'assets' / baseline_name).read_text())
    for name, expected in baseline['modules'].items():
        if Path(name).name != name or sha256(ROOT / 'assets' / name) != expected:
            raise ValueError('Missing or changed pinned shell module: ' + name)
    required = ['build.py', 'check_delivery.mjs', 'check_runtime.mjs', 'shell_identity.mjs',
                'check.mjs', 'presentation_roles.py', 'composition_plan.py', 'typography.py']
    for name in required:
        if not (SCRIPTS / name).is_file():
            raise ValueError('Incomplete skill package: scripts/' + name)
    with tempfile.TemporaryDirectory(prefix='maker-ready-') as temp:
        folder = Path(temp)
        project = folder / 'deck.json'
        project.write_text(json.dumps({
            'title': 'Maker readiness',
            'cssIsolation': 'strict',
            'slides': [{'id': 'ready', 'label': 'Ready', 'header': 'none',
                        'html': '<h2>Maker readiness</h2><p>Shell runtime smoke check.</p>'}]
        }))
        output = folder / 'smoke.html'
        run_json([sys.executable, '-B', str(SCRIPTS / 'build.py'), str(project), str(output)])
        smoke = run_json([node, str(SCRIPTS / 'check_runtime.mjs'), str(output), str(project)])
    return {'status': 'pass', 'makerVersion': package['version'], 'nodeVersion': version,
            'baselineSha256': sha256(ROOT / 'assets' / baseline_name), 'smoke': smoke}


def verify(output, project=None, qa_dir=None):
    before = {'html': sha256(output)}
    if project:
        before['project'] = sha256(project)
    runtime = run_json([shutil.which('node') or 'node', str(SCRIPTS / 'check_runtime.mjs'),
                        str(output)] + ([str(project)] if project else []))
    result = {'runtime': runtime}
    if project:
        result['delivery'] = run_json([
            shutil.which('node') or 'node', str(SCRIPTS / 'check_delivery.mjs'),
            str(output), str(project)])
        result['shellRegression'] = run_json([
            shutil.which('node') or 'node', str(SCRIPTS / 'check.mjs'),
            str(output), '--out', str(qa_dir)])
    after = {'html': sha256(output)}
    if project:
        after['project'] = sha256(project)
    if before != after:
        raise ValueError('HTML or project changed during verification. Check the new revision.')
    return {'status': result.get('delivery', runtime)['status'], 'scope': 'delivery' if project else 'runtime-only',
            'hashes': after, 'checks': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    ready = commands.add_parser('ready')
    ready.add_argument('--report', type=Path, required=True)
    build = commands.add_parser('build')
    build.add_argument('project', type=Path)
    build.add_argument('output', type=Path)
    build.add_argument('--theme', type=Path)
    build.add_argument('--composition-plan', type=Path, required=True)
    build.add_argument('--typography', choices=['off', 'review', 'apply'], default='apply')
    build.add_argument('--external-media', action='store_true')
    build.add_argument('--report', type=Path, required=True)
    check = commands.add_parser('verify')
    check.add_argument('output', type=Path)
    check.add_argument('--project', type=Path)
    check.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    # Reserve new evidence before doing work. Refuse to reuse an earlier report.
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x') as report_file:
        result = {'status': 'fail', 'action': args.action, 'visualApproval': False}
        try:
            if args.action == 'ready':
                result['environment'] = readiness()
                result['status'] = 'pass'
            elif args.action == 'build':
                if args.output.exists():
                    raise ValueError('Use a new HTML output path')
                result['environment'] = readiness()
                inputs = [args.project, args.composition_plan] + ([args.theme] if args.theme else [])
                input_hashes = {str(file.resolve()): sha256(file) for file in inputs}
                command = [sys.executable, '-B', str(SCRIPTS / 'build.py'),
                           str(args.project.resolve()), str(args.output.resolve()), '--final',
                           '--composition-plan', str(args.composition_plan.resolve()),
                           '--typography', args.typography]
                if args.theme:
                    command.extend(['--theme', str(args.theme.resolve())])
                if args.external_media:
                    command.append('--external-media')
                result['build'] = run_json(command)
                result['verification'] = verify(args.output, args.project, args.report.with_suffix('.shell-qa'))
                if input_hashes != {str(file.resolve()): sha256(file) for file in inputs}:
                    raise ValueError('Build inputs changed during the guarded build')
                result['inputs'] = input_hashes
                result['status'] = result['verification']['status']
            else:
                result['verification'] = verify(args.output, args.project, args.report.with_suffix('.shell-qa'))
                result['status'] = result['verification']['status']
        except Exception as error:
            result['error'] = str(error)
            if isinstance(error, StepFailure):
                result['failure'] = error.details
        json.dump(result, report_file, ensure_ascii=False, indent=2)
        report_file.write('\n')
    print(json.dumps({'status': result['status'], 'action': args.action,
                      'report': str(args.report.resolve()), 'visualApproval': False}))
    return 0 if result['status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
