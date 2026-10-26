"""An installation manifest must not hide altered or missing game resources."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.native.verify_resources import verify


class VerificationTests(unittest.TestCase):
    def test_reports_missing_and_changed_even_with_a_forged_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'good.narc').write_bytes(b'original')
            (root / 'changed.narc').write_bytes(b'wrong texture')
            (root / 'save.bin').write_bytes(b'player progress')
            (root / 'universe-install.json').write_text('{"resources_sha256": {}}')
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            with patch('tools.native.verify_resources.read_rom', return_value=b''), \
                    patch('tools.native.verify_resources.nitro_files', return_value={
                        'good.narc': b'original', 'changed.narc': b'original',
                        'missing.narc': b'original'}), \
                    patch('tools.native.verify_resources.french_resources', return_value=({}, {}, {})):
                report = verify(root, 'us', 'fr', vanilla=True)
            self.assertFalse(report['ok'])
            self.assertEqual(report['matching_resources'], 1)
            self.assertEqual(report['changed'], ['changed.narc'])
            self.assertEqual(report['missing'], ['missing.narc'])
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})

    def test_accepts_expected_french_and_universe_overrides(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'graphic').mkdir()
            (root / 'msgdata').mkdir()
            (root / 'graphic/ui.narc').write_bytes(b'French buttons')
            (root / 'msgdata/pl_msg.narc').write_bytes(b'Universe intro')
            with patch('tools.native.verify_resources.read_rom', return_value=b''), \
                    patch('tools.native.verify_resources.nitro_files', return_value={
                        'graphic/ui.narc': b'original', 'msgdata/pl_msg.narc': b'original'}), \
                    patch('tools.native.verify_resources.french_resources', return_value=(
                        {'graphic/ui.narc': b'French buttons'}, {}, {'graphic/ui.narc': {}})), \
                    patch('tools.native.verify_resources.apply_intro', return_value=(b'Universe intro', {})):
                report = verify(root, 'us', 'fr', intro_only=True)
            self.assertTrue(report['ok'])
            self.assertEqual(report['matching_resources'], 2)
            self.assertEqual(report['french_graphics'], 1)


if __name__ == '__main__':
    unittest.main()
