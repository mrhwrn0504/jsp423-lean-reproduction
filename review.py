"""Print checked terminal types and definitions using the retained build environment."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def main(work):
    result = json.loads((work/'result.json').read_text(encoding='utf-8'))
    status = json.loads((work/'status.json').read_text(encoding='utf-8'))
    if result['status'] != 'passed' or status['stage'] != 'passed':
        raise RuntimeError('Complete the fresh build before inspecting terminal types')
    env = os.environ.copy()
    settings = json.loads((work/'build-environment.json').read_text(encoding='utf-8'))
    env.update(settings)
    toolchain = Path(settings['LEAN_SYSROOT'])
    env['PATH'] = str(toolchain/'bin') + os.pathsep + env.get('PATH', '')
    compiler = toolchain/'bin'/('lean.exe' if os.name == 'nt' else 'lean')
    compiler_hash = hashlib.sha256(compiler.read_bytes()).hexdigest()
    if compiler_hash != result['compiler_sha256']:
        raise RuntimeError('Compiler changed since the recorded build')
    source = ROOT/'ReviewTargets.lean'
    command = [str(compiler), '-j1', '-M4096', '-R', str(ROOT), str(source)]
    with (work/'logs/statement-review.log').open('w',encoding='utf-8') as stream:
        code = subprocess.run(command, cwd=work/'mathlib', env=env, stdout=stream,
                              stderr=subprocess.STDOUT).returncode
    receipt = dict(exit_code=code, command=command,
                   finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   result_sha256=hashlib.sha256((work/'result.json').read_bytes()).hexdigest(),
                   extension_olean_sha256=hashlib.sha256((work/'lib/NoSquareSumHypothesis.olean').read_bytes()).hexdigest(),
                   compiler_sha256=compiler_hash,
                   source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                   log_sha256=hashlib.sha256((work/'logs/statement-review.log').read_bytes()).hexdigest())
    (work/'statement-review.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))
    if code:
        raise SystemExit(code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, default=ROOT/'_work')
    main(parser.parse_args().work_dir.resolve())
