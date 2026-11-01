"""Fetch pinned sources and compile the JSP423 import closure (Python 3.11+)."""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parent
LOCK = json.loads((ROOT / 'sources.lock.json').read_text(encoding='utf-8'))
ACTIVE_WORK = None


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def run(args, cwd, log, env):
    print('RUN', ' '.join(map(str, args)), flush=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=env,
                                stdout=stream, stderr=subprocess.STDOUT)
    save(log.with_suffix(log.suffix + '.receipt.json'),
         dict(command=list(map(str, args)), cwd=str(cwd), exit_code=result.returncode,
              finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    if result.returncode:
        raise RuntimeError(f'Exit {result.returncode}: see {log}')


def fetch_sources(work, env):
    originals, sources = work / 'originals', work / 'sources'
    def fetch(row):
        dest = originals / row['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            with urllib.request.urlopen(row['url'], timeout=120) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != row['original_sha256']:
                raise RuntimeError('Downloaded source hash mismatch: ' + row['module'])
            dest.write_bytes(data)
        if sha(dest) != row['original_sha256']:
            raise RuntimeError('Original source hash mismatch: ' + row['module'])
        target = sources / row['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        # Patches use LF. Raw upstream bytes are retained in originals/.
        target.write_text(dest.read_text(encoding='utf-8-sig'), encoding='utf-8', newline='\n')
        return row['module']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for name in pool.map(fetch, LOCK['modules']):
            print('SOURCE', name, flush=True)
    patch = ROOT / 'patches/kernel-v4.33.0.patch'
    if sha(patch) != LOCK['patch_sha256']:
        raise RuntimeError('Patch hash mismatch')
    # An explicit repository boundary prevents an enclosing workspace repository
    # from silently skipping patches whose paths lie outside its current prefix.
    run(['git', 'init'], sources, work/'logs/source-git-init.log', env)
    run(['git', '-c', 'core.autocrlf=false', 'apply', '--check', patch], sources, work/'logs/patch-check.log', env)
    run(['git', '-c', 'core.autocrlf=false', 'apply', patch], sources, work/'logs/patch-apply.log', env)
    for row in LOCK['modules']:
        if sha(sources / row['path']) != row['prepared_lf_sha256']:
            raise RuntimeError('Prepared source mismatch: ' + row['module'])
    save(work/'source-receipt.json', dict(modules=LOCK['modules'], patch_sha256=sha(patch)))


def checkout(path, url, revision, work, env, name):
    path.mkdir(parents=True, exist_ok=True)
    if not (path/'.git').exists():
        run(['git', 'init'], path, work/f'logs/git-{name}-init.log', env)
        run(['git', 'remote', 'add', 'origin', url], path, work/f'logs/git-{name}-remote.log', env)
    rem = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], cwd=path, env=env, text=True).strip()
    if rem.removesuffix('.git') != url.removesuffix('.git'):
        raise RuntimeError('Unexpected git remote: ' + rem)
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=path, env=env,
                          capture_output=True, text=True)
    if head.returncode or head.stdout.strip() != revision:
        run(['git', 'fetch', '--depth', '1', 'origin', revision], path,
            work/f'logs/git-{name}-fetch.log', env)
        run(['git', '-c', 'core.autocrlf=false', 'checkout', '--detach', revision], path,
            work/f'logs/git-{name}-checkout.log', env)
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=path, env=env, text=True).strip() != revision:
        raise RuntimeError('Revision mismatch: '+name)
    # Permit untracked cache files, forbid tracked source edits.
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=path, env=env, text=True).strip():
        raise RuntimeError('Tracked checkout is modified: '+name)


def fetch_dependencies(work, env):
    mathlib = work/'mathlib'
    checkout(mathlib, **dict(url=LOCK['mathlib']['url'], revision=LOCK['mathlib']['rev']),
             work=work, env=env, name='mathlib')
    manifest = json.loads((mathlib/'lake-manifest.json').read_text(encoding='utf-8'))
    if manifest != LOCK['mathlib_manifest']:
        raise RuntimeError('Mathlib dependency manifest mismatch')
    for package in manifest['packages']:
        if package['type'] != 'git':
            raise RuntimeError('Unpinned non-git dependency')
        checkout(mathlib/'.lake/packages'/package['name'], package['url'], package['rev'],
                 work, env, package['name'])
    save(work/'dependency-receipt.json', dict(mathlib=LOCK['mathlib'], packages=manifest['packages']))


def verify_dependencies(work, env):
    manifest = json.loads((work/'mathlib/lake-manifest.json').read_text(encoding='utf-8'))
    if manifest != LOCK['mathlib_manifest']:
        raise RuntimeError('Dependency manifest changed')
    items = [(work/'mathlib', LOCK['mathlib']['rev'])] + [
        (work/'mathlib/.lake/packages'/p['name'], p['rev']) for p in manifest['packages']]
    for directory, revision in items:
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=directory, env=env, text=True).strip()
        dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'],
                                        cwd=directory, env=env, text=True).strip()
        if head != revision or dirty:
            raise RuntimeError('Dependency revision or tracked content changed: '+str(directory))


def build(work, env, lean):
    save(work/'result.json', dict(status='running'))
    sources, outputs = work/'sources', work/'lib'
    outputs.mkdir(exist_ok=True)
    paths = [outputs, work/'mathlib/.lake/build/lib/lean'] + [
        work/'mathlib/.lake/packages'/p['name']/'.lake/build/lib/lean'
        for p in LOCK['mathlib_manifest']['packages']]
    env = env.copy()
    env['LEAN_PATH'] = os.pathsep.join(map(str, paths))
    env['LEAN_NUM_THREADS'] = '1'
    save(work/'build-environment.json', dict(LEAN_PATH=env['LEAN_PATH'], LEAN_SYSROOT=env['LEAN_SYSROOT']))
    rows = {row['module']: row for row in LOCK['modules']}
    receipts, done = {}, set()
    while len(done) < len(rows):
        ready = sorted(m for m,r in rows.items() if m not in done and
                       all(i not in rows or i in done for i in r['imports']))
        if not ready:
            raise RuntimeError('Cyclic custom imports')
        for module in ready:
            row = rows[module]
            source = sources/row['path']
            if sha(source) != row['prepared_lf_sha256']:
                raise RuntimeError('Source changed: ' + module)
            output = outputs/Path(row['path']).with_suffix('.olean')
            output.parent.mkdir(parents=True, exist_ok=True)
            run([lean, '-j1', '-M4096', '-R', sources, '-o', output, source],
                work/'mathlib', work/f'logs/compile-{module}.log', env)
            receipts[module] = dict(source_sha256=sha(source), olean_sha256=sha(output), exit_code=0)
            done.add(module)
            save(work/'compiled-modules.json', receipts)
            save(work/'status.json', dict(stage='compiling', completed=len(done), total=len(rows), latest=module))
    extension = ROOT/'NoSquareSumHypothesis.lean'
    if sha(extension) != LOCK['extension_sha256']:
        raise RuntimeError('Extension source mismatch')
    run([lean, '-j1', '-M4096', '-R', ROOT, '-o', outputs/'NoSquareSumHypothesis.olean', extension],
        work/'mathlib', work/'logs/extension-axioms.log', env)
    log = (work/'logs/extension-axioms.log').read_text(encoding='utf-8')
    targets = ['JSP423Audit.ae_convergence_without_square_sum_divergence',
               'JSP423Audit.literal_statement', 'Erdos527.erdos_527']
    axioms = {}
    for name in targets:
        match = re.search(re.escape(name) + r"' depends on axioms:\s*\[([^\]]*)\]", log)
        if not match:
            raise RuntimeError('Missing axiom output for ' + name)
        values = {v.strip() for v in match[1].split(',')}
        if values != {'propext', 'Classical.choice', 'Quot.sound'}:
            raise RuntimeError('Unexpected axioms for ' + name + ': ' + repr(values))
        axioms[name] = sorted(values)
    save(work/'result.json', dict(status='passed', finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         custom_modules=len(done), extension_sha256=sha(extension),
         extension_olean_sha256=sha(outputs/'NoSquareSumHypothesis.olean'), axioms=axioms,
         compiler_sha256=sha(lean), lock_sha256=sha(ROOT/'sources.lock.json'),
         driver_sha256=sha(ROOT/'reproduce.py'),
         scope='Fresh custom compilation; official Mathlib cache; no award/novelty claim'))
    save(work/'status.json', dict(stage='passed', completed=len(done), total=len(rows)))


def main():
    global ACTIVE_WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['sources', 'dependencies', 'cache', 'build', 'all'], default='all')
    parser.add_argument('--work-dir', type=Path, default=ROOT/'_work')
    parser.add_argument('--toolchain', type=Path, help='Lean 4.33.0 installation directory; otherwise use lean on PATH')
    args = parser.parse_args()
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    ACTIVE_WORK = work
    save(work/'status.json', dict(stage=args.phase, started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    env = os.environ.copy()
    env['GIT_TERMINAL_PROMPT'] = '0'
    # Discard inherited Lean library paths: no old custom artifacts may be imported.
    env.pop('LEAN_PATH', None)
    env.pop('LEAN_SRC_PATH', None)
    if args.phase == 'sources':
        fetch_sources(work, env)
        return
    suffix = '.exe' if os.name == 'nt' else ''
    if args.toolchain:
        toolchain = args.toolchain.resolve()
    else:
        lean_on_path = shutil.which('lean')
        if not lean_on_path:
            raise RuntimeError('Install Lean 4.33.0 (elan) or pass --toolchain')
        toolchain = Path(subprocess.check_output([lean_on_path, '--print-prefix'], env=env, text=True).strip())
    lean, lake = toolchain/('bin/lean'+suffix), toolchain/('bin/lake'+suffix)
    env['PATH'] = str(toolchain/'bin') + os.pathsep + env.get('PATH', '')
    env['LEAN_SYSROOT'] = str(toolchain)
    version = subprocess.check_output([lean, '--version'], env=env, text=True).strip()
    if not re.search(r'\bversion 4\.33\.0(?:\b|,)', version):
        raise RuntimeError('Wrong compiler version: '+version)
    save(work/'toolchain-receipt.json', dict(version=version, lean_sha256=sha(lean), path=str(toolchain)))
    if args.phase in ('all', 'sources'):
        fetch_sources(work, env)
    if args.phase in ('all', 'dependencies'):
        fetch_dependencies(work, env)
    if args.phase in ('all', 'cache'):
        if not (toolchain/'include/lean/lean.h').is_file():
            raise RuntimeError('A complete Lean installation including include/lean/lean.h is required for the cache tool')
        verify_dependencies(work, env)
        run([lake, 'exe', 'cache', 'get'], work/'mathlib', work/'logs/mathlib-cache.log', env)
    if args.phase in ('all', 'build'):
        verify_dependencies(work, env)
        build(work, env, lean)


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        if ACTIVE_WORK is not None:
            save(ACTIVE_WORK/'status.json', dict(stage='failed', error=str(exc),
                 finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        raise
