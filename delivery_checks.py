"""Check delivery evidence bindings; this module never verifies a mathematical proof."""
import hashlib
import json
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_inspection(work, root):
    manifest = json.loads((root / 'targets.json').read_text(encoding='utf-8'))
    names = [manifest['upstream_target'], *manifest['interface_targets'],
             manifest['semantic_bridge'], *manifest['model_declarations']]
    receipt = json.loads((work / 'target-inspection.json').read_text(encoding='utf-8'))
    manifest_hash = digest(root / 'targets.json')
    source = work / 'target-inspection' / manifest_hash / 'Targets.lean'
    expected_text = 'import ExactStatement\n' + '\n'.join('#check ' + name for name in names) + '\n'
    expected = dict(manifest_sha256=manifest_hash,
                    exact_receipt_sha256=digest(work / 'exact-statement.json'),
                    source_sha256=digest(source), log_sha256=digest(work / 'logs/target-inspection.log'))
    if receipt.get('status') != 'passed' or receipt.get('declarations') != names:
        raise RuntimeError('Target inspection status or declaration list changed')
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise RuntimeError('Target inspection source or log binding changed')
    if source.read_text(encoding='utf-8') != expected_text:
        raise RuntimeError('Target inspection source does not implement the manifest')


def validate_replay(work, root):
    path = work / 'kernel-replay.json'
    if not path.exists():
        return
    replay = json.loads(path.read_text(encoding='utf-8'))
    exact = json.loads((work / 'exact-statement.json').read_text(encoding='utf-8'))
    compiler = Path(exact['compiler_path'])
    tool = compiler.with_name('leanchecker' + compiler.suffix)
    if replay.get('status') != 'passed':
        raise RuntimeError('Retained replay has not passed')
    if replay.get('independent_kernel') is not False or replay.get('fresh_environment') is not False:
        raise RuntimeError('Unsupported replay verification level')
    expected = dict(tool_sha256=digest(tool), driver_sha256=digest(root / 'replay.py'),
                    exact_receipt_sha256=digest(work / 'exact-statement.json'))
    if any(replay.get(k) != v for k, v in expected.items()):
        raise RuntimeError('Replay tool, driver or interface receipt changed')
    if replay.get('mode') == 'custom-closure':
        modules = list(json.loads((work / 'compiled-modules.json').read_text(encoding='utf-8')))
        modules += ['NoSquareSumHypothesis', 'ExactStatement']
    elif replay.get('mode') == 'interface-only':
        modules = ['ExactStatement']
    else:
        raise RuntimeError('Unknown replay scope')
    if [r['module'] for r in replay['results']] != modules:
        raise RuntimeError('Replay module list changed')
    for row in replay['results']:
        name = row['module']
        log = work / 'logs' / ('replay-' + name + '.log')
        if row['exit_code'] != 0 or row['command'] != [str(tool), '-v', name]:
            raise RuntimeError('Replay command or exit status changed')
        if digest(log) != row['log_sha256'] or 'replaying ' + name not in log.read_text(encoding='utf-8'):
            raise RuntimeError('Replay output evidence changed')
