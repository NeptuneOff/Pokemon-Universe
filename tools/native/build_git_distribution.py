"""Build deterministic, chunked Windows packages consumed directly from Git.

The developer prepares and verifies resources once. Players need only Git and
the Windows launcher; no ROM, Python, external download or LFS is required.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

if __package__:
    from .prepare_platinum import ROOT, PACKAGES, RELEASE, safe_path
else:
    from prepare_platinum import ROOT, PACKAGES, RELEASE, safe_path

CHUNK_BYTES = 512 * 1024
STORY = {'fielddata/script/scr_seq.narc', 'msgdata/msg.narc',
         'msgdata/pl_msg.narc', 'msgdata/scenario/scr_msg.narc'}
DEFAULT_CONFIG = ('[General]\nInternalResolutionScale=1\nWindowWidth=512\n'
                  'WindowHeight=768\nFullScreen=false\nScreenLayout=vertical\n'
                  'SwapScreens=false\nVsyncInterval=1\nCapFrameRate=true\n')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def deterministic_archive(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=6)
    return stream.getvalue()


def build_distribution(runtime, package, output):
    runtime, package, output = Path(runtime).resolve(), Path(package), Path(output).resolve()
    if output.exists():
        raise ValueError('Destination deja presente ; utiliser un dossier de construction neuf.')
    installed_manifest = (runtime / 'universe-install.json').read_bytes()
    install = json.loads(installed_manifest)
    if install.get('platform') != 'windows' or install.get('upstream_release') != RELEASE:
        raise ValueError('Installation Windows incompatible.')
    engine = package.read_bytes()
    if digest(engine) != PACKAGES['windows'][1]:
        raise ValueError('Paquet moteur incompatible.')
    groups = {'engine': {}, 'assets': {}, 'story': {}}
    seen = set()

    def add(group, name, expected):
        safe_path(name)
        if name.casefold() in seen:
            raise ValueError('Collision de fichier Windows : ' + name)
        if name.lower().endswith(('.nds', '.sav', '.log')) or Path(name).name.lower() in {
                'save.bin', 'sim_config.ini', 'sim_config_prj.ini'}:
            raise ValueError('Donnee personnelle interdite : ' + name)
        path = runtime.joinpath(*safe_path(name).parts)
        if not path.resolve().is_relative_to(runtime):
            raise ValueError('Fichier situe hors de l’installation : ' + name)
        data = path.read_bytes()
        if digest(data) != expected:
            raise ValueError('Fichier modifie : ' + name)
        groups[group][name] = data
        seen.add(name.casefold())

    with zipfile.ZipFile(io.BytesIO(engine)) as archive:
        for entry in archive.infolist():
            if entry.is_dir() or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Entree moteur incompatible : ' + entry.filename)
            add('engine', entry.filename, digest(archive.read(entry)))
    for name, expected in install['resources_sha256'].items():
        add('story' if name in STORY else 'assets', name, expected)
    add('story', 'universe-install.json', digest(installed_manifest))
    for path in sorted((ROOT / 'content/native/portable/licenses').glob('*.txt')):
        name = 'licenses/' + path.name
        if name.casefold() in seen:
            raise ValueError('Collision de notice : ' + name)
        groups['story'][name] = path.read_bytes()
        seen.add(name.casefold())
    files = [{'path': name, 'package': group, 'bytes': len(data), 'sha256': digest(data)}
             for group, members in groups.items() for name, data in sorted(members.items())]
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.git-distribution-', dir=output.parent))
    try:
        packages = []
        for group, members in groups.items():
            data = engine if group == 'engine' else deterministic_archive(members)
            chunks = []
            folder = stage / 'packages' / group
            folder.mkdir(parents=True)
            for number, offset in enumerate(range(0, len(data), CHUNK_BYTES)):
                chunk = data[offset:offset + CHUNK_BYTES]
                name = f'packages/{group}/{number:04d}.part'
                (stage / name).write_bytes(chunk)
                chunks.append({'path': name, 'bytes': len(chunk), 'sha256': digest(chunk)})
            packages.append({'id': group, 'bytes': len(data), 'sha256': digest(data), 'chunks': chunks})
        release = {'schema': 1, 'platform': 'windows-x64', 'upstream_release': RELEASE,
                   'executable': 'main.exe', 'resource_count': len(install['resources_sha256']),
                   'default_config': DEFAULT_CONFIG, 'files': files, 'packages': packages}
        release['build_id'] = digest(json.dumps(release, sort_keys=True, separators=(',', ':')).encode())[:20]
        (stage / 'release.json').write_text(json.dumps(release, indent=2) + '\n', encoding='utf-8')
        stage.rename(output)
        return {'build_id': release['build_id'], 'files': len(files),
                'chunks': sum(len(p['chunks']) for p in packages),
                'compressed_bytes': sum(p['bytes'] for p in packages),
                'installed_bytes': sum(f['bytes'] for f in files)}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build_distribution(args.runtime, args.package, args.output), indent=2))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print('Distribution interrompue : ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
