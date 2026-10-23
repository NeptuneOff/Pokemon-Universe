"""Protect actual save bytes across successful and failed game launches."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.native.launch_platinum import backup_save, launch


class LauncherTests(unittest.TestCase):
    def runtime(self, root):
        platform = 'windows' if os.name == 'nt' else 'linux'
        (root / 'universe-install.json').write_text(json.dumps({
            'platform': platform, 'french_banks': {'text.narc': 1},
        }))
        (root / 'text.narc').write_bytes(b'resource')
        executable = root / ('main.exe' if platform == 'windows' else 'pokeplatinum.AppImage')
        executable.touch()
        return executable

    def test_new_game_does_not_require_a_save(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.runtime(root)
            with patch('tools.native.launch_platinum.subprocess.call', return_value=0):
                self.assertEqual(launch(root), 0)
            self.assertFalse((root / 'save.bin').exists())
            self.assertFalse((root / 'universe-backups').exists())

    def test_old_and_new_progress_survive_even_if_game_returns_an_error(self):
        for exit_code in (0, 1):
            with self.subTest(exit_code=exit_code), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                executable = self.runtime(root)
                save = root / 'save.bin'
                save.write_bytes(b'previous progress')

                def game(command, *, cwd, env):
                    self.assertEqual(len(command), 1)
                    self.assertTrue(Path(command[0]).samefile(executable))
                    self.assertTrue(Path(cwd).samefile(root))
                    self.assertEqual({p.read_bytes() for p in (root / 'universe-backups').glob('*.sav')},
                                     {b'previous progress'})
                    save.write_bytes(b'new progress')
                    return exit_code

                with patch('tools.native.launch_platinum.subprocess.call', side_effect=game):
                    self.assertEqual(launch(root), exit_code)
                self.assertEqual(save.read_bytes(), b'new progress')
                self.assertEqual({p.read_bytes() for p in (root / 'universe-backups').glob('*.sav')},
                                 {b'previous progress', b'new progress'})
                backup_save(root)
                self.assertEqual(len(list((root / 'universe-backups').iterdir())), 2)

    def test_failed_backup_prevents_launch_without_touching_save(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.runtime(root)
            save = root / 'save.bin'
            save.write_bytes(b'valuable progress')
            with patch('tools.native.launch_platinum.os.replace', side_effect=OSError('disk full')), \
                    patch('tools.native.launch_platinum.subprocess.call') as game:
                with self.assertRaises(OSError):
                    launch(root)
                game.assert_not_called()
            self.assertEqual(save.read_bytes(), b'valuable progress')
            self.assertEqual(list((root / 'universe-backups').iterdir()), [])

    def test_corrupt_backup_is_reported_and_original_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            save = root / 'save.bin'
            save.write_bytes(b'valuable progress')
            backup_save(root).write_bytes(b'truncated')
            with self.assertRaisesRegex(ValueError, 'altérée'):
                backup_save(root)
            self.assertEqual(save.read_bytes(), b'valuable progress')


if __name__ == '__main__':
    unittest.main()
