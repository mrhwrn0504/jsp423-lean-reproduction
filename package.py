"""Create a small relocatable project archive, excluding downloaded dependencies."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
FILES = ['README.md', 'STATEMENT.md', 'ATTRIBUTION.md', 'REPRODUCTION.md', 'BOOTSTRAP.md', 'IMPROVEMENTS.md',
         'reproduce.py', 'audit.py', 'review.py', 'ReviewTargets.lean', 'package.py', 'NoSquareSumHypothesis.lean',
         'ExactStatement.lean', 'check_exact.py', 'test_input_binding.py', 'REVIEW-PACKET.md',
         'verify.py', 'targets.json', 'test_workflow.py', 'replay.py',
         'incremental.py', 'test_incremental.py',
         'delivery_checks.py', 'test_delivery_checks.py',
         'sources.lock.json', 'lean-toolchain', '.gitignore',
         'patches/kernel-v4.33.0.patch', 'licenses/Apache-2.0.txt',
         'licenses/plby-latest-NOTICE.txt', 'licenses/sources.json']


def package(work, output):
    from audit import audit as audit_build
    audit_build(work)
    from check_exact import validate_exact
    validate_exact(work)
    from verify import validate_workflow
    validate_workflow(work)
    from delivery_checks import validate_inspection, validate_replay
    validate_inspection(work, ROOT)
    validate_replay(work, ROOT)
    audit = json.loads((work/'audit.json').read_text(encoding='utf-8'))
    if audit['status'] != 'passed':
        raise RuntimeError('An evidence audit must pass before packaging')
    # Evidence snapshots retain paths from this specific run. They are not config.
    evidence_names = ['result.json', 'status.json', 'audit.json', 'compiled-modules.json',
                      'source-receipt.json', 'dependency-receipt.json', 'toolchain-receipt.json',
                      'build-environment.json', 'statement-review.json', 'exact-statement.json',
                      'verification.json', 'target-inspection.json']
    evidence_names += [name for name in ('full-toolchain-install.json', 'history-preservation.json',
                                        'patch-provenance.json', 'completion-requirements.json', 'exact-reuse.json',
                                        'shared-artifact-cache.json', 'test-summary.json', 'relocation-source-map.json')
                       if (work/name).exists()]
    files = [(ROOT/name, 'jsp423-repro/'+name) for name in FILES]
    files += [(work/name, 'jsp423-repro/evidence/'+name) for name in evidence_names]
    test_summary = work/'test-summary.json'
    if test_summary.exists():
        tests = json.loads(test_summary.read_text(encoding='utf-8'))
        if tests.get('status') != 'passed' or any(row['exit_code'] for row in tests['tests']):
            raise RuntimeError('Regression summary has not passed')
        for name, expected in tests['inputs'].items():
            if Path(name).name != name or hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
                raise RuntimeError('Regression input changed')
        for row in tests['tests']:
            log = work/'logs'/('regression-'+row['test']+'.log')
            if hashlib.sha256(log.read_bytes()).hexdigest() != row['log_sha256']:
                raise RuntimeError('Regression log changed')
    files += [(path, 'jsp423-repro/evidence/logs/'+path.name)
              for path in sorted((work/'logs').iterdir()) if path.is_file()]
    exact = json.loads((work/'exact-statement.json').read_text(encoding='utf-8'))
    snapshot = Path(exact['snapshot_source'])
    files.append((snapshot, 'jsp423-repro/evidence/exact-inputs/'+snapshot.parent.name+'/'+snapshot.name))
    verification = json.loads((work/'verification.json').read_text(encoding='utf-8'))
    inspection = work/'target-inspection'/verification['manifest_sha256']/'Targets.lean'
    files.append((inspection, 'jsp423-repro/evidence/target-inspection/Targets.lean'))
    replay_path = work/'kernel-replay.json'
    if replay_path.exists():
        replay = json.loads(replay_path.read_text(encoding='utf-8'))
        if replay.get('status') != 'passed':
            raise RuntimeError('Retained replay has not passed; do not package it as successful evidence')
        def checksum(path):
            with path.open('rb') as stream:
                return hashlib.file_digest(stream, 'sha256').hexdigest()
        if replay['driver_sha256'] != checksum(ROOT/'replay.py') or replay['exact_receipt_sha256'] != checksum(work/'exact-statement.json'):
            raise RuntimeError('Retained replay is stale')
        for row in replay['results']:
            if row['exit_code'] or row['log_sha256'] != checksum(work/'logs'/('replay-'+row['module']+'.log')):
                raise RuntimeError('Replay log evidence changed')
        files.append((replay_path, 'jsp423-repro/evidence/kernel-replay.json'))
    hashes = []
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, name in files:
            data = path.read_bytes()
            archive.writestr(name, data)
            hashes.append(dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
        manifest = dict(files=hashes, exclusions=['toolchain', 'downloaded source trees',
                         'Mathlib cache', 'custom .olean files'],
                        note='Evidence paths record the original run; execute reproduce.py for a new build')
        archive.writestr('jsp423-repro/PACKAGE-MANIFEST.json', json.dumps(manifest,indent=2))
    with output.open('rb') as stream:
        checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
    output.with_suffix('.zip.sha256').write_text(checksum+'  '+output.name+'\n', encoding='utf-8')
    print(json.dumps(dict(archive=str(output), bytes=output.stat().st_size,
                         members=len(files)+1, sha256=checksum)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, default=ROOT/'_work')
    parser.add_argument('--output', type=Path, default=ROOT.parent/'deliverables/jsp423-repro.zip')
    args = parser.parse_args()
    package(args.work_dir.resolve(), args.output.resolve())
