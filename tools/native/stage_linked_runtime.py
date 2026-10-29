"""Stage a source-built development engine with verified French Git resources.

No ROM or player save is read. The released installation is not modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile

if __package__:
    from .prepare_platinum import safe_path
else:
    from prepare_platinum import safe_path

ROOT = Path(__file__).resolve().parents[2]


def verified(path, size, expected):
    data = Path(path).read_bytes()
    if len(data) != size or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Resource differs from the Git release: ' + str(path))
    return data


def stage_runtime(base, built_engine, build_manifest, output, release_path=ROOT / 'distribution/windows/release.json'):
    base, built_engine, output = Path(base).resolve(), Path(built_engine).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Candidate destination already exists: ' + str(output))
    release = json.loads(Path(release_path).read_text(encoding='utf-8'))
    provenance = json.loads(Path(build_manifest).read_text(encoding='utf-8'))
    lock = json.loads((ROOT / 'native/universe/port-lock.json').read_text(encoding='utf-8'))
    if release['schema'] != 1 or release['platform'] != 'windows-x64' or provenance['engine_commit'] != lock['engine_commit']:
        raise ValueError('Incompatible release or compiled source provenance')
    if provenance['dependency_commits'] != lock['dependency_commits']:
        raise ValueError('Compiled dependency revisions differ from the source lock')
    # Strict allowlist: source-build and old runtime folders can contain private
    # saves, logs and complete ROMs, none of which may enter this candidate.
    engine_entries = [f for f in release['files'] if f['package'] == 'engine']
    names = {f['path'] for f in engine_entries}
    required = {'main.exe', 'header.bin', 'firmware.bin', 'SDL2.dll', 'libenet-7.dll',
                'libgcc_s_seh-1.dll', 'libstdc++-6.dll', 'libwinpthread-1.dll'}
    if names != required:
        raise ValueError('Unexpected PC engine file list')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.linked-stage-', dir=output.parent))
    try:
        for entry in release['files']:
            if entry['package'] == 'engine':
                continue
            name = safe_path(entry['path'])
            source = base.joinpath(*name.parts)
            if not source.resolve().is_relative_to(base):
                raise ValueError('Resource resolves outside the verified installation')
            data = verified(source, entry['bytes'], entry['sha256'])
            target = temporary.joinpath(*name.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        engine_hashes = {}
        for name in sorted(names):
            source = built_engine / name
            if not source.resolve().is_relative_to(built_engine):
                raise ValueError('Engine file resolves outside its build folder')
            data = source.read_bytes()
            if not data:
                raise ValueError('Empty compiled engine file: ' + name)
            if name == 'main.exe':
                if data[:2] != b'MZ' or len(data) < 64:
                    raise ValueError('The compiled game is not a Windows executable')
                pe = struct.unpack_from('<I', data, 60)[0]
                if pe + 6 > len(data) or data[pe:pe + 4] != b'PE\0\0' or struct.unpack_from('<H', data, pe + 4)[0] != 0x8664:
                    raise ValueError('The compiled game is not a Windows x64 executable')
            (temporary / name).write_bytes(data)
            engine_hashes[name] = hashlib.sha256(data).hexdigest()
        identity_path = temporary / 'universe-install.json'
        identity = json.loads(identity_path.read_text(encoding='utf-8'))
        identity['engine_variant'] = 'universe-linked-development'
        identity['compiled_engine_sha256'] = engine_hashes
        identity_path.write_bytes((json.dumps(identity, indent=2) + '\n').encode('utf-8'))
        provenance['compiled_engine_sha256'] = engine_hashes
        provenance['base_resource_build'] = release['build_id']
        provenance['graphical_battle_tested'] = False
        (temporary / 'universe-port-build.json').write_bytes((json.dumps(provenance, indent=2) + '\n').encode('utf-8'))
        (temporary / 'sim_config.ini').write_bytes(release['default_config'].encode('utf-8'))
        temporary.rename(output)
        return {'candidate': str(output), 'resource_build': release['build_id'],
                'engine_variant': 'universe-linked-development', 'compiled_engine_sha256': engine_hashes}
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-runtime', type=Path, required=True)
    parser.add_argument('--built-engine', type=Path, required=True)
    parser.add_argument('--build-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage_runtime(args.base_runtime, args.built_engine, args.build_manifest, args.output), indent=2))
