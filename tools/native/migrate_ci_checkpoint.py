"""One reviewed migration of a disposable CI flash, never player installations.

The original bytes remain unchanged. Only the checkpoint's build binding moves
between these two exact source builds, which retain Platinum's save layout.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tempfile
import zipfile

if __package__:
    from .publish_linked_candidate import pack_bytes
    from .visual_checkpoint import restore_checkpoint
else:
    from publish_linked_candidate import pack_bytes
    from visual_checkpoint import restore_checkpoint

SOURCE_BUILD = '470ee0957a354a38f9bd'
TARGET_SOURCE = '7bd2e2e0f7eae6dcc6177a7c78987e5f7ab094a9'
ENGINE = '35067868f64f23d25d17ac3e536cfdd9a7f40523'


def migrate(checkpoint, release, provenance):
    checkpoint = Path(checkpoint)
    manifest = json.loads((checkpoint / 'checkpoint.json').read_text(encoding='utf-8'))
    if manifest.get('build_id') != SOURCE_BUILD or release.get('compiled_from_commit') != TARGET_SOURCE or provenance.get('engine_commit') != ENGINE:
        raise ValueError('This checkpoint migration has not been reviewed for these exact builds')
    if 'starter_port.c' not in provenance.get('universe_sources', {}):
        raise ValueError('The target is not the reviewed native starter integration')
    # The engine pin is unchanged; this patch only consumes unused VarsFlags.
    # No serialization/party/box/save headers or SPI libraries are patched.
    allowed = {'meson.build','src/main.c','src/battle/battle_controller_player.c',
        'include/struct_defs/choose_starter_data.h','src/choose_starter/choose_starter_app.c',
        'src/scrcmd.c','src/scrcmd_party.c','src/system_vars.c','src/trainer_data.c','src/game_start.c',
        *('subprojects/' + name + '.wrap' for name in ('libntr','libntrsystem','libntrwifi','libntrdwc','libvct'))}
    if set(provenance.get('source_patches', {})) != allowed:
        raise ValueError('The target has unreviewed source changes')
    if not isinstance(release.get('build_id'), str) or len(release['build_id']) != 20:
        raise ValueError('Invalid target build')
    with tempfile.TemporaryDirectory(prefix='universe-ci-save-check-') as folder:
        restore_checkpoint(checkpoint, Path(folder), SOURCE_BUILD)
    before = hashlib.sha256((checkpoint / 'save.bin').read_bytes()).hexdigest()
    manifest['migrated_from_build'] = SOURCE_BUILD
    manifest['migration_reason'] = 'Reviewed unchanged engine/save layout; five previously unused native variables for starter options.'
    manifest['build_id'] = release['build_id']
    (checkpoint / 'checkpoint.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    assert hashlib.sha256((checkpoint / 'save.bin').read_bytes()).hexdigest() == before
    return {'source_build': SOURCE_BUILD, 'target_build': release['build_id'], 'flash_sha256': before, 'flash_modified': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint', required=True, type=Path)
    p.add_argument('--distribution', required=True, type=Path)
    a = p.parse_args()
    release = json.loads((a.distribution / 'release.json').read_text(encoding='utf-8'))
    story = next(v for v in release['packages'] if v['id'] == 'story')
    with zipfile.ZipFile(io.BytesIO(pack_bytes(a.distribution, story))) as archive:
        raw = archive.read('universe-port-build.json')
    record = next(v for v in release['files'] if v['path'] == 'universe-port-build.json')
    if len(raw) != record['bytes'] or hashlib.sha256(raw).hexdigest() != record['sha256']:
        raise ValueError('Unverified target provenance')
    print(json.dumps(migrate(a.checkpoint, release, json.loads(raw))))
