"""The downstream preparer must fail closed and leave the dependency intact."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.native.prepare_universe_port import prepare, patch_sources, replace_once


class PortSourceTests(unittest.TestCase):
    def fixture(self, base):
        engine, component = base / 'engine', base / 'component'
        engine.mkdir()
        component.mkdir()
        # Match the upstream repository's explicit LF export attributes; this
        # must not depend on the runner's global core.autocrlf setting.
        files = {'.gitattributes': '* text eol=lf\n', 'meson.build': "subdir('src')\n", 'src/main.c': 'void NitroMain(void)\n{\n}\n',
            'src/battle/battle_controller_player.c': 'void *BattleContext_New(void)\n{\n    MI_CpuClearFast(battleContext, sizeof(BattleContext));\n}\nvoid BattleContext_Free(BattleContext *battleCtx)\n{\n}\n',
            'subprojects/example.wrap': '[wrap-git]\nrevision = main\n'}
        for name, text in files.items():
            path = engine / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode())
        for command in [['git', 'init'], ['git', 'add', '.'], ['git', '-c', 'user.name=Fixture',
                '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture']]:
            subprocess.run(command, cwd=engine, check=True, capture_output=True)
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=engine, text=True).strip()
        lock = {'engine_commit': revision, 'dependency_commits': {'example': '1' * 40},
            'source_sha256': {n: hashlib.sha256(t.encode()).hexdigest() for n, t in files.items() if n.endswith(('.build', '.c'))}}
        (component / 'port-lock.json').write_text(json.dumps(lock))
        for name in ['universe.c', 'journey.c', 'port_bridge.c', 'port_bridge.h', 'entry_wrap.c', 'include/universe.h', 'generated/catalog.inc', 'generated/journey.inc']:
            path = component / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fixture\n')
        return engine, component, files, lock

    def test_isolated_build_hooks_and_original_files_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            engine, component, original, lock = self.fixture(base)
            output = base / 'copy with spaces'
            manifest = prepare(engine, output, component)
            for name, text in original.items():
                self.assertEqual((engine / name).read_bytes(), text.encode())
            self.assertIn('Universe_PortStartup', (output / 'src/main.c').read_text())
            controller = (output / 'src/battle/battle_controller_player.c').read_text()
            self.assertIn('Universe_BattleBegin', controller)
            self.assertIn('Universe_BattleEnd', controller)
            self.assertIn('--wrap=main', (output / 'meson.build').read_text())
            self.assertIn('revision = ' + '1' * 40, (output / 'subprojects/example.wrap').read_text())
            self.assertEqual(manifest['engine_commit'], lock['engine_commit'])
            with self.assertRaisesRegex(ValueError, 'already exists'):
                prepare(engine, output, component)

    def test_changed_or_ambiguous_sources_are_not_partially_patched(self):
        with tempfile.TemporaryDirectory() as folder:
            engine, _, original, lock = self.fixture(Path(folder))
            (engine / 'src/main.c').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'source changed'):
                patch_sources(engine, lock)
            self.assertEqual((engine / 'meson.build').read_text(), original['meson.build'])
            (engine / 'src/main.c').write_bytes(original['src/main.c'].encode())
            (engine / 'subprojects/example.wrap').write_bytes(b'revision = main\nrevision = main\n')
            with self.assertRaisesRegex(ValueError, 'ambiguous'):
                patch_sources(engine, lock)
            self.assertEqual((engine / 'src/main.c').read_text(), original['src/main.c'])
            with self.assertRaises(ValueError):
                replace_once('missing', 'anchor', 'replacement')

    def test_wrong_revision_or_failed_component_copy_leaves_no_installation(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            engine, component, _, lock = self.fixture(base)
            (component / 'port-lock.json').write_text(json.dumps({**lock, 'engine_commit': '0' * 40}))
            with self.assertRaisesRegex(ValueError, 'Unexpected engine'):
                prepare(engine, base / 'output', component)
            (component / 'port-lock.json').write_text(json.dumps(lock))
            (component / 'generated/catalog.inc').unlink()
            with self.assertRaises(OSError):
                prepare(engine, base / 'output', component)
            self.assertFalse((base / 'output').exists())
            self.assertFalse(list(base.glob('.port-stage-*')))
