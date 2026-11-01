"""Compile the standard finite-prefix bridge against the audited pinned environment."""
import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('jsp423_check', ROOT / 'check_exact.py')
checked = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checked)


def main():
    work = ROOT / '_work'
    receipt = work / 'index-shift.json'
    started = time.perf_counter()
    receipt.write_text('{"status":"running"}\n', encoding='utf-8')
    try:
        checked.audit(work)
        settings = json.loads((work / 'build-environment.json').read_text(encoding='utf-8'))
        compiler = Path(settings['LEAN_SYSROOT']) / 'bin' / ('lean.exe' if os.name == 'nt' else 'lean')
        before = checked.input_fingerprints(work, compiler)
        source = ROOT / 'IndexShift.lean'
        source_hash = checked.digest(source)
        driver_hash = checked.digest(Path(__file__))
        snapshot_dir = work / 'index-inputs' / source_hash
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot = snapshot_dir / source.name
        snapshot.write_bytes(source.read_bytes())
        output = work / 'lib/IndexShift.olean'
        log = work / 'logs/index-shift.log'
        env = os.environ.copy()
        env.update(settings)
        env['PATH'] = str(compiler.parent) + os.pathsep + env.get('PATH', '')
        env['LEAN_NUM_THREADS'] = '1'
        command = [str(compiler), '-j1', '-M4096', '-R', str(snapshot_dir), '-o', str(output), str(snapshot)]
        with log.open('w', encoding='utf-8') as stream:
            code = subprocess.run(command, cwd=work / 'mathlib', env=env,
                                  stdout=stream, stderr=subprocess.STDOUT).returncode
        if code:
            raise RuntimeError(f'Finite-prefix bridge Lean exit {code}: {log}')
        text = log.read_text(encoding='utf-8')
        target = 'JSP423Audit.partial_sums_drop_zero'
        matches = re.findall(re.escape(target) + r"' depends on axioms:\s*\[([^\]]*)\]", text)
        if len(matches) == 1:
            axioms = {v.strip() for v in matches[0].split(',') if v.strip()}
        elif target + "' does not depend on any axioms" in text:
            axioms = set()
        else:
            raise RuntimeError('Missing bridge axiom evidence')
        if axioms - {'propext', 'Classical.choice', 'Quot.sound'}:
            raise RuntimeError('Unexpected finite-prefix bridge axiom')
        checked.require_unchanged(before, checked.input_fingerprints(work, compiler))
        if source_hash != checked.digest(source) or source_hash != checked.digest(snapshot) or driver_hash != checked.digest(Path(__file__)):
            raise RuntimeError('Finite-prefix bridge inputs changed')
        data = dict(status='passed', seconds=time.perf_counter() - started,
                    finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    target=target, command=command, exit_code=code, axioms=sorted(axioms),
                    source_sha256=source_hash, snapshot_source=str(snapshot),
                    output_sha256=checked.digest(output), log_sha256=checked.digest(log),
                    driver_sha256=driver_hash, compiler_sha256=checked.digest(compiler),
                    base_result_sha256=checked.digest(work / 'result.json'),
                    scope='Generic natural partial-sum finite-prefix identity, not an independent proof of Erdos527')
        receipt.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(data))
    except Exception as exc:
        receipt.write_text(json.dumps({'status': 'failed', 'error': str(exc)}) + '\n', encoding='utf-8')
        raise


if __name__ == '__main__':
    main()
