"""Replay explicitly named custom modules using the bundled Lean kernel checker."""
import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('jsp423_check', ROOT / 'check_exact.py')
checked = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checked)


def main(work, closure):
    receipt = work / 'kernel-replay.json'
    started = time.perf_counter()
    receipt.write_text(json.dumps({'status': 'running'}) + '\n', encoding='utf-8')
    try:
        checked.audit(work)
        checked.validate_exact(work)
        settings = json.loads((work / 'build-environment.json').read_text(encoding='utf-8'))
        compiler = Path(settings['LEAN_SYSROOT']) / 'bin' / ('lean.exe' if os.name == 'nt' else 'lean')
        tool = compiler.with_name('leanchecker.exe' if os.name == 'nt' else 'leanchecker')
        tool_hash = checked.digest(tool)
        before = checked.input_fingerprints(work, compiler)
        own_hash = checked.digest(Path(__file__))
        exact_receipt = checked.digest(work / 'exact-statement.json')
        env = os.environ.copy()
        env.update(settings)
        env['PATH'] = str(tool.parent) + os.pathsep + env.get('PATH', '')
        env['LEAN_NUM_THREADS'] = '1'
        modules = list(json.loads((work / 'compiled-modules.json').read_text(encoding='utf-8'))) if closure else []
        modules += ['NoSquareSumHypothesis', 'ExactStatement'] if closure else ['ExactStatement']
        results = []
        for module in modules:
            log = work / 'logs' / ('replay-' + module + '.log')
            command = [str(tool), '-v', module]
            begin = time.perf_counter()
            with log.open('w', encoding='utf-8') as stream:
                code = subprocess.run(command, cwd=work / 'mathlib', env=env,
                                      stdout=stream, stderr=subprocess.STDOUT).returncode
            if code:
                raise RuntimeError(f'Kernel replay exit {code}: {log}')
            if f'replaying {module}' not in log.read_text(encoding='utf-8'):
                raise RuntimeError('Missing target replay evidence: ' + module)
            results.append(dict(module=module, command=command, exit_code=code,
                                seconds=time.perf_counter() - begin, log_sha256=checked.digest(log)))
        checked.require_unchanged(before, checked.input_fingerprints(work, compiler))
        checked.validate_exact(work)
        if tool_hash != checked.digest(tool) or own_hash != checked.digest(Path(__file__)):
            raise RuntimeError('Replay tool or driver changed')
        if exact_receipt != checked.digest(work / 'exact-statement.json'):
            raise RuntimeError('Interface receipt changed')
        data = dict(status='passed', finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    mode='custom-closure' if closure else 'interface-only', results=results,
                    seconds=time.perf_counter() - started, tool_sha256=tool_hash,
                    driver_sha256=own_hash, exact_receipt_sha256=exact_receipt,
                    independent_kernel=False, fresh_environment=False,
                    limitation='Same Lean kernel replay; imported Mathlib constants are trusted, not replayed from an empty environment')
        receipt.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'status': 'passed', 'mode': data['mode'], 'modules': len(results), 'seconds': data['seconds']}))
    except Exception as exc:
        receipt.write_text(json.dumps({'status': 'failed', 'error': str(exc)}) + '\n', encoding='utf-8')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, default=ROOT / '_work')
    parser.add_argument('--custom-closure', action='store_true', help='Replay 18 upstream custom modules and both local interfaces sequentially')
    args = parser.parse_args()
    main(args.work_dir.resolve(), args.custom_closure)
