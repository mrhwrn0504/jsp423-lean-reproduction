"""Audit retained fresh-build evidence; does not itself compile any Lean file."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def audit(work):
    checks = []
    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))
        if not condition:
            raise RuntimeError('Audit failed: ' + name)
    lock, result, status = read(ROOT/'sources.lock.json'), read(work/'result.json'), read(work/'status.json')
    check('latest status and result passed', status['stage'] == 'passed' and result['status'] == 'passed')
    check('lock digest', digest(ROOT/'sources.lock.json') == result['lock_sha256'])
    check('driver digest', digest(ROOT/'reproduce.py') == result['driver_sha256'])
    check('exactly 18 custom modules', len(lock['modules']) == result['custom_modules'] == 18)
    compiled, env, toolchain = read(work/'compiled-modules.json'), read(work/'build-environment.json'), read(work/'toolchain-receipt.json')
    check('exact compiled module set', set(compiled) == {r['module'] for r in lock['modules']})
    check('fixed compiler version', re.search(r'\bversion 4\.33\.0(?:\b|,)', toolchain['version']))
    compiler = Path(toolchain['path'])/'bin'/('lean.exe' if __import__('os').name == 'nt' else 'lean')
    check('compiler digest', digest(compiler) == toolchain['lean_sha256'] == result['compiler_sha256'])
    check('compiler sysroot matches receipt', Path(env['LEAN_SYSROOT']).resolve() == Path(toolchain['path']).resolve())
    expected_paths = [work/'lib', work/'mathlib/.lake/build/lib/lean'] + [
        work/'mathlib/.lake/packages'/p['name']/'.lake/build/lib/lean' for p in lock['mathlib_manifest']['packages']]
    import os
    check('only isolated library search roots',
          [Path(p).resolve() for p in env['LEAN_PATH'].split(os.pathsep)] == [p.resolve() for p in expected_paths])
    first = read(work/'logs/source-git-init.log.receipt.json')['finished_utc']
    first_stamp = datetime.datetime.fromisoformat(first).timestamp()
    end_stamp = datetime.datetime.fromisoformat(result['finished_utc']).timestamp()
    check('build time interval exists', first_stamp <= end_stamp)
    for row in lock['modules']:
        name, relative = row['module'], Path(row['path'])
        source, output = work/'sources'/relative, work/'lib'/relative.with_suffix('.olean')
        receipt = read(work/f'logs/compile-{name}.log.receipt.json')
        check(name+' original bytes', digest(work/'originals'/relative) == row['original_sha256'])
        check(name+' prepared source', digest(source) == row['prepared_lf_sha256'] == compiled[name]['source_sha256'])
        check(name+' output bytes', digest(output) == compiled[name]['olean_sha256'])
        check(name+' compiler exit', receipt['exit_code'] == compiled[name]['exit_code'] == 0)
        check(name+' explicit source and output', receipt['command'] == [str(compiler), '-j1', '-M4096', '-R',
              str(work/'sources'), '-o', str(output), str(source)])
        check(name+' fresh output time', first_stamp <= output.stat().st_mtime <= end_stamp + 2)
    check('patch digest', digest(ROOT/'patches/kernel-v4.33.0.patch') == lock['patch_sha256'])
    for stem in ('patch-check', 'patch-apply', 'mathlib-cache', 'extension-axioms'):
        check(stem+' exit code', read(work/f'logs/{stem}.log.receipt.json')['exit_code'] == 0)
    extension = ROOT/'NoSquareSumHypothesis.lean'
    check('extension source', digest(extension) == lock['extension_sha256'] == result['extension_sha256'])
    check('extension output', digest(work/'lib/NoSquareSumHypothesis.olean') == result['extension_olean_sha256'])
    axiom_log = (work/'logs/extension-axioms.log').read_text(encoding='utf-8')
    names = ['Erdos527.erdos_527', 'JSP423Audit.literal_statement',
             'JSP423Audit.ae_convergence_without_square_sum_divergence']
    check('exact target set', set(names) == set(result['axioms']))
    for name in names:
        pattern = re.escape(name) + r"' depends on axioms:\s*\[([^\]]*)\]"
        matches = re.findall(pattern, axiom_log)
        values = {v.strip() for v in matches[0].split(',')} if len(matches) == 1 else set()
        check(name+' actual standard axioms', values == {'propext', 'Classical.choice', 'Quot.sound'} == set(result['axioms'][name]))
    review = read(work/'statement-review.json')
    check('statement inspection exit code', review['exit_code'] == 0)
    check('statement inspection uses this build', review['result_sha256'] == digest(work/'result.json'))
    check('statement inspection uses this extension', review['extension_olean_sha256'] == result['extension_olean_sha256'])
    check('statement inspection uses this compiler', review['compiler_sha256'] == result['compiler_sha256'])
    check('statement inspection source', digest(ROOT/'ReviewTargets.lean') == review['source_sha256'])
    check('statement inspection log', digest(work/'logs/statement-review.log') == review['log_sha256'])
    manifest = read(work/'mathlib/lake-manifest.json')
    check('complete Mathlib manifest', manifest == lock['mathlib_manifest'])
    dependencies = [(work/'mathlib', lock['mathlib']['rev'])] + [
        (work/'mathlib/.lake/packages'/p['name'], p['rev']) for p in manifest['packages']]
    for directory, revision in dependencies:
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=directory, text=True).strip()
        dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=directory, text=True).strip()
        check(directory.name+' fixed clean revision', head == revision and not dirty)
    report = dict(status='passed', checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  checks=checks, result_sha256=digest(work/'result.json'),
                  limitation='Evidence audit, not another Lean kernel or an original mathematical proof')
    (work/'audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(status='passed', checks=len(checks), work=str(work)), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, default=ROOT/'_work')
    work = parser.parse_args().work_dir.resolve()
    try:
        audit(work)
    except BaseException as exc:
        (work/'audit.json').write_text(json.dumps(dict(status='failed',error=str(exc)),indent=2)+'\n',encoding='utf-8')
        raise
