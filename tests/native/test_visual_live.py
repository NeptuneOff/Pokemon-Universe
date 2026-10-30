import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.native.visual_live import decode_batch, publish_evidence, git


class VisualLiveTests(unittest.TestCase):
    def test_other_sessions_and_replayed_sequences_are_ignored(self):
        self.assertIsNone(decode_batch({'run_id': 99}, 123, 0))
        payload = {'run_id': 123, 'sequence': 4, 'steps': [{'key': 'z'}]}
        self.assertIsNone(decode_batch(payload, 123, 4))
        self.assertEqual(decode_batch(payload, 123, 3),
                         {'sequence': 4, 'steps': [{'key': 'z'}], 'finish': False})
        self.assertTrue(decode_batch({**payload, 'finish': True}, 123, 3)['finish'])

    def test_malformed_batches_are_refused(self):
        for extra in ({'sequence': True}, {'sequence': 0}, {'steps': 'z'},
                      {'steps': ['z']}, {'steps': [{}] * 151}, {'finish': 'yes'}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                decode_batch({'run_id': 123, 'sequence': 1, **extra}, 123, 0)

    def test_git_evidence_does_not_change_the_source_index_or_publish_flash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote, repo = root / 'remote.git', root / 'source'
            subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
            repo.mkdir()
            git(repo, 'init')
            git(repo, 'config', 'user.name', 'Fixture')
            git(repo, 'config', 'user.email', 'fixture@example.invalid')
            git(repo, 'remote', 'add', 'origin', str(remote))
            (repo / 'source.txt').write_text('unchanged source\n')
            git(repo, 'add', 'source.txt')
            git(repo, 'commit', '-m', 'Source fixture')
            original_index = git(repo, 'write-tree')
            evidence = repo / 'native-runtime/qa/evidence'
            evidence.mkdir(parents=True)
            (evidence / 'report.json').write_text(json.dumps({'phase': 'waiting'}))
            (evidence / 'capture.png').write_bytes(b'fixture-image')
            (evidence / 'save.bin').write_bytes(b'private flash')
            first = publish_evidence(repo, evidence, 123, 0)
            files = git(repo, 'ls-tree', '-r', '--name-only', first).splitlines()
            self.assertEqual(files, ['docs/evidence/linked-port-123/capture.png',
                                     'docs/evidence/linked-port-123/report.json'])
            self.assertEqual(git(repo, 'write-tree'), original_index)
            self.assertEqual((repo / 'source.txt').read_text(), 'unchanged source\n')
            (evidence / 'report.json').write_text(json.dumps({'phase': 'finished'}))
            second = publish_evidence(repo, evidence, 123, 1)
            self.assertEqual(git(repo, 'rev-parse', second + '^'), first)
            self.assertEqual(git(repo, 'write-tree'), original_index)
