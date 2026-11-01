"""Test incremental invalidation and corrupted-artifact rejection, not mathematical proofs."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('jsp423_incremental', Path(__file__).with_name('incremental.py'))
incremental = importlib.util.module_from_spec(spec)
spec.loader.exec_module(incremental)


class IncrementalTests(unittest.TestCase):
    def test_transitive_invalidation_and_unrelated_stability(self):
        key = incremental.key_for
        context = {'compiler': 'v1'}
        a = key('A1', {}, context)
        b = key('B', {'A': {'key': a, 'output': 'outA'}}, context)
        c = key('C', {'B': {'key': b, 'output': 'outB'}}, context)
        a2 = key('A2', {}, context)
        b2 = key('B', {'A': {'key': a2, 'output': 'outA'}}, context)
        c2 = key('C', {'B': {'key': b2, 'output': 'outB'}}, context)
        self.assertNotEqual(a, a2)
        self.assertNotEqual(b, b2)
        self.assertNotEqual(c, c2)
        self.assertEqual(key('unrelated', {}, context), key('unrelated', {}, context))

    def test_context_and_output_changes_invalidate(self):
        key = incremental.key_for
        self.assertNotEqual(key('s', {}, {'compiler': '1'}), key('s', {}, {'compiler': '2'}))
        self.assertNotEqual(key('s', {'A': 'old'}, {}), key('s', {'A': 'new'}, {}))

    def test_corrupt_or_missing_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'A.olean'
            output.write_bytes(b'fixture-not-a-real-proof')
            entry = {'key': 'key', 'output_sha256': incremental.checked.digest(output)}
            self.assertTrue(incremental.usable(entry, 'key', output))
            self.assertFalse(incremental.usable(entry, 'other', output))
            output.write_bytes(b'corrupted-fixture')
            self.assertFalse(incremental.usable(entry, 'key', output))
            self.assertFalse(incremental.usable(entry, 'key', output.with_name('missing.olean')))

    def test_extra_or_missing_axiom_output_rejected(self):
        good = '\n'.join("'" + n + "' depends on axioms: [propext, Classical.choice, Quot.sound]"
                         for n in incremental.checked.TARGETS)
        self.assertEqual(set(incremental.interface_axioms(good)), set(incremental.checked.TARGETS))
        for bad in [good.replace('Quot.sound', 'unproved_assumption'), '', good + '\n' + good]:
            with self.assertRaises(RuntimeError):
                incremental.interface_axioms(bad)


if __name__ == '__main__':
    unittest.main()
