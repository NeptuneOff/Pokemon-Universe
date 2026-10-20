"""Launch the prepared native game from its resource and save directory."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


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
    return subprocess.call([str(executable)], cwd=runtime, env=env)


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
