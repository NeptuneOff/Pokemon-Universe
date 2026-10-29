import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from tools.native.stage_linked_runtime import ROOT, stage_runtime


class LinkedRuntimeTests(unittest.TestCase):
    def fixture(self, folder):
        base, engine = folder / 'base', folder / 'engine'
        base.mkdir()
        engine.mkdir()
        lock = json.loads((ROOT / 'native/universe/port-lock.json').read_text())
        provenance = folder / 'build.json'
        provenance.write_text(json.dumps({'engine_commit': lock['engine_commit'],
            'dependency_commits': lock['dependency_commits']}))
        names = ['main.exe', 'header.bin', 'firmware.bin', 'SDL2.dll', 'libenet-7.dll',
                 'libgcc_s_seh-1.dll', 'libstdc++-6.dll', 'libwinpthread-1.dll']
        pe = bytearray(128)
        pe[:2] = b'MZ'
        struct.pack_into('<I', pe, 60, 64)
        pe[64:68] = b'PE\0\0'
        struct.pack_into('<H', pe, 68, 0x8664)
        entries = []
        for name in names:
            (engine / name).write_bytes(pe if name == 'main.exe' else b'compiled dependency')
            entries.append({'path': name, 'package': 'engine'})
        for name, data in {'graphic/world.narc': b'French assets',
                           'universe-install.json': b'{"platform":"windows"}'}.items():
            path = base / name
            path.parent.mkdir(exist_ok=True, parents=True)
            path.write_bytes(data)
            entries.append({'path': name, 'package': 'assets', 'bytes': len(data),
                            'sha256': hashlib.sha256(data).hexdigest()})
        release = folder / 'release.json'
        release.write_text(json.dumps({'schema': 1, 'platform': 'windows-x64', 'build_id': 'fixture',
                                       'files': entries, 'default_config': '[General]\n'}))
        return base, engine, provenance, release

    def test_candidate_uses_french_assets_and_new_engine_without_private_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            base, engine, provenance, release = self.fixture(root)
            for parent in (base, engine):
                for name in ['save.bin', 'private.nds', 'debug.log', 'unrelated.txt']:
                    (parent / name).write_bytes(b'private content')
            result = stage_runtime(base, engine, provenance, root / 'candidate', release)
            candidate = root / 'candidate'
            self.assertEqual((candidate / 'graphic/world.narc').read_bytes(), b'French assets')
            self.assertEqual((candidate / 'main.exe').read_bytes(), (engine / 'main.exe').read_bytes())
            for name in ['save.bin', 'private.nds', 'debug.log', 'unrelated.txt']:
                self.assertFalse((candidate / name).exists())
                self.assertTrue((base / name).exists())
            identity = json.loads((candidate / 'universe-install.json').read_text())
            self.assertEqual(identity['engine_variant'], 'universe-linked-development')
            self.assertEqual(result['compiled_engine_sha256'], identity['compiled_engine_sha256'])
            with self.assertRaisesRegex(ValueError, 'already exists'):
                stage_runtime(base, engine, provenance, candidate, release)

    def test_bad_asset_or_executable_or_provenance_cannot_leave_a_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            base, engine, provenance, release = self.fixture(root)
            path = base / 'graphic/world.narc'
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Resource differs'):
                stage_runtime(base, engine, provenance, root / 'candidate', release)
            path.write_bytes(b'French assets')
            (engine / 'main.exe').write_bytes(b'not executable')
            with self.assertRaisesRegex(ValueError, 'Windows executable'):
                stage_runtime(base, engine, provenance, root / 'candidate', release)
            p = json.loads(provenance.read_text())
            p['engine_commit'] = '0' * 40
            provenance.write_text(json.dumps(p))
            with self.assertRaisesRegex(ValueError, 'provenance'):
                stage_runtime(base, engine, provenance, root / 'candidate', release)
            self.assertFalse((root / 'candidate').exists())
            self.assertFalse(list(root.glob('.linked-stage-*')))
