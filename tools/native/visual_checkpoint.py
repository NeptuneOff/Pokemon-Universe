"""Integrity-checked checkpoints of disposable CI game sessions only."""
import hashlib
import json
import re
from pathlib import Path


def read_plan(path):
    plan = json.loads(Path(path).read_text(encoding='utf-8'))
    run_id = plan['run_id']
    candidate = plan.get('candidate_ref', 'builds/windows-linked')
    live_seconds = plan.get('live_seconds', 0)
    if type(run_id) is not int or run_id < 0:
        raise ValueError('Invalid disposable checkpoint run')
    pinned = isinstance(candidate, str) and re.fullmatch('[0-9a-f]{40}', candidate)
    if run_id and not pinned:
        raise ValueError('A resumed checkpoint requires an immutable candidate commit')
    if not pinned and candidate != 'builds/windows-linked':
        raise ValueError('Invalid candidate reference')
    if type(live_seconds) is not int or not 0 <= live_seconds <= 1200:
        raise ValueError('Invalid bounded live duration')
    return {'run_id': run_id, 'candidate_ref': candidate, 'live_seconds': live_seconds}


def write_checkpoint(runtime, output, build_id):
    source = Path(runtime) / 'save.bin'
    if not source.exists():
        return False
    if source.is_symlink() or not source.is_file():
        raise ValueError('The disposable flash file must be a regular file')
    data = source.read_bytes()
    if not data:
        return False
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'save.bin').write_bytes(data)
    (output / 'checkpoint.json').write_text(json.dumps({
        'schema': 1, 'build_id': build_id, 'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
        'kind': 'disposable-ci-flash',
        'game_save_validated': False,
    }, indent=2) + '\n', encoding='utf-8')
    return True


def restore_checkpoint(checkpoint, runtime, build_id):
    checkpoint, runtime = Path(checkpoint), Path(runtime)
    if {p.name for p in checkpoint.iterdir()} != {'save.bin', 'checkpoint.json'}:
        raise ValueError('Unexpected disposable checkpoint files')
    if any(p.is_symlink() or not p.is_file() for p in checkpoint.iterdir()):
        raise ValueError('Checkpoint entries must be regular files')
    manifest = json.loads((checkpoint / 'checkpoint.json').read_text(encoding='utf-8'))
    data = (checkpoint / 'save.bin').read_bytes()
    if manifest.get('schema') != 1 or manifest.get('kind') != 'disposable-ci-flash' or manifest.get('build_id') != build_id:
        raise ValueError('The checkpoint belongs to another game build')
    if not data or len(data) != manifest['bytes'] or hashlib.sha256(data).hexdigest() != manifest['sha256']:
        raise ValueError('The disposable checkpoint is corrupt')
    if (runtime / 'save.bin').exists():
        raise ValueError('Refusing to overwrite an existing flash file')
    (runtime / 'save.bin').write_bytes(data)
