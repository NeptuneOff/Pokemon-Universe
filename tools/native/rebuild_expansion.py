"""Rebuild the native metadata offline from the checked-in, pinned snapshots."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

if __package__:
    from .build_expansion_catalog import build
else:
    from build_expansion_catalog import build

ROOT = Path(__file__).resolve().parents[2]


def rebuild(source_root, output_root):
    source_root, output_root = Path(source_root), Path(output_root)
    provenance = json.loads((source_root / 'provenance.json').read_text(encoding='utf-8'))
    required = {'pokedex.ts.gz', 'species-names.csv.gz'}
    if set(provenance['files']) != required:
        raise ValueError('Unexpected snapshot file list')
    for name, metadata in provenance['files'].items():
        decoded = gzip.decompress((source_root / name).read_bytes())
        if hashlib.sha256(decoded).hexdigest() != metadata['decoded_sha256']:
            raise ValueError('Snapshot hash mismatch: ' + name)
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='universe-catalog-') as folder:
        pokedex = Path(folder) / 'pokedex.json'
        node = shutil.which('node')
        if not node:
            raise ValueError('Node 24 is required for developer rebuilds only')
        subprocess.run([node, str(ROOT / 'tools/native/read_showdown.mjs'),
                        str(source_root / 'pokedex.ts.gz'), str(pokedex)], check=True,
                       capture_output=True, text=True, timeout=30)
        return build(pokedex, source_root / 'species-names.csv.gz', provenance,
                     output_root / 'catalog.json', output_root / 'catalog.inc')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--write', action='store_true')
    args = parser.parse_args()
    targets = {'catalog.json': ROOT / 'content/native/expansion/catalog.json',
               'catalog.inc': ROOT / 'native/universe/generated/catalog.inc'}
    try:
        with tempfile.TemporaryDirectory(prefix='universe-generated-') as folder:
            counts = rebuild(ROOT / 'content/native/expansion/sources', folder)
            for name, target in targets.items():
                data = (Path(folder) / name).read_bytes()
                if args.check and (not target.exists() or target.read_bytes().replace(b'\r\n', b'\n') != data):
                    raise ValueError('Generated file differs: ' + str(target.relative_to(ROOT)))
                if args.write:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
            print(json.dumps({'ok': True, **counts}))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print('Expansion rebuild failed: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
