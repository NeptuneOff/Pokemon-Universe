import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from tools.native.build_git_distribution import deterministic_archive, digest
from tools.native.patch_intro import crypt_message, encode_text, encrypted_messages, narc_members
from tools.native.patch_investigation import append_messages
from tools.native.publish_linked_candidate import pack_bytes
from tools.native.refresh_story import DEFINITIONS, TEXT, refresh_messages, rebuild
from test_resources import archive, message_bank


class StoryRefreshTests(unittest.TestCase):
    def definitions(self):
        old = [{'id': 'intro-1', 'bank': 0, 'message': 0, 'text': ['A']}]
        for i in range(1, 4):
            old.append({'id': 'quest-' + str(i), 'text_bank': i,
                        'messages': {'note': 'Indice ' + str(i), 'back': 'Revoir'}})
        new = copy.deepcopy(old)
        new[0].update(id='intro-2', text=['Les Méga-Gemmes résonnent.\r'])
        new[1]['messages']['note'] = 'Une pierre a réagi près du lac.'
        banks = [message_bank()] + [append_messages(message_bank(), x['messages'].values())[0] for x in old[1:]]
        return old, new, archive(banks + [b'untouched graphics'])

    def test_replaces_known_messages_without_changing_ids_or_other_banks(self):
        old, new, original = self.definitions()
        updated, changes = refresh_messages(original, old, new)
        before, _ = narc_members(original)
        after, _ = narc_members(updated)
        self.assertEqual([c['bank'] for c in changes], [0, 1])
        self.assertEqual(after[2:], before[2:])
        for i, bank in enumerate(after[:4]):
            _, messages = encrypted_messages(bank)
            _, previous = encrypted_messages(before[i])
            self.assertEqual(len(messages), len(previous))
            self.assertEqual(messages[1], previous[1])  # Native control sequence preserved.
        _, intro = encrypted_messages(after[0])
        self.assertEqual(crypt_message(intro[0], 0), encode_text(''.join(new[0]['text'])))

    def test_unknown_old_content_changed_message_ids_and_bank_moves_are_refused(self):
        for fault in ('old-content', 'message-ids', 'bank'):
            with self.subTest(fault=fault):
                old, new, original = self.definitions()
                if fault == 'old-content':
                    old[0]['text'] = ['Other']
                elif fault == 'message-ids':
                    new[1]['messages']['extra'] = 'New event'
                else:
                    new[1]['text_bank'] = 2
                with self.assertRaises(ValueError):
                    refresh_messages(original, old, new)

    def test_git_rebuild_reuses_artwork_and_engine_and_omits_unlisted_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, output = root / 'repo', root / 'output'
            repo.mkdir()
            old, new, messages = self.definitions()
            definitions = repo / 'content/native'
            definitions.mkdir(parents=True)
            for name, item in zip(DEFINITIONS, old):
                (definitions / name).write_text(json.dumps(item), encoding='utf-8')
            identity = {'resources_sha256': {TEXT: digest(messages)}}
            groups = {'engine': {'main.exe': b'engine'}, 'assets': {'art.narc': b'pixels'},
                      'story': {TEXT: messages, 'universe-install.json': json.dumps(identity).encode()}}
            distribution = repo / 'distribution/windows'
            packages, files = [], []
            for group, members in groups.items():
                data = deterministic_archive(members)
                name = 'packages/' + group + '/0000.part'
                path = distribution / name
                path.parent.mkdir(parents=True)
                path.write_bytes(data)
                packages.append({'id': group, 'bytes': len(data), 'sha256': digest(data),
                    'chunks': [{'path': name, 'bytes': len(data), 'sha256': digest(data)}]})
                files.extend({'path': n, 'package': group, 'bytes': len(d), 'sha256': digest(d)} for n, d in members.items())
            release = {'build_id': 'fixture', 'resource_count': 2, 'packages': packages, 'files': files}
            (distribution / 'release.json').write_text(json.dumps(release))
            (repo / 'save.bin').write_bytes(b'private test flash')
            (distribution / 'unlisted.nds').write_bytes(b'private test input')
            for command in [['git', 'init'], ['git', 'add', '.'], ['git', '-c', 'user.name=Fixture',
                '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Source fixture']]:
                subprocess.run(command, cwd=repo, check=True, capture_output=True)
            sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
            for name, item in zip(DEFINITIONS, new):
                (definitions / name).write_text(json.dumps(item), encoding='utf-8')
            result = rebuild(repo, sha, output)
            current = json.loads((output / 'release.json').read_text())
            self.assertEqual(current['build_id'], result['build_id'])
            self.assertNotEqual(current['build_id'], release['build_id'])
            self.assertEqual(current['resource_count'], 2)
            for package in current['packages']:
                if package['id'] != 'story':
                    self.assertEqual(package, next(p for p in packages if p['id'] == package['id']))
            seen = {}
            for package in current['packages']:
                with zipfile.ZipFile(io.BytesIO(pack_bytes(output, package))) as z:
                    seen.update({n: z.read(n) for n in z.namelist()})
            self.assertNotIn('save.bin', seen)
            self.assertFalse((output / 'unlisted.nds').exists())
            self.assertEqual(seen['main.exe'], b'engine')
            self.assertEqual(seen['art.narc'], b'pixels')
            for entry in current['files']:
                self.assertEqual(digest(seen[entry['path']]), entry['sha256'])
            self.assertEqual(json.loads(seen['universe-install.json'])['resources_sha256'][TEXT], digest(seen[TEXT]))
            with self.assertRaisesRegex(ValueError, 'already exists'):
                rebuild(repo, sha, output)
