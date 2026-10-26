"""Package an already prepared private Windows install, without a ROM selector.

Only explicit resource/package entries are copied. Test saves, ROMs, logs and
unrelated files are excluded. The resulting private artifact is not a GitHub
release; public Git contains this packaging code, not extracted game assets.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

if __package__:
    from .prepare_platinum import ROOT, PACKAGES, RELEASE, safe_path
else:
    from prepare_platinum import ROOT, PACKAGES, RELEASE, safe_path


def package_windows(runtime, package, output):
    runtime, package, output = Path(runtime).resolve(), Path(package), Path(output).resolve()
    if output.exists():
        raise ValueError('Archive deja presente : ' + str(output))
    manifest = json.loads((runtime / 'universe-install.json').read_text(encoding='utf-8'))
    if manifest.get('platform') != 'windows' or manifest.get('upstream_release') != RELEASE:
        raise ValueError('Une installation Windows compatible est requise.')
    if hashlib.sha256(package.read_bytes()).hexdigest() != PACKAGES['windows'][1]:
        raise ValueError('Paquet du moteur incompatible.')
    files = {}

    def installed(name, expected):
        path = runtime.joinpath(*safe_path(name).parts)
        if not path.resolve().is_relative_to(runtime):
            raise ValueError('Fichier situe hors de l’installation : ' + name)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Fichier modifie : ' + name)
        if name in files:
            raise ValueError('Collision de fichier : ' + name)
        files[name] = data

    with zipfile.ZipFile(package) as source:
        for entry in source.infolist():
            if not entry.is_dir():
                installed(entry.filename, hashlib.sha256(source.read(entry)).hexdigest())
    for name, expected in manifest['resources_sha256'].items():
        installed(name, expected)
    files['sim_config.ini'] = (runtime / 'sim_config.ini').read_bytes()
    files['universe-install.json'] = (runtime / 'universe-install.json').read_bytes()
    templates = ROOT / 'content/native/portable'
    for template in sorted(templates.rglob('*')):
        if template.is_file():
            name = template.relative_to(templates).as_posix()
            if name in files:
                raise ValueError('Collision de lanceur : ' + name)
            files[name] = template.read_bytes()
    if any(name.lower().endswith(('.nds', '.sav')) or Path(name).name == 'save.bin' for name in files):
        raise ValueError('Le paquet ne doit pas contenir de ROM ou de sauvegarde.')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.universe-', suffix='.zip', delete=False) as stream:
            temporary = Path(stream.name)
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as dest:
            for name, data in sorted(files.items()):
                dest.writestr('Pokemon-Universe/' + name, data)
        with zipfile.ZipFile(temporary) as check:
            bad = check.testzip()
            if bad:
                raise ValueError('Archive illisible : ' + bad)
        temporary.rename(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'path': str(output), 'files': len(files), 'bytes': output.stat().st_size,
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(package_windows(args.runtime, args.package, args.output), indent=2))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print('Paquet interrompu : ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
