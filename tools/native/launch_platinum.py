"""Launch the prepared native game from its resource and save directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def backup_save(runtime):
    """Keep every distinct save, without changing or interpreting the game's data."""
    source = Path(runtime) / 'save.bin'
    if not source.exists():
        return None
    data = source.read_bytes()
    if not data:
        return None
    digest = hashlib.sha256(data).hexdigest()
    folder = Path(runtime) / 'universe-backups'
    folder.mkdir(exist_ok=True)
    target = folder / (digest + '.sav')
    if target.exists():
        if target.read_bytes() != data:
            raise ValueError('Copie de secours altérée : ' + str(target))
        return target
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=folder, prefix='.save-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def launch(runtime):
    runtime = Path(runtime).resolve()
    manifest_path = runtime / 'universe-install.json'
    if not manifest_path.is_file():
        raise ValueError('Prépare le jeu avec PREPARER-PLATINE.bat ou prepare_platinum.py.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    platform = 'windows' if os.name == 'nt' else 'linux'
    if manifest.get('platform') != platform:
        raise ValueError('Cette installation ne correspond pas au système actuel.')
    for name in manifest['french_banks']:
        if not (runtime / name).is_file():
            raise ValueError('Ressource manquante : ' + name)
    env = os.environ.copy()
    executable = runtime / ('main.exe' if platform == 'windows' else 'pokeplatinum.AppImage')
    if not executable.is_file():
        raise ValueError('Exécutable absent : ' + str(executable))
    if platform == 'linux':
        env['APPIMAGE_EXTRACT_AND_RUN'] = '1'
    backup_save(runtime)
    result = subprocess.call([str(executable)], cwd=runtime, env=env)
    backup_save(runtime)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path,
                        default=ROOT / 'native-runtime' / ('windows-fr' if os.name == 'nt' else 'linux-fr'))
    args = parser.parse_args()
    try:
        return launch(args.runtime)
    except (OSError, ValueError, KeyError) as error:
        print('Lancement interrompu : ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
