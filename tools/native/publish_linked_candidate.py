"""Repack a CI-verified development engine for the Git-only Windows launcher.

Used in a separate generated build branch, never as an automatic promotion to
the player-facing main distribution. No save or unlisted artifact is included.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

if __package__:
    from .build_git_distribution import deterministic_archive, digest, CHUNK_BYTES
    from .prepare_platinum import safe_path
else:
    from build_git_distribution import deterministic_archive, digest, CHUNK_BYTES
    from prepare_platinum import safe_path


def data_at(root, name):
    root = Path(root).resolve()
    path = root.joinpath(*safe_path(name).parts)
    if not path.resolve().is_relative_to(root):
        raise ValueError('Path outside the source tree: ' + name)
    return path.read_bytes()


def pack_bytes(distribution, package):
    result = bytearray()
    for part in package['chunks']:
        data = data_at(distribution, part['path'])
        if len(data) != part['bytes'] or digest(data) != part['sha256']:
            raise ValueError('Corrupt base Git chunk: ' + part['path'])
        result.extend(data)
    if len(result) != package['bytes'] or digest(result) != package['sha256']:
        raise ValueError('Corrupt base Git package: ' + package['id'])
    return bytes(result)


def publish(source_root, candidate, output, source_sha, run_id):
    source_root, candidate, output = Path(source_root), Path(candidate), Path(output)
    if output.exists():
        raise ValueError('Output already exists')
    if len(source_sha) != 40 or any(c not in '0123456789abcdef' for c in source_sha) or int(run_id) <= 0:
        raise ValueError('Invalid source commit or CI run')
    distribution = source_root / 'distribution/windows'
    release = json.loads((distribution / 'release.json').read_text(encoding='utf-8'))
    provenance = json.loads(data_at(candidate, 'universe-port-build.json'))
    identity = json.loads(data_at(candidate, 'universe-install.json'))
    lock = json.loads(data_at(source_root, 'native/universe/port-lock.json'))
    if release['schema'] != 1 or release['platform'] != 'windows-x64':
        raise ValueError('Invalid base release')
    if provenance['engine_commit'] != lock['engine_commit'] or provenance['dependency_commits'] != lock['dependency_commits']:
        raise ValueError('The candidate engine does not match the source lock')
    if provenance['base_resource_build'] != release['build_id'] or identity['engine_variant'] != 'universe-linked-development':
        raise ValueError('The candidate does not match the base resource build')
    for name, expected in provenance['universe_sources'].items():
        if digest(data_at(source_root / 'native/universe', name).replace(b'\r\n', b'\n')) != expected:
            raise ValueError('The linked component differs from the source commit: ' + name)
    engine_names = {f['path'] for f in release['files'] if f['package'] == 'engine'}
    if set(provenance['compiled_engine_sha256']) != engine_names or identity['compiled_engine_sha256'] != provenance['compiled_engine_sha256']:
        raise ValueError('Unexpected compiled engine file list')
    packages = {p['id']: p for p in release['packages']}
    with zipfile.ZipFile(io.BytesIO(pack_bytes(distribution, packages['story']))) as archive:
        original_identity = json.loads(archive.read('universe-install.json'))
    for name, value in original_identity.items():
        if identity.get(name) != value:
            raise ValueError('The original installation identity changed: ' + name)
    groups = {'engine': {}, 'story': {}}
    records = []
    for entry in release['files']:
        name, group = entry['path'], entry['package']
        data = data_at(candidate, name)
        if group == 'engine':
            if digest(data) != provenance['compiled_engine_sha256'][name]:
                raise ValueError('Compiled engine checksum mismatch: ' + name)
        elif name != 'universe-install.json' and (len(data) != entry['bytes'] or digest(data) != entry['sha256']):
            raise ValueError('A French resource changed: ' + name)
        if group in groups:
            groups[group][name] = data
        records.append({'path': name, 'package': group, 'bytes': len(data), 'sha256': digest(data)})
    provenance['source_commit'] = source_sha
    provenance['ci_run_id'] = int(run_id)
    for name, data in {
        'universe-port-build.json': (json.dumps(provenance, indent=2) + '\n').encode(),
        'licenses/showdown.txt': data_at(source_root, 'data/SHOWDOWN-LICENSE'),
    }.items():
        if any(f['path'] == name for f in records):
            raise ValueError('Duplicate publication entry')
        groups['story'][name] = data
        records.append({'path': name, 'package': 'story', 'bytes': len(data), 'sha256': digest(data)})
    # Verify the immutable artwork package before reusing its Git objects.
    pack_bytes(distribution, packages['assets'])
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.publish-linked-', dir=output.parent))
    try:
        # Reuse only the declared artwork chunks, never extra source files.
        for part in packages['assets']['chunks']:
            target = temporary.joinpath(*safe_path(part['path']).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data_at(distribution, part['path']))
        rebuilt = {}
        for group, members in groups.items():
            folder = temporary / 'packages' / group
            folder.mkdir(parents=True)
            data = deterministic_archive(members)
            parts = []
            for number, offset in enumerate(range(0, len(data), CHUNK_BYTES)):
                chunk = data[offset:offset + CHUNK_BYTES]
                name = f'packages/{group}/{number:04d}.part'
                (temporary / name).write_bytes(chunk)
                parts.append({'path': name, 'bytes': len(chunk), 'sha256': digest(chunk)})
            rebuilt[group] = {'id': group, 'bytes': len(data), 'sha256': digest(data), 'chunks': parts}
        release['files'] = records
        release['packages'] = [rebuilt.get(p['id'], p) for p in release['packages']]
        release['engine_variant'] = 'universe-linked-development'
        release['compiled_from_commit'] = source_sha
        release['ci_run_id'] = int(run_id)
        release.pop('build_id', None)
        release['build_id'] = digest(json.dumps(release, sort_keys=True, separators=(',', ':')).encode())[:20]
        (temporary / 'release.json').write_bytes((json.dumps(release, indent=2) + '\n').encode())
        temporary.rename(output)
        return release['build_id']
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--run-id', type=int, required=True)
    args = parser.parse_args()
    print(publish(args.source_root, args.candidate, args.output, args.source_sha, args.run_id))
