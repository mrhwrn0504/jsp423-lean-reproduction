"""Regression tests for stale metadata bindings, using non-proof temporary fixtures."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('delivery_checks', Path(__file__).with_name('delivery_checks.py'))
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)


class DeliveryBindingTests(unittest.TestCase):
    def fixture(self, root):
        work = root / 'work'
        (work / 'logs').mkdir(parents=True)
        manifest = dict(upstream_target='Example.upstream', interface_targets=['Example.interface'],
                        semantic_bridge='Example.bridge', model_declarations=['Example.model'])
        (root / 'targets.json').write_text(json.dumps(manifest), encoding='utf-8')
        (work / 'exact-statement.json').write_text('{"fixture":"not-a-proof"}', encoding='utf-8')
        names = ['Example.upstream', 'Example.interface', 'Example.bridge', 'Example.model']
        manifest_hash = delivery.digest(root / 'targets.json')
        source = work / 'target-inspection' / manifest_hash / 'Targets.lean'
        source.parent.mkdir(parents=True)
        source.write_text('import ExactStatement\n' + '\n'.join('#check ' + n for n in names) + '\n', encoding='utf-8')
        log = work / 'logs/target-inspection.log'
        log.write_text('fixture output, not a Lean execution', encoding='utf-8')
        receipt = dict(status='passed', declarations=names, manifest_sha256=manifest_hash,
                       exact_receipt_sha256=delivery.digest(work / 'exact-statement.json'),
                       source_sha256=delivery.digest(source), log_sha256=delivery.digest(log))
        (work / 'target-inspection.json').write_text(json.dumps(receipt), encoding='utf-8')
        return work, source, log

    def test_later_log_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work, source, log = self.fixture(root)
            delivery.validate_inspection(work, root)
            log.write_text('changed', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'binding changed'):
                delivery.validate_inspection(work, root)

    def test_later_source_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work, source, log = self.fixture(root)
            source.write_text('import ExactStatement\n', encoding='utf-8')
            with self.assertRaises(RuntimeError):
                delivery.validate_inspection(work, root)


if __name__ == '__main__':
    unittest.main()
