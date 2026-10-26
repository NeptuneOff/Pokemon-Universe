"""Prepare the native Platinum PC port from personal USA/France ROMs.

Python standard library only. No compilation, ROM upload or save replacement.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import sys
import tempfile
import urllib.request
import zipfile

if __package__:
    from .patch_intro import apply_intro, narc_members
    from .patch_investigation import apply_investigation, SCRIPTS
else:
    from patch_intro import apply_intro, narc_members
    from patch_investigation import apply_investigation, SCRIPTS

ROOT = Path(__file__).resolve().parents[2]
RELEASE = 'v0.1.12'
PACKAGES = {
    'windows': ('release_win64.zip', '0db11b84199b1b7cebdbdb8ceca26fc4c2a2a1c2f448aef86bfde8b26f49e5ec', 'main.exe'),
    'linux': ('release_linux.zip', 'a264c4eee1107e1a6a08ae0dc70b695b744cd6735c28b7c3d8cb81cd27e8d511', 'main'),
}
ROMS = {
    'us': (b'CPUE', '0862ec35b24de5c7e2dcb88c9eea0873110d755c'),
    'fr': (b'CPUF', '41ea92f794560e347cd9509f5ec9e9d479a4bbf1'),
}
FRENCH = ('msgdata/msg.narc', 'msgdata/pl_msg.narc', 'msgdata/scenario/scr_msg.narc')


def safe_path(name):
    p = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or p.is_absolute() or any(
            part in ('', '..', '.') for part in name.split('/')):
        raise ValueError('Chemin dangereux : ' + name)
    return p


def read_rom(path, lang):
    path = Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            files = [entry for entry in z.infolist() if entry.filename.lower().endswith('.nds')]
            if len(files) != 1 or files[0].file_size != 134217728:
                raise ValueError('Le ZIP doit contenir une seule ROM de 128 Mio.')
            data = z.read(files[0])
    else:
        if path.stat().st_size != 134217728:
            raise ValueError('Une ROM originale de 128 Mio est requise.')
        data = path.read_bytes()
    code, digest = ROMS[lang]
    if data[12:16] != code or hashlib.sha1(data).hexdigest() != digest:
        raise ValueError('ROM ' + lang.upper() + ' incompatible ou modifiée. Voir docs/NATIVE-FR.md.')
    return data


def nitro_files(data):
    """Extract named NitroFS entries using the FNT/FAT, with bounds checks."""
    def area(offset, size):
        if offset < 0 or size < 0 or offset + size > len(data):
            raise ValueError('Table NDS hors limites.')
        return data[offset:offset + size]
    if len(data) < 0x50:
        raise ValueError('En-tête NDS tronqué.')
    fo, fs, ao, az = struct.unpack_from('<4I', data, 0x40)
    fnt, fat = area(fo, fs), area(ao, az)
    result, visited = {}, set()

    def directory(number, prefix=''):
        if not 0xf000 <= number <= 0xffff:
            raise ValueError('Identifiant de répertoire NDS invalide.')
        idx = number & 0xfff
        if idx in visited or idx * 8 + 8 > len(fnt):
            raise ValueError('Arborescence NDS invalide.')
        visited.add(idx)
        pos, fid, _ = struct.unpack_from('<IHH', fnt, idx * 8)
        while pos < len(fnt):
            length = fnt[pos]
            pos += 1
            if length == 0:
                return
            n = length & 127
            if not n or pos + n > len(fnt):
                raise ValueError('Nom NDS tronqué.')
            name = fnt[pos:pos + n].decode('ascii')
            pos += n
            safe_path(name)
            if '/' in name:
                raise ValueError('Composant NDS invalide.')
            full = prefix + name
            if length & 128:
                if pos + 2 > len(fnt):
                    raise ValueError('Répertoire NDS tronqué.')
                child = struct.unpack_from('<H', fnt, pos)[0]
                pos += 2
                directory(child, full + '/')
            else:
                if fid * 8 + 8 > len(fat) or full in result:
                    raise ValueError('Allocation NDS invalide.')
                start, end = struct.unpack_from('<II', fat, fid * 8)
                fid += 1
                result[full] = area(start, end - start)
        raise ValueError('Répertoire NDS sans terminaison.')

    directory(0xf000)
    return result


def narc_count(data):
    return len(narc_members(data)[0])


def extract_package(package, target):
    with zipfile.ZipFile(package) as z:
        if sum(entry.file_size for entry in z.infolist()) > 512 * 1024 * 1024:
            raise ValueError('Paquet trop volumineux.')
        for entry in z.infolist():
            p = safe_path(entry.filename.rstrip('/'))
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Lien symbolique interdit.')
            out = target.joinpath(*p.parts)
            if entry.is_dir():
                out.mkdir(parents=True, exist_ok=True)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(z.read(entry))


def french_resources(us, fr, text_only=False):
    """Map French resources to the USA paths compiled into the PC engine."""
    localized, counts, graphics = {}, {}, {}
    for name in FRENCH:
        a, b = narc_count(us[name]), narc_count(fr[name])
        if a != b:
            raise ValueError('Banques de textes incompatibles : ' + name)
        counts[name] = b
        localized[name] = fr[name]
    if not text_only:
        definition = json.loads((ROOT / 'content/native/graphics.fr.json').read_text(encoding='utf-8'))
        for entry in definition['archives']:
            target, source, expected = entry['target'], entry['source'], entry['members']
            if target not in us or source not in fr:
                raise ValueError('Ressource de localisation absente : ' + source)
            if narc_count(us[target]) != expected or narc_count(fr[source]) != expected:
                raise ValueError('Archive graphique incompatible : ' + target)
            localized[target] = fr[source]
            graphics[target] = {'source': source, 'members': expected}
    return localized, counts, graphics


def saved_progress(source, platform):
    """Read a compatible installation's save without changing the source."""
    source = Path(source).resolve()
    manifest = json.loads((source / 'universe-install.json').read_text(encoding='utf-8'))
    if manifest.get('platform') != platform or manifest.get('upstream_release') != RELEASE:
        raise ValueError('La sauvegarde doit venir du même port et du même système.')
    data = (source / 'save.bin').read_bytes()
    if not data:
        raise ValueError('La sauvegarde à reprendre est vide.')
    return data


def prepare(us_path, fr_path, platform, output, package=None, vanilla=False, text_only=False,
            *, intro_only=False, save_from=None):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Dossier déjà présent ; aucune sauvegarde ne sera écrasée : ' + str(output))
    progress = saved_progress(save_from, platform) if save_from is not None else None
    print('Vérification des ROM et des textes français…', flush=True)
    us = nitro_files(read_rom(us_path, 'us'))
    fr = nitro_files(read_rom(fr_path, 'fr'))
    localized, counts, graphics = french_resources(us, fr, text_only)
    patches = []
    original_intro = fr['msgdata/pl_msg.narc']
    if not vanilla:
        localized['msgdata/pl_msg.narc'], provenance = apply_intro(original_intro)
        patches.append(provenance)
        if not intro_only:
            quest_resources, provenance = apply_investigation(us[SCRIPTS], localized['msgdata/pl_msg.narc'])
            localized.update(quest_resources)
            patches.append(provenance)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.platinum-', dir=output.parent))
    try:
        filename, digest, executable = PACKAGES[platform]
        if package is None:
            print('Téléchargement du port natif ' + RELEASE + '…', flush=True)
            package = stage / filename
            url = 'https://github.com/cybervisi0n/pokeplatinum/releases/download/' + RELEASE + '/' + filename
            with urllib.request.urlopen(url, timeout=60) as source, package.open('wb') as dest:
                shutil.copyfileobj(source, dest)
        if hashlib.sha256(Path(package).read_bytes()).hexdigest() != digest:
            raise ValueError('Empreinte du paquet natif incorrecte.')
        runtime = stage / 'runtime'
        runtime.mkdir()
        extract_package(package, runtime)
        if not (runtime / executable).is_file():
            raise ValueError('Exécutable natif absent.')
        print('Installation des ressources et des textes français…', flush=True)
        resources = {}
        for name, data in us.items():
            p = runtime.joinpath(*safe_path(name).parts)
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists():
                raise ValueError('Collision de ressource : ' + name)
            resource = localized.get(name, data)
            p.write_bytes(resource)
            resources[name] = hashlib.sha256(resource).hexdigest()
        if patches:
            backup = runtime / 'universe-original/msgdata/pl_msg.narc'
            backup.parent.mkdir(parents=True)
            backup.write_bytes(original_intro)
            if not intro_only:
                script_backup = runtime / 'universe-original' / SCRIPTS
                script_backup.parent.mkdir(parents=True, exist_ok=True)
                script_backup.write_bytes(us[SCRIPTS])
        if progress is not None:
            (runtime / 'save.bin').write_bytes(progress)
            saves = runtime / 'universe-backups'
            saves.mkdir(exist_ok=True)
            (saves / (hashlib.sha256(progress).hexdigest() + '.sav')).write_bytes(progress)
        (runtime / 'sim_config.ini').write_text(
            '[General]\nInternalResolutionScale=1\nWindowWidth=512\nWindowHeight=768\n'
            'FullScreen=false\nScreenLayout=vertical\nSwapScreens=false\nVsyncInterval=1\nCapFrameRate=true\n',
            encoding='utf-8')
        manifest = {'schema': 1, 'upstream_release': RELEASE, 'platform': platform,
                    'package_sha256': digest, 'rom_sha1': {key: value[1] for key, value in ROMS.items()},
                    'named_resources': len(us), 'french_banks': counts, 'french_graphics': graphics,
                    'universe_campaign': False, 'universe_investigation': not vanilla and not intro_only,
                    'patches': patches, 'resources_sha256': resources}
        if progress is not None:
            manifest['imported_save_sha256'] = hashlib.sha256(progress).hexdigest()
        (runtime / 'universe-install.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        if platform == 'linux':
            (runtime / executable).chmod(0o755)
            (runtime / 'pokeplatinum.AppImage').chmod(0o755)
        runtime.rename(output)
        print('Prêt : ' + str(output / executable), flush=True)
        return manifest
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--us', type=Path)
    parser.add_argument('--fr', type=Path)
    parser.add_argument('--platform', choices=PACKAGES, default='windows' if os.name == 'nt' else 'linux')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--vanilla', action='store_true', help='Omettre le prologue et l’enquête Universe.')
    parser.add_argument('--intro-only', action='store_true', help='Omettre l’enquête de Bonaugure.')
    parser.add_argument('--save-from', type=Path, help='Copier la sauvegarde d’une installation fermée, laissée intacte.')
    parser.add_argument('--text-only', action='store_true', help='Garder les graphismes USA pour comparaison.')
    args = parser.parse_args()
    if args.gui:
        import tkinter as tk
        from tkinter import filedialog
        window = tk.Tk()
        window.withdraw()
        try:
            for field, label in [('us', 'Choisir Platine USA Rev 1'), ('fr', 'Choisir Platine France')]:
                value = filedialog.askopenfilename(title=label, filetypes=[('ROM ou ZIP', '*.nds *.zip')])
                if not value:
                    print('Installation annulée.')
                    return 2
                setattr(args, field, Path(value))
        finally:
            window.destroy()
    if not args.us or not args.fr:
        parser.error('Fournis --us et --fr, ou utilise --gui.')
    prepare(args.us, args.fr, args.platform,
            args.output or ROOT / 'native-runtime' / (args.platform + '-fr'),
            args.package, args.vanilla, args.text_only, intro_only=args.intro_only, save_from=args.save_from)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        print('Préparation interrompue : ' + str(error), file=sys.stderr)
        sys.exit(1)
