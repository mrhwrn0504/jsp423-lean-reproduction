"""Check fail-closed workflow behavior using isolated temporary projects."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('jsp423_verify', Path(__file__).with_name('verify.py'))
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


class WorkflowFailureTests(unittest.TestCase):
    def test_target_mismatch_replaces_old_success_with_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'targets.json').write_text(json.dumps({'interface_targets': []}), encoding='utf-8')
            (root / 'verification.json').write_text('{"status":"passed"}', encoding='utf-8')
            original = workflow.ROOT
            workflow.ROOT = root
            try:
                with self.assertRaisesRegex(RuntimeError, 'disagree'):
                    workflow.run(root, 'retained')
            finally:
                workflow.ROOT = original
            self.assertEqual(json.loads((root / 'verification.json').read_text())['status'], 'failed')

    def test_failed_child_stage_never_reports_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = json.loads((workflow.ROOT / 'targets.json').read_text())
            (root / 'targets.json').write_text(json.dumps(manifest), encoding='utf-8')
            (root / 'check_exact.py').write_text('raise SystemExit(7)\n', encoding='utf-8')
            original = workflow.ROOT
            workflow.ROOT = root
            try:
                with self.assertRaisesRegex(RuntimeError, 'interface failed'):
                    workflow.run(root, 'compile')
            finally:
                workflow.ROOT = original
            receipt = json.loads((root / 'verification.json').read_text())
            self.assertEqual(receipt['status'], 'failed')
            self.assertEqual(receipt['stages'][0]['exit_code'], 7)


if __name__ == '__main__':
    unittest.main()
