"""Audit the retained base build, then compile and audit the exact JSP423 targets."""
import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('jsp423_local_audit', ROOT / 'audit.py')
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)
audit, digest = audit_module.audit, audit_module.digest
TARGETS = ['JSP423Audit.original_problem', 'JSP423Audit.original_problem_expanded',
           'JSP423Audit.original_problem_partial_sums']


def input_fingerprints(work, compiler):
    """Bind the interface, driver, fixed environment, compiler and custom imports."""
    files = [Path(__file__), ROOT / 'audit.py', ROOT / 'ExactStatement.lean',
             ROOT / 'sources.lock.json', compiler, work / 'result.json',
             work / 'build-environment.json', work / 'compiled-modules.json']
    compiled = json.loads((work / 'compiled-modules.json').read_text(encoding='utf-8'))
    files += [work / 'lib' / (name.replace('.', '/') + '.olean') for name in compiled]
    return {str(path): digest(path) for path in files}


def require_unchanged(before, after):
    if before != after:
        changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
        raise RuntimeError('Verification inputs changed during execution: ' + ', '.join(changed))


def validate_exact(work):
    data = json.loads((work / 'exact-statement.json').read_text(encoding='utf-8'))
    if data.get('status') != 'passed' or data.get('exit_code') != 0 or data.get('targets') != TARGETS:
        raise RuntimeError('Exact-statement compilation is not current and successful')
    files = {'base_result_sha256': work / 'result.json',
             'checker_sha256': Path(__file__), 'source_sha256': ROOT / 'ExactStatement.lean',
             'olean_sha256': work / 'lib/ExactStatement.olean',
             'log_sha256': work / 'logs/exact-statement.log'}
    for key, path in files.items():
        if digest(path) != data[key]:
            raise RuntimeError('Exact-statement evidence changed: ' + key)
    compiler = Path(data['compiler_path'])
    require_unchanged(data['input_fingerprints'], input_fingerprints(work, compiler))
    if digest(Path(data['snapshot_source'])) != data['source_sha256']:
        raise RuntimeError('Compiled interface snapshot changed')
    text = (work / 'logs/exact-statement.log').read_text(encoding='utf-8')
    for target in TARGETS:
        matches = re.findall(re.escape(target) + r"' depends on axioms:\s*\[([^\]]*)\]", text)
        values = {v.strip() for v in matches[0].split(',')} if len(matches) == 1 else set()
        if values != {'propext', 'Classical.choice', 'Quot.sound'} or sorted(values) != data['axioms'][target]:
            raise RuntimeError('Exact-statement axiom evidence changed')
    return data


def main(work, reuse=False):
    started = time.perf_counter()
    if reuse:
        reuse_receipt = work / 'exact-reuse.json'
        reuse_receipt.write_text(json.dumps({'status': 'running'}) + '\n', encoding='utf-8')
        try:
            audit(work)
            before_receipt = digest(work / 'exact-statement.json')
            data = validate_exact(work)
            if digest(work / 'exact-statement.json') != before_receipt:
                raise RuntimeError('Cached receipt changed during validation')
            record = dict(status='passed', mode='validated-cache-reuse',
                          finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          seconds=time.perf_counter() - started,
                          exact_receipt_sha256=before_receipt, targets=data['targets'],
                          new_lean_execution=False)
            reuse_receipt.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(record))
            return
        except Exception as exc:
            reuse_receipt.write_text(json.dumps({'status': 'failed', 'error': str(exc)}) + '\n', encoding='utf-8')
            raise
    checker_hash = digest(Path(__file__))
    receipt = work / 'exact-statement.json'
    receipt.write_text(json.dumps({'status': 'running'}) + '\n', encoding='utf-8')
    try:
        audit(work)
        audit_before_seconds = time.perf_counter() - started
        settings = json.loads((work / 'build-environment.json').read_text(encoding='utf-8'))
        env = os.environ.copy()
        env.update(settings)
        env['LEAN_NUM_THREADS'] = '1'
        compiler = Path(settings['LEAN_SYSROOT']) / 'bin' / ('lean.exe' if os.name == 'nt' else 'lean')
        env['PATH'] = str(compiler.parent) + os.pathsep + env.get('PATH', '')
        source = ROOT / 'ExactStatement.lean'
        before = input_fingerprints(work, compiler)
        snapshot_dir = work / 'exact-inputs' / before[str(source)]
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_source = snapshot_dir / source.name
        snapshot_source.write_bytes(source.read_bytes())
        if digest(snapshot_source) != before[str(source)]:
            raise RuntimeError('Interface changed while taking input snapshot')
        output = work / 'lib/ExactStatement.olean'
        log = work / 'logs/exact-statement.log'
        command = [str(compiler), '-j1', '-M4096', '-R', str(snapshot_dir), '-o', str(output), str(snapshot_source)]
        lean_started = time.perf_counter()
        with log.open('w', encoding='utf-8') as stream:
            code = subprocess.run(command, cwd=work / 'mathlib', env=env,
                                  stdout=stream, stderr=subprocess.STDOUT).returncode
        if code:
            raise RuntimeError(f'Lean exited {code}: {log}')
        lean_seconds = time.perf_counter() - lean_started
        require_unchanged(before, input_fingerprints(work, compiler))
        if digest(snapshot_source) != before[str(source)]:
            raise RuntimeError('Compiled snapshot changed during Lean execution')
        audit_after_started = time.perf_counter()
        audit(work)
        require_unchanged(before, input_fingerprints(work, compiler))
        audit_after_seconds = time.perf_counter() - audit_after_started
        text = log.read_text(encoding='utf-8')
        axioms = {}
        for target in TARGETS:
            matches = re.findall(re.escape(target) + r"' depends on axioms:\s*\[([^\]]*)\]", text)
            values = {v.strip() for v in matches[0].split(',')} if len(matches) == 1 else set()
            if values != {'propext', 'Classical.choice', 'Quot.sound'}:
                raise RuntimeError('Unexpected axiom output for ' + target)
            axioms[target] = sorted(values)
        if digest(Path(__file__)) != checker_hash:
            raise RuntimeError('Checker changed during this run; rerun it')
        data = dict(status='passed', finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    command=command, exit_code=code, targets=TARGETS, axioms=axioms,
                    base_result_sha256=digest(work / 'result.json'),
                    base_audit_sha256=digest(work / 'audit.json'),
                    checker_sha256=checker_hash, source_sha256=digest(source),
                    compiler_path=str(compiler), input_fingerprints=before,
                    snapshot_source=str(snapshot_source),
                    timings_seconds=dict(audit_before=audit_before_seconds, lean=lean_seconds,
                                         audit_after=audit_after_seconds, total=time.perf_counter() - started),
                    olean_sha256=digest(output), log_sha256=digest(log),
                    scope='New interface compilation against the audited retained base; not a fresh rebuild of 18 upstream modules')
        receipt.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(data, ensure_ascii=False))
    except Exception as exc:
        receipt.write_text(json.dumps({'status': 'failed', 'error': str(exc)}) + '\n', encoding='utf-8')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, default=ROOT / '_work')
    parser.add_argument('--reuse', action='store_true',
                        help='Validate retained inputs and results without rerunning Lean; fail if stale')
    args = parser.parse_args()
    main(args.work_dir.resolve(), reuse=args.reuse)
