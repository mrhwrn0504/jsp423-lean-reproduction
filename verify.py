"""One local entry point: full build, interface compilation, or validated reuse."""
import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('jsp423_check', ROOT / 'check_exact.py')
checked = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checked)


def validate_workflow(work):
    data = json.loads((work / 'verification.json').read_text(encoding='utf-8'))
    if data.get('status') != 'passed':
        raise RuntimeError('Unified verification has not passed')
    expected = {'driver_sha256': checked.digest(Path(__file__)),
                'manifest_sha256': checked.digest(ROOT / 'targets.json'),
                'exact_receipt_sha256': checked.digest(work / 'exact-statement.json'),
                'target_inspection_sha256': checked.digest(work / 'target-inspection.json')}
    if any(data.get(k) != v for k, v in expected.items()):
        raise RuntimeError('Unified verification record is stale')
    checked.validate_exact(work)
    for stage in data['stages']:
        log = work / 'logs' / ('verify-' + stage['name'] + '.log') if stage['name'] != 'target-inspection' else work / 'logs/target-inspection.log'
        if stage['exit_code'] != 0 or checked.digest(log) != stage['log_sha256']:
            raise RuntimeError('Unified stage evidence changed')
    return data


def run(work, mode, toolchain=None):
    work.mkdir(parents=True, exist_ok=True)
    (work / 'logs').mkdir(exist_ok=True)
    report = work / 'verification.json'
    started = time.perf_counter()
    data = dict(status='running', mode=mode, stages=[])
    def save():
        report.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        own_hash = checked.digest(Path(__file__))
        manifest_file = ROOT / 'targets.json'
        manifest_hash = checked.digest(manifest_file)
        manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
        if manifest['interface_targets'] != checked.TARGETS:
            raise RuntimeError('Manifest and compiled interface target list disagree')
        names = [manifest['upstream_target'], *manifest['interface_targets'],
                 manifest['semantic_bridge'], *manifest['model_declarations']]
        if not all(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*', n) for n in names):
            raise RuntimeError('Invalid declaration name in manifest')
        def stage(name, command):
            begin = time.perf_counter()
            log = work / 'logs' / ('verify-' + name + '.log')
            with log.open('w', encoding='utf-8') as stream:
                code = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT).returncode
            data['stages'].append(dict(name=name, command=command, exit_code=code,
                                       seconds=time.perf_counter() - begin, log_sha256=checked.digest(log)))
            save()
            if code:
                raise RuntimeError(f'{name} failed: {log}')
        if mode == 'full':
            command = [sys.executable, '-I', str(ROOT / 'reproduce.py'), '--work-dir', str(work)]
            if toolchain:
                command += ['--toolchain', str(toolchain)]
            stage('full-build', command)
            stage('review', [sys.executable, '-I', str(ROOT / 'review.py'), '--work-dir', str(work)])
        stage('interface', [sys.executable, '-I', str(ROOT / 'check_exact.py'), '--work-dir', str(work)]
              + (['--reuse'] if mode == 'retained' else []))
        settings = json.loads((work / 'build-environment.json').read_text(encoding='utf-8'))
        compiler = Path(settings['LEAN_SYSROOT']) / 'bin' / ('lean.exe' if os.name == 'nt' else 'lean')
        inspection_receipt = work / 'target-inspection.json'
        inspection_dir = work / 'target-inspection' / manifest_hash
        source = inspection_dir / 'Targets.lean'
        source_text = 'import ExactStatement\n' + '\n'.join('#check ' + name for name in names) + '\n'
        if mode == 'retained':
            inspection = json.loads(inspection_receipt.read_text(encoding='utf-8'))
            expected = {'manifest_sha256': manifest_hash,
                        'exact_receipt_sha256': checked.digest(work / 'exact-statement.json'),
                        'source_sha256': checked.digest(source),
                        'log_sha256': checked.digest(work / 'logs/target-inspection.log')}
            if inspection.get('status') != 'passed' or any(inspection.get(k) != v for k, v in expected.items()):
                raise RuntimeError('Target inspection is stale; run compile mode')
        else:
            inspection_dir.mkdir(parents=True, exist_ok=True)
            source.write_text(source_text, encoding='utf-8', newline='\n')
            inspection_source_hash = checked.digest(source)
            env = os.environ.copy()
            env.update(settings)
            env['PATH'] = str(compiler.parent) + os.pathsep + env.get('PATH', '')
            env['LEAN_NUM_THREADS'] = '1'
            before = checked.input_fingerprints(work, compiler)
            command = [str(compiler), '-j1', '-M4096', '-R', str(inspection_dir), str(source)]
            log = work / 'logs/target-inspection.log'
            begin = time.perf_counter()
            with log.open('w', encoding='utf-8') as stream:
                code = subprocess.run(command, cwd=work / 'mathlib', env=env,
                                      stdout=stream, stderr=subprocess.STDOUT).returncode
            data['stages'].append(dict(name='target-inspection', command=command,
                                       exit_code=code, seconds=time.perf_counter() - begin,
                                       log_sha256=checked.digest(log)))
            save()
            if code:
                raise RuntimeError('Target inspection failed')
            checked.require_unchanged(before, checked.input_fingerprints(work, compiler))
            if checked.digest(source) != inspection_source_hash:
                raise RuntimeError('Inspection source changed during Lean execution')
            inspection = dict(status='passed', declarations=names, manifest_sha256=manifest_hash,
                              exact_receipt_sha256=checked.digest(work / 'exact-statement.json'),
                              source_sha256=checked.digest(source), log_sha256=checked.digest(log))
            inspection_receipt.write_text(json.dumps(inspection, indent=2) + '\n', encoding='utf-8')
        checked.validate_exact(work)
        if checked.digest(Path(__file__)) != own_hash or checked.digest(manifest_file) != manifest_hash:
            raise RuntimeError('Workflow or target manifest changed during verification')
        data.update(status='passed', finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    seconds=time.perf_counter() - started, driver_sha256=own_hash,
                    manifest_sha256=manifest_hash, targets=manifest,
                    exact_receipt_sha256=checked.digest(work / 'exact-statement.json'),
                    target_inspection_sha256=checked.digest(inspection_receipt),
                    newly_compiled_upstream_modules=18 if mode == 'full' else 0,
                    new_interface_compilation=mode != 'retained',
                    independent_kernel_replay=False)
        save()
        print(json.dumps({'status': 'passed', 'mode': mode, 'seconds': data['seconds']}))
    except Exception as exc:
        data.update(status='failed', error=str(exc), seconds=time.perf_counter() - started)
        save()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['full', 'compile', 'retained'], default='full')
    parser.add_argument('--work-dir', type=Path, default=ROOT / '_work')
    parser.add_argument('--toolchain', type=Path)
    args = parser.parse_args()
    run(args.work_dir.resolve(), args.mode, args.toolchain.resolve() if args.toolchain else None)
