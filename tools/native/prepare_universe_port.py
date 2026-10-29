"""Prepare a private downstream PC source build with Universe linked in.

The pinned engine submodule, player installation and saves are never edited.
This is a developer/CI tool, not part of JOUER.bat.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
INCLUDE = '\n#ifdef SDK_PORT\n#include "universe_native/port_bridge.h"\n#endif\n'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Source anchor is absent or ambiguous: ' + old[:80])
    return text.replace(old, new, 1)


def patch_sources(folder, lock):
    folder = Path(folder)
    original = {}
    for name, expected in lock['source_sha256'].items():
        data = (folder / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Pinned engine source changed: ' + name)
        original[name] = data.decode('utf-8')
    meson = replace_once(original['meson.build'], "subdir('src')\n", "subdir('src')\n\n" + """# Universe downstream PC integration; DS and console targets are unchanged.
if build_target == 'linux' or build_target == 'win64'
    pokeplatinum_c += files('universe_native/universe.c',
                            'universe_native/port_bridge.c',
                            'universe_native/entry_wrap.c')
    link_args += ['-Wl,--wrap=main']
endif
""")
    main = INCLUDE + replace_once(original['src/main.c'], 'void NitroMain(void)\n{',
        'void NitroMain(void)\n{\n#ifdef SDK_PORT\n    Universe_PortStartup();\n#endif')
    controller = INCLUDE + replace_once(original['src/battle/battle_controller_player.c'],
        '    MI_CpuClearFast(battleContext, sizeof(BattleContext));',
        '    MI_CpuClearFast(battleContext, sizeof(BattleContext));\n#ifdef SDK_PORT\n    Universe_BattleBegin(battleContext);\n#endif')
    controller = replace_once(controller, 'void BattleContext_Free(BattleContext *battleCtx)\n{',
        'void BattleContext_Free(BattleContext *battleCtx)\n{\n#ifdef SDK_PORT\n    Universe_BattleEnd(battleCtx);\n#endif')
    patched = {'meson.build': meson, 'src/main.c': main,
               'src/battle/battle_controller_player.c': controller}
    # Validate all dependency declarations before writing any file.
    for name, revision in lock['dependency_commits'].items():
        path = 'subprojects/' + name + '.wrap'
        text = (folder / path).read_text(encoding='utf-8')
        patched[path] = replace_once(text, 'revision = main', 'revision = ' + revision)
    for name, text in patched.items():
        (folder / name).write_bytes(text.encode('utf-8'))
    return {name: hashlib.sha256(text.encode('utf-8')).hexdigest() for name, text in patched.items()}


def prepare(engine, output, component=ROOT / 'native/universe'):
    engine, output, component = Path(engine).resolve(), Path(output).resolve(), Path(component).resolve()
    lock = json.loads((component / 'port-lock.json').read_text(encoding='utf-8'))
    if output.exists():
        raise ValueError('Build folder already exists: ' + str(output))
    revision = subprocess.check_output(['git', '-C', str(engine), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != lock['engine_commit']:
        raise ValueError('Unexpected engine commit: ' + revision)
    subprocess.run(['git', '-C', str(engine), 'diff', '--exit-code', 'HEAD', '--'], check=True, capture_output=True)
    archive = subprocess.check_output(['git', '-C', str(engine), 'archive', '--format=tar', revision])
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.port-stage-', dir=output.parent))
    try:
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(stage, filter='data')
        changed = patch_sources(stage, lock)
        files = ['universe.c', 'port_bridge.c', 'port_bridge.h', 'entry_wrap.c',
                 'include/universe.h', 'generated/catalog.inc']
        component_hashes = {}
        for name in files:
            target = stage / 'universe_native' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            data = (component / name).read_bytes().replace(b'\r\n', b'\n')
            target.write_bytes(data)
            component_hashes[name] = hashlib.sha256(data).hexdigest()
        manifest = {'schema': 1, 'engine_commit': revision,
                    'dependency_commits': lock['dependency_commits'], 'source_patches': changed,
                    'universe_sources': component_hashes, 'status': 'source-prepared-not-graphically-validated'}
        (stage / 'universe-port-build.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode())
        stage.rename(output)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, default=ROOT / 'engine/platinum')
    parser.add_argument('--output', type=Path, default=ROOT / 'native-runtime/universe-port')
    args = parser.parse_args()
    print(json.dumps(prepare(args.engine, args.output), indent=2))
