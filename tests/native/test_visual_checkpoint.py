import json
from pathlib import Path
import tempfile
import unittest

from tools.native.visual_checkpoint import write_checkpoint, restore_checkpoint, read_plan


class VisualCheckpointTests(unittest.TestCase):
    def test_resume_plan_requires_a_fixed_candidate_and_a_valid_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'plan.json'
            config.write_text(json.dumps({'run_id': 0}))
            self.assertEqual(read_plan(config), {'run_id': 0, 'candidate_ref': 'builds/windows-linked', 'live_seconds': 0})
            config.write_text(json.dumps({'run_id': 123, 'candidate_ref': 'a' * 40}))
            self.assertEqual(read_plan(config)['candidate_ref'], 'a' * 40)
            for invalid in ({'run_id': True}, {'run_id': -1}, {'run_id': 123},
                            {'run_id': 123, 'candidate_ref': 'main'},
                            {'run_id': 0, 'candidate_ref': 'untrusted-ref'},
                            {'run_id': 0, 'live_seconds': 1201}, {'run_id': 0, 'live_seconds': True}):
                config.write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):
                    read_plan(config)

    def test_only_disposable_flash_is_retained_and_can_resume_the_same_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime, resumed, checkpoint = root / 'runtime', root / 'resumed', root / 'checkpoint'
            runtime.mkdir()
            resumed.mkdir()
            (runtime / 'save.bin').write_bytes(b'disposable test flash')
            (runtime / 'unlisted.nds').write_bytes(b'private')
            (runtime / 'game.log').write_bytes(b'private')
            self.assertTrue(write_checkpoint(runtime, checkpoint, 'build-one'))
            self.assertEqual({p.name for p in checkpoint.iterdir()}, {'checkpoint.json', 'save.bin'})
            self.assertFalse(json.loads((checkpoint / 'checkpoint.json').read_text())['game_save_validated'])
            restore_checkpoint(checkpoint, resumed, 'build-one')
            self.assertEqual((resumed / 'save.bin').read_bytes(), b'disposable test flash')
            self.assertEqual((runtime / 'save.bin').read_bytes(), b'disposable test flash')
            with self.assertRaisesRegex(ValueError, 'overwrite'):
                restore_checkpoint(checkpoint, resumed, 'build-one')

    def test_wrong_build_changed_flash_and_extra_files_are_refused(self):
        for fault in ('wrong-build', 'changed-flash', 'extra-file'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                runtime, resumed, checkpoint = root / 'runtime', root / 'resumed', root / 'checkpoint'
                runtime.mkdir()
                resumed.mkdir()
                (runtime / 'save.bin').write_bytes(b'disposable test flash')
                write_checkpoint(runtime, checkpoint, 'build-one')
                if fault == 'changed-flash':
                    (checkpoint / 'save.bin').write_bytes(b'changed')
                if fault == 'extra-file':
                    (checkpoint / 'unexpected').write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    restore_checkpoint(checkpoint, resumed, 'other' if fault == 'wrong-build' else 'build-one')
                self.assertFalse((resumed / 'save.bin').exists())

    def test_missing_or_empty_flash_is_not_a_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(write_checkpoint(root, root / 'checkpoint', 'build-one'))
            (root / 'save.bin').write_bytes(b'')
            self.assertFalse(write_checkpoint(root, root / 'checkpoint', 'build-one'))
            self.assertFalse((root / 'checkpoint').exists())
