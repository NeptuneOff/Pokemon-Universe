import json
from pathlib import Path
import tempfile
import unittest

from tools.native.migrate_ci_checkpoint import migrate, SOURCE_BUILD, TARGET_SOURCE, ENGINE
from tools.native.visual_checkpoint import write_checkpoint, restore_checkpoint


class CiCheckpointMigrationTests(unittest.TestCase):
    def fixture(self, root):
        runtime, checkpoint = root / 'runtime', root / 'checkpoint'
        runtime.mkdir()
        (runtime / 'save.bin').write_bytes(b'disposable pre-starter flash')
        write_checkpoint(runtime, checkpoint, SOURCE_BUILD)
        names = ['meson.build','src/main.c','src/battle/battle_controller_player.c',
            'include/struct_defs/choose_starter_data.h','src/choose_starter/choose_starter_app.c',
            'src/scrcmd.c','src/scrcmd_party.c','src/system_vars.c','src/trainer_data.c','src/game_start.c']
        names += ['subprojects/'+n+'.wrap' for n in ('libntr','libntrsystem','libntrwifi','libntrdwc','libvct')]
        provenance = {'engine_commit': ENGINE, 'universe_sources': {'starter_port.c': 'test'},
                      'source_patches': dict.fromkeys(names, 'test')}
        return checkpoint, {'build_id': 'a'*20, 'compiled_from_commit': TARGET_SOURCE}, provenance

    def test_reviewed_upgrade_changes_only_metadata_and_restores_identical_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            checkpoint, release, provenance=self.fixture(root)
            before=(checkpoint/'save.bin').read_bytes()
            result=migrate(checkpoint,release,provenance)
            self.assertFalse(result['flash_modified'])
            self.assertEqual((checkpoint/'save.bin').read_bytes(),before)
            resumed=root/'resumed';resumed.mkdir()
            restore_checkpoint(checkpoint,resumed,'a'*20)
            self.assertEqual((resumed/'save.bin').read_bytes(),before)
            self.assertEqual(json.loads((checkpoint/'checkpoint.json').read_text())['migrated_from_build'],SOURCE_BUILD)

    def test_unknown_source_target_or_save_patch_is_refused_without_mutation(self):
        for fault in ('source','target','engine','save-header','corrupt-flash'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as folder:
                checkpoint,release,provenance=self.fixture(Path(folder))
                if fault=='source':
                    p=checkpoint/'checkpoint.json';m=json.loads(p.read_text());m['build_id']='b'*20;p.write_text(json.dumps(m))
                if fault=='target':release['compiled_from_commit']='f'*40
                if fault=='engine':provenance['engine_commit']='f'*40
                if fault=='save-header':provenance['source_patches']['include/savedata.h']='test'
                if fault=='corrupt-flash':(checkpoint/'save.bin').write_bytes(b'corrupt')
                before={p.name:p.read_bytes() for p in checkpoint.iterdir()}
                with self.assertRaises(ValueError):migrate(checkpoint,release,provenance)
                self.assertEqual(before,{p.name:p.read_bytes() for p in checkpoint.iterdir()})
