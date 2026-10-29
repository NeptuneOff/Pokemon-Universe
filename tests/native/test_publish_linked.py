import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.native.build_git_distribution import deterministic_archive, digest
from tools.native.publish_linked_candidate import publish, pack_bytes


class PublishLinkedTests(unittest.TestCase):
    def fixture(self, root):
        source, candidate = root / 'source', root / 'candidate'
        distribution = source / 'distribution/windows'
        distribution.mkdir(parents=True)
        candidate.mkdir()
        core = source / 'native/universe'
        core.mkdir(parents=True)
        (core / 'universe.c').write_bytes(b'component source\n')
        lock = {'engine_commit': '1' * 40, 'dependency_commits': {'sdk': '2' * 40}}
        (core / 'port-lock.json').write_text(json.dumps(lock))
        (source / 'data').mkdir()
        (source / 'data/SHOWDOWN-LICENSE').write_bytes(b'MIT notice')
        identity = {'platform': 'windows', 'upstream_release': 'v0.1.12', 'resources_sha256': {'world.narc': digest(b'French pixels')}}
        names = ['main.exe', 'SDL2.dll', 'libenet-7.dll', 'libgcc_s_seh-1.dll',
                 'libstdc++-6.dll', 'libwinpthread-1.dll', 'header.bin', 'firmware.bin']
        groups = {'engine': {name: b'original ' + name.encode() for name in names},
                  'assets': {'world.narc': b'French pixels'},
                  'story': {'universe-install.json': json.dumps(identity).encode()}}
        files, packages = [], []
        for group, members in groups.items():
            data = deterministic_archive(members)
            name = 'packages/' + group + '/0000.part'
            (distribution / name).parent.mkdir(parents=True)
            (distribution / name).write_bytes(data)
            packages.append({'id': group, 'bytes': len(data), 'sha256': digest(data),
                'chunks': [{'path': name, 'bytes': len(data), 'sha256': digest(data)}]})
            for name, data in members.items():
                (candidate / name).write_bytes(data)
                files.append({'path': name, 'package': group, 'bytes': len(data), 'sha256': digest(data)})
        release = {'schema': 1, 'platform': 'windows-x64', 'build_id': 'fixture',
                   'files': files, 'packages': packages, 'default_config': '[General]\n'}
        (distribution / 'release.json').write_text(json.dumps(release))
        engine_hashes = {}
        for name in names:
            data = b'compiled ' + name.encode()
            (candidate / name).write_bytes(data)
            engine_hashes[name] = digest(data)
        identity['engine_variant'] = 'universe-linked-development'
        identity['compiled_engine_sha256'] = engine_hashes
        (candidate / 'universe-install.json').write_text(json.dumps(identity))
        provenance = {**lock, 'base_resource_build': 'fixture', 'compiled_engine_sha256': engine_hashes,
            'universe_sources': {'universe.c': digest(b'component source\n')}, 'graphical_battle_tested': False}
        (candidate / 'universe-port-build.json').write_text(json.dumps(provenance))
        (candidate / 'save.bin').write_bytes(b'private')
        (distribution / 'unlisted.nds').write_bytes(b'private')
        return source, candidate, distribution

    def test_round_trip_preserves_french_assets_credits_and_excludes_private_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, candidate, original = self.fixture(root)
            output = root / 'published'
            build_id = publish(source, candidate, output, 'a' * 40, 123)
            release = json.loads((output / 'release.json').read_text())
            self.assertEqual(build_id, release['build_id'])
            self.assertFalse((output / 'unlisted.nds').exists())
            seen = {}
            for package in release['packages']:
                with zipfile.ZipFile(io.BytesIO(pack_bytes(output, package))) as archive:
                    for name in archive.namelist():
                        seen[name] = archive.read(name)
            self.assertEqual(seen['world.narc'], b'French pixels')
            self.assertEqual(seen['main.exe'], b'compiled main.exe')
            self.assertEqual(seen['licenses/showdown.txt'], b'MIT notice')
            self.assertNotIn('save.bin', seen)
            self.assertNotIn('unlisted.nds', seen)
            self.assertEqual(json.loads(seen['universe-port-build.json'])['ci_run_id'], 123)
            for entry in release['files']:
                self.assertEqual(digest(seen[entry['path']]), entry['sha256'])
            self.assertEqual((output / 'packages/assets/0000.part').read_bytes(),
                             (original / 'packages/assets/0000.part').read_bytes())

    def test_changed_binary_or_resource_or_source_cannot_be_published(self):
        for relative, where in [('main.exe', 'candidate'), ('world.narc', 'candidate'),
                                ('native/universe/universe.c', 'source')]:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                source, candidate, _ = self.fixture(root)
                ((candidate if where == 'candidate' else source) / relative).write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    publish(source, candidate, root / 'output', 'a' * 40, 123)
                self.assertFalse((root / 'output').exists())
