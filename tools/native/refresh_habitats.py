"""Repack native encounter content from a verified Git revision, without a ROM.

The executable, artwork and saves are not modified. Only the encounter archive
and its installation identity may differ in the resulting Windows distribution.
"""
import argparse
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

if __package__:
    from .build_git_distribution import CHUNK_BYTES, deterministic_archive, digest
    from .patch_habitats import ARCHIVE, DEFINITION, apply_habitats
    from .prepare_platinum import ROOT, safe_path
else:
    from build_git_distribution import CHUNK_BYTES, deterministic_archive, digest
    from patch_habitats import ARCHIVE, DEFINITION, apply_habitats
    from prepare_platinum import ROOT, safe_path

IDENTITY = 'universe-install.json'


def unpack_group(release, package, read):
    """Verify chunks, the complete package and every declared member."""
    payload = bytearray()
    for part in package['chunks']:
        safe_path(part['path'])
        chunk = read(part['path'])
        if len(chunk) != part['bytes'] or digest(chunk) != part['sha256']:
            raise ValueError('Corrupt habitat source chunk: ' + part['path'])
        payload.extend(chunk)
    if len(payload) != package['bytes'] or digest(payload) != package['sha256']:
        raise ValueError('Corrupt habitat source package')
    expected = {f['path']: f for f in release['files'] if f['package'] == package['id']}
    result = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())) or set(archive.namelist()) != set(expected):
            raise ValueError('Unexpected habitat source files')
        for entry in archive.infolist():
            name = entry.filename
            safe_path(name)
            if entry.is_dir() or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsupported habitat source entry')
            data = archive.read(entry)
            if len(data) != expected[name]['bytes'] or digest(data) != expected[name]['sha256']:
                raise ValueError('Habitat source file differs: ' + name)
            result[name] = data
    return result


def rebuild(repo, base_ref, output):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    if not re.fullmatch('[0-9a-f]{40}', base_ref):
        raise ValueError('Use an immutable habitat source revision')
    if output.exists():
        raise ValueError('Habitat output already exists')

    def at(path):
        safe_path(path)
        return subprocess.check_output(['git', '-C', str(repo), 'show', base_ref + ':' + path])

    def part(path):
        return at('distribution/windows/' + path)

    release = json.loads(at('distribution/windows/release.json'))
    if release.get('schema') != 1 or release.get('platform') != 'windows-x64':
        raise ValueError('Invalid Windows habitat base')
    packages = {p['id']: p for p in release['packages']}
    if set(packages) != {'engine', 'assets', 'story'} or len(packages) != len(release['packages']):
        raise ValueError('Unexpected habitat base packages')
    names = [f['path'].casefold() for f in release['files']]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate Windows habitat source paths')
    groups = {name: unpack_group(release, package, part) for name, package in packages.items()}
    raw_definition = (repo / DEFINITION).read_bytes().replace(b'\r\n', b'\n')
    definition = json.loads(raw_definition)
    source = groups['assets'][ARCHIVE]
    identity = json.loads(groups['story'][IDENTITY])
    if identity['resources_sha256'][ARCHIVE] != digest(source):
        raise ValueError('Source habitat installation identity differs')
    updated, provenance = apply_habitats(source, definition)
    if updated == source:
        if identity.get('universe_habitats', {}).get('definition_sha256') != digest(raw_definition):
            raise ValueError('An already modified habitat lacks matching provenance')
    else:
        groups['assets'][ARCHIVE] = updated
        identity['resources_sha256'][ARCHIVE] = digest(updated)
        provenance.update(base_commit=base_ref, base_build=release['build_id'], definition_sha256=digest(raw_definition))
        identity['universe_habitats'] = provenance
        groups['story'][IDENTITY] = (json.dumps(identity, indent=2) + '\n').encode()
        release['habitats_id'] = definition['id']
        release['habitats_source_commit'] = base_ref
        for entry in release['files']:
            if entry['path'] in (ARCHIVE, IDENTITY):
                data = groups[entry['package']][entry['path']]
                entry.update(bytes=len(data), sha256=digest(data))
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.habitat-refresh-', dir=output.parent))
    try:
        for package in release['packages']:
            group = package['id']
            if group == 'engine' or updated == source:
                # These objects have already passed complete package verification.
                for item in package['chunks']:
                    target = stage.joinpath(*safe_path(item['path']).parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(part(item['path']))
                continue
            data = deterministic_archive(groups[group])
            chunks = []
            for number, offset in enumerate(range(0, len(data), CHUNK_BYTES)):
                chunk = data[offset:offset + CHUNK_BYTES]
                name = f'packages/{group}/{number:04d}.part'
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(chunk)
                chunks.append({'path': name, 'bytes': len(chunk), 'sha256': digest(chunk)})
            package.update(bytes=len(data), sha256=digest(data), chunks=chunks)
        if updated != source:
            release.pop('build_id', None)
            release['build_id'] = digest(json.dumps(release, sort_keys=True, separators=(',', ':')).encode())[:20]
        (stage / 'release.json').write_text(json.dumps(release, indent=2) + '\n', encoding='utf-8')
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {'build_id': release['build_id'], 'habitats_id': definition['id'],
            'changed': updated != source, 'areas': provenance['areas'],
            'source_archive': digest(source), 'patched_archive': digest(updated)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--base-ref', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(rebuild(args.repo, args.base_ref, args.output), indent=2))
