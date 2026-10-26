"""Compare installed resources with personal Platinum ROMs, without changing files."""
import argparse
import json
import os
from pathlib import Path
import sys

if __package__:
    from .prepare_platinum import ROOT, french_resources, nitro_files, read_rom, safe_path
    from .patch_intro import apply_intro
    from .patch_investigation import apply_investigation, apply_followup, SCRIPTS
else:
    from prepare_platinum import ROOT, french_resources, nitro_files, read_rom, safe_path
    from patch_intro import apply_intro
    from patch_investigation import apply_investigation, apply_followup, SCRIPTS


def verify(runtime, us_path, fr_path, *, vanilla=False, text_only=False, intro_only=False, bonaugure_only=False):
    us = nitro_files(read_rom(us_path, 'us'))
    fr = nitro_files(read_rom(fr_path, 'fr'))
    localized, _, graphics = french_resources(us, fr, text_only)
    if not vanilla:
        localized['msgdata/pl_msg.narc'], _ = apply_intro(fr['msgdata/pl_msg.narc'])
        if not intro_only:
            quest_resources, _ = apply_investigation(us[SCRIPTS], localized['msgdata/pl_msg.narc'])
            localized.update(quest_resources)
            if not bonaugure_only:
                quest_resources, _ = apply_followup(localized[SCRIPTS], localized['msgdata/pl_msg.narc'])
                localized.update(quest_resources)
    expected = us | localized
    missing, changed = [], []
    runtime = Path(runtime).resolve()
    for name, original in sorted(expected.items()):
        path = runtime.joinpath(*safe_path(name).parts)
        if not path.resolve().is_relative_to(runtime):
            raise ValueError('Ressource située hors du dossier du jeu : ' + name)
        if not path.is_file():
            missing.append(name)
        elif path.read_bytes() != original:
            changed.append(name)
    return {'ok': not missing and not changed, 'expected_resources': len(expected),
            'matching_resources': len(expected) - len(missing) - len(changed),
            'french_graphics': len(graphics), 'universe_intro': not vanilla,
            'universe_investigation': not vanilla and not intro_only,
            'universe_followup': not vanilla and not intro_only and not bonaugure_only,
            'missing': missing, 'changed': changed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--us', type=Path, required=True)
    parser.add_argument('--fr', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, default=ROOT / 'native-runtime' /
                        ('windows-fr' if os.name == 'nt' else 'linux-fr'))
    parser.add_argument('--vanilla', action='store_true')
    parser.add_argument('--intro-only', action='store_true')
    parser.add_argument('--bonaugure-only', action='store_true')
    parser.add_argument('--text-only', action='store_true')
    parser.add_argument('--json', action='store_true', dest='as_json')
    args = parser.parse_args()
    try:
        result = verify(args.runtime, args.us, args.fr,
                        vanilla=args.vanilla, text_only=args.text_only, intro_only=args.intro_only,
                        bonaugure_only=args.bonaugure_only)
    except (OSError, ValueError, KeyError) as error:
        print('Vérification interrompue : ' + str(error), file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(f"{result['matching_resources']}/{result['expected_resources']} ressources conformes.")
        for name in result['missing']:
            print('Manquante : ' + name)
        for name in result['changed']:
            print('Modifiée : ' + name)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
