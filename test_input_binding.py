"""Negative tests for receipt input binding; no proof sources are modified."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

spec = importlib.util.spec_from_file_location('jsp423_check', Path(__file__).with_name('check_exact.py'))
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class InputBindingTests(unittest.TestCase):
    def test_unchanged_accepted(self):
        checker.require_unchanged({'source': 'a', 'compiler': 'b'}, {'source': 'a', 'compiler': 'b'})

    def test_changed_inputs_rejected(self):
        for name in ['source', 'compiler', 'custom_import', 'environment']:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / name
                path.write_bytes(b'before')
                before = {str(path): checker.digest(path)}
                path.write_bytes(b'after')
                after = {str(path): checker.digest(path)}
                with self.assertRaisesRegex(RuntimeError, 'inputs changed'):
                    checker.require_unchanged(before, after)

    def test_missing_or_extra_input_rejected(self):
        for after in [{}, {'source': 'a', 'extra': 'b'}]:
            with self.assertRaises(RuntimeError):
                checker.require_unchanged({'source': 'a'}, after)

    def test_child_process_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.lean'
            path.write_bytes(b'before')
            before = {str(path): checker.digest(path)}
            subprocess.run([sys.executable, '-I', '-c',
                            'from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(b"changed")',
                            str(path)], check=True)
            with self.assertRaisesRegex(RuntimeError, 'inputs changed'):
                checker.require_unchanged(before, {str(path): checker.digest(path)})


if __name__ == '__main__':
    unittest.main()
