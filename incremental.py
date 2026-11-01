"""Build the fixed custom closure in a separate content-validated incremental store."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('jsp423_check', ROOT / 'check_exact.py')
checked = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checked)


def key_for(source_hash, dependencies, context):
    value = dict(source=source_hash, dependencies=dependencies, context=context)
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def usable(entry, key, output):
    return bool(entry and entry.get('key') == key and output.is_file()
                and checked.digest(output) == entry.get('output_sha256'))


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def interface_axioms(text):
    axioms = {}
    for target in checked.TARGETS:
        matches = re.findall(re.escape(target) + r"' depends on axioms:\s*\[([^\]]*)\]", text)
        values = {v.strip() for v in matches[0].split(',')} if len(matches) == 1 else set()
        if values != {'propext', 'Classical.choice', 'Quot.sound'}:
            raise RuntimeError('Incremental interface axiom audit failed: ' + target)
        axioms[target] = sorted(values)
    return axioms


def main(work, store, source_tree, force, no_seed=False):
    store.mkdir(parents=True, exist_ok=True)
    (store / 'logs').mkdir(exist_ok=True)
    report = store / 'result.json'
    started = time.perf_counter()
    save(report, dict(status='running'))
    try:
        checked.audit(work)
        checked.validate_exact(work)
        settings = json.loads((work / 'build-environment.json').read_text(encoding='utf-8'))
        compiler = Path(settings['LEAN_SYSROOT']) / 'bin' / ('lean.exe' if os.name == 'nt' else 'lean')
        before = checked.input_fingerprints(work, compiler)
        driver_hash = checked.digest(Path(__file__))
        lock = json.loads((ROOT / 'sources.lock.json').read_text(encoding='utf-8'))
        baseline = json.loads((work / 'compiled-modules.json').read_text(encoding='utf-8'))
        exact = checked.validate_exact(work)
        rows = {row['module']: dict(row, source=source_tree / row['path']) for row in lock['modules']}
        rows['ExactStatement'] = dict(path='ExactStatement.lean', source=ROOT / 'ExactStatement.lean',
                                      prepared_lf_sha256=exact['source_sha256'])
        for name, row in rows.items():
            text = row['source'].read_text(encoding='utf-8')
            imports = re.findall(r'^\s*import\s+([A-Za-z_][\w.]*)\s*$', text, re.MULTILINE)
            if not imports:
                raise RuntimeError('Cannot identify imports: ' + name)
            unknown = [m for m in imports if (m.startswith('ErdosProblems.') or m.startswith('BoundedGaps.')) and m not in rows]
            if unknown:
                raise RuntimeError('Unsupported custom imports: ' + repr(unknown))
            row['dependencies'] = sorted(m for m in imports if m in rows)
            row['source_sha256'] = checked.digest(row['source'])
        cache_file = store / 'cache.json'
        cache = json.loads(cache_file.read_text(encoding='utf-8')) if cache_file.exists() else {}
        context = dict(driver=driver_hash, compiler=checked.digest(compiler),
                       lock=checked.digest(ROOT / 'sources.lock.json'),
                       base_result=checked.digest(work / 'result.json'), options=['-j1', '-M4096'])
        env = os.environ.copy()
        env.update(settings)
        env['PATH'] = str(compiler.parent) + os.pathsep + env.get('PATH', '')
        env['LEAN_NUM_THREADS'] = '1'
        env['LEAN_PATH'] = os.pathsep.join([str(store / 'lib'), *settings['LEAN_PATH'].split(os.pathsep)[1:]])
        done = {}
        while len(done) < len(rows):
            ready = sorted(n for n, r in rows.items() if n not in done and all(d in done for d in r['dependencies']))
            if not ready:
                raise RuntimeError('Custom import cycle')
            for name in ready:
                row = rows[name]
                dependencies = {d: dict(key=done[d]['key'], output=done[d]['output_sha256']) for d in row['dependencies']}
                key = key_for(row['source_sha256'], dependencies, context)
                output = store / 'lib' / Path(row['path']).with_suffix('.olean')
                output.parent.mkdir(parents=True, exist_ok=True)
                begin = time.perf_counter()
                origin = 'compiled'
                cached = cache.get(name)
                evidence = (cached or {}).get('compilation', {})
                evidence_valid = True
                if evidence.get('origin') == 'lean-execution':
                    old_log = store / 'logs' / (name + '.log')
                    evidence_valid = old_log.is_file() and checked.digest(old_log) == evidence.get('log_sha256')
                if not force and evidence_valid and usable(cached, key, output):
                    origin = 'cache-hit'
                else:
                    seed_hash = exact['olean_sha256'] if name == 'ExactStatement' else baseline[name]['olean_sha256']
                    seed = work / 'lib' / Path(row['path']).with_suffix('.olean')
                    deps_original = all(done[d]['output_sha256'] == baseline[d]['olean_sha256']
                                        for d in row['dependencies'])
                    can_seed = row['source_sha256'] == row['prepared_lf_sha256'] and deps_original
                    if not force and not no_seed and can_seed and checked.digest(seed) == seed_hash:
                        shutil.copyfile(seed, output)
                        origin = 'seeded-from-audited-base'
                        evidence = dict(origin='audited-base', baseline_result=context['base_result'])
                    else:
                        snapshot_root = store / 'inputs' / key
                        snapshot = snapshot_root / row['path']
                        snapshot.parent.mkdir(parents=True, exist_ok=True)
                        snapshot.write_bytes(row['source'].read_bytes())
                        if checked.digest(snapshot) != row['source_sha256']:
                            raise RuntimeError('Source changed before compilation: ' + name)
                        log = store / 'logs' / (name + '.log')
                        command = [str(compiler), '-j1', '-M4096', '-R', str(snapshot_root), '-o', str(output), str(snapshot)]
                        with log.open('w', encoding='utf-8') as stream:
                            code = subprocess.run(command, cwd=work / 'mathlib', env=env,
                                                  stdout=stream, stderr=subprocess.STDOUT).returncode
                        if code:
                            raise RuntimeError(f'Lean exit {code}: {name}; {log}')
                        if checked.digest(snapshot) != row['source_sha256']:
                            raise RuntimeError('Snapshot changed during compilation: ' + name)
                        evidence = dict(origin='lean-execution', command=command, exit_code=code,
                                        log_sha256=checked.digest(log), snapshot=str(snapshot))
                if checked.digest(row['source']) != row['source_sha256']:
                    raise RuntimeError('Source changed during run: ' + name)
                entry = dict(key=key, source_sha256=row['source_sha256'],
                             output_sha256=checked.digest(output), dependencies=dependencies,
                             compilation=evidence)
                cache[name] = entry
                done[name] = dict(entry, mode=origin, seconds=time.perf_counter() - begin,
                                  modified_source=row['source_sha256'] != row['prepared_lf_sha256'])
                save(cache_file, cache)
                save(store / 'progress.json', dict(completed=len(done), total=len(rows), latest=name))
        checked.require_unchanged(before, checked.input_fingerprints(work, compiler))
        if checked.digest(Path(__file__)) != driver_hash:
            raise RuntimeError('Incremental driver changed during run')
        for name, entry in done.items():
            output = store / 'lib' / Path(rows[name]['path']).with_suffix('.olean')
            if checked.digest(output) != entry['output_sha256'] or checked.digest(rows[name]['source']) != entry['source_sha256']:
                raise RuntimeError('Final input/output changed: ' + name)
        interface_entry = done['ExactStatement']['compilation']
        interface_log = (store / 'logs/ExactStatement.log' if interface_entry['origin'] == 'lean-execution'
                         else work / 'logs/exact-statement.log')
        axioms = interface_axioms(interface_log.read_text(encoding='utf-8'))
        counts = {m: sum(e['mode'] == m for e in done.values()) for m in ['compiled', 'cache-hit', 'seeded-from-audited-base']}
        data = dict(status='passed', finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    seconds=time.perf_counter() - started, modules=done, counts=counts,
                    driver_sha256=driver_hash, context=context,
                    interface_axioms=axioms, interface_log_sha256=checked.digest(interface_log),
                    scope='Separate incremental artifacts; baseline fresh-build evidence is unchanged; Mathlib imports retain the baseline trust boundary')
        save(report, data)
        print(json.dumps(dict(status='passed', seconds=data['seconds'], counts=counts)))
    except Exception as exc:
        save(report, dict(status='failed', error=str(exc)))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, default=ROOT / '_work')
    parser.add_argument('--store', type=Path, default=ROOT / '_incremental')
    parser.add_argument('--source-tree', type=Path, help='Optional edited custom source tree; original baseline is never overwritten')
    parser.add_argument('--force', action='store_true', help='Compile all targets instead of using cache or audited base artifacts')
    parser.add_argument('--no-seed', action='store_true', help='Use valid cache hits, but rebuild misses rather than seeding from the audited base')
    args = parser.parse_args()
    work = args.work_dir.resolve()
    main(work, args.store.resolve(), args.source_tree.resolve() if args.source_tree else work / 'sources', args.force, args.no_seed)
