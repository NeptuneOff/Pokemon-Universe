"""Rebuild existing Universe dialogue from a verified Git distribution, no ROM.

Only existing messages are replaced. Script bytes, message IDs, rewards and
save variables stay intact; adding an event needs its own script integration.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

from tools.native.build_git_distribution import CHUNK_BYTES, deterministic_archive, digest
from tools.native.patch_intro import narc_members, replace_narc_member, encrypted_messages, crypt_message, encode_text, replace_message
from tools.native.prepare_platinum import safe_path

TEXT = 'msgdata/pl_msg.narc'
DEFINITIONS = ['prologue.fr.json', 'bonaugure.fr.json', 'littorella-labo.fr.json', 'littorella-temoin.fr.json']


def refresh_messages(archive, old_definitions, new_definitions):
    if len(old_definitions) != len(new_definitions):
        raise ValueError('The dialogue definition set changed')
    changes = []
    for old, new in zip(old_definitions, new_definitions):
        bank_id = old.get('bank', old.get('text_bank'))
        if bank_id != new.get('bank', new.get('text_bank')):
            raise ValueError('The message bank changed')
        members, _ = narc_members(archive)
        bank = members[bank_id]
        _, messages = encrypted_messages(bank)
        if 'text' in old:
            if old['message'] != new['message']:
                raise ValueError('The intro message index changed')
            first = old['message']
            previous, updated = [''.join(old['text'])], [''.join(new['text'])]
        else:
            if list(old['messages']) != list(new['messages']):
                raise ValueError('Message IDs changed; a script update is required')
            previous, updated = list(old['messages'].values()), list(new['messages'].values())
            matches = [start for start in range(len(messages) - len(previous) + 1)
                       if all(messages[start + i] == crypt_message(encode_text(text), start + i)
                              for i, text in enumerate(previous))]
            if len(matches) != 1:
                raise ValueError('Previous Universe dialogue is missing or ambiguous')
            first = matches[0]
        if first < 0 or first + len(previous) > len(messages):
            raise ValueError('Previous message range is invalid')
        if any(messages[first + i] != crypt_message(encode_text(text), first + i)
               for i, text in enumerate(previous)):
            raise ValueError('Previous Universe dialogue differs')
        count = 0
        for i, (before, after) in enumerate(zip(previous, updated)):
            if before != after:
                bank = replace_message(bank, first + i, after)
                count += 1
        if count:
            archive = replace_narc_member(archive, bank_id, bank)
            changes.append({'id': new['id'], 'bank': bank_id, 'first_message': first, 'changed_messages': count})
    return archive, changes


def rebuild(repo, base_ref, output):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    if not re.fullmatch('[0-9a-f]{40}', base_ref):
        raise ValueError('Use an immutable source commit')
    if output.exists():
        raise ValueError('Story output already exists')

    def at(path):
        safe_path(path)
        return subprocess.check_output(['git', '-C', str(repo), 'show', base_ref + ':' + path])

    release = json.loads(at('distribution/windows/release.json'))
    packages = {p['id']: p for p in release['packages']}
    assembled = bytearray()
    for part in packages['story']['chunks']:
        data = at('distribution/windows/' + part['path'])
        if len(data) != part['bytes'] or digest(data) != part['sha256']:
            raise ValueError('Corrupt source story fragment')
        assembled.extend(data)
    if len(assembled) != packages['story']['bytes'] or digest(assembled) != packages['story']['sha256']:
        raise ValueError('Corrupt source story package')
    expected = {f['path']: f for f in release['files'] if f['package'] == 'story'}
    with zipfile.ZipFile(io.BytesIO(assembled)) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())) or set(archive.namelist()) != set(expected):
            raise ValueError('Unexpected story package members')
        story = {name: archive.read(name) for name in archive.namelist()}
    for name, data in story.items():
        safe_path(name)
        if len(data) != expected[name]['bytes'] or digest(data) != expected[name]['sha256']:
            raise ValueError('Story file differs from the source release: ' + name)
    old_defs = [json.loads(at('content/native/' + name)) for name in DEFINITIONS]
    new_defs = [json.loads((repo / 'content/native' / name).read_text(encoding='utf-8')) for name in DEFINITIONS]
    previous_digest = digest(story[TEXT])
    story[TEXT], changes = refresh_messages(story[TEXT], old_defs, new_defs)
    if not changes:
        raise ValueError('No dialogue changed')
    identity = json.loads(story['universe-install.json'])
    if identity['resources_sha256'][TEXT] != previous_digest:
        raise ValueError('Source installation identity differs')
    identity['resources_sha256'][TEXT] = digest(story[TEXT])
    identity['universe_campaign'] = {'id': new_defs[0]['id'], 'archive': TEXT, 'bank': new_defs[0]['bank'],
                                   'message': new_defs[0]['message'], 'source_sha256': previous_digest,
                                   'patched_sha256': digest(story[TEXT])}
    identity['universe_story_refresh'] = {'base_commit': base_ref, 'base_build': release['build_id'],
        'source_sha256': previous_digest, 'patched_sha256': digest(story[TEXT]), 'changes': changes,
        'definitions_sha256': {name: digest((repo / 'content/native' / name).read_bytes().replace(b'\r\n', b'\n')) for name in DEFINITIONS}}
    story['universe-install.json'] = (json.dumps(identity, indent=2) + '\n').encode()
    data = deterministic_archive(story)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.story-refresh-', dir=output.parent))
    try:
        # Reuse only declared engine/artwork chunks, and verify each while copying.
        for package in release['packages']:
            if package['id'] == 'story':
                continue
            whole = hashlib.sha256()
            size = 0
            for part in package['chunks']:
                chunk = at('distribution/windows/' + part['path'])
                if len(chunk) != part['bytes'] or digest(chunk) != part['sha256']:
                    raise ValueError('Corrupt source fragment: ' + part['path'])
                target = stage.joinpath(*safe_path(part['path']).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(chunk)
                whole.update(chunk)
                size += len(chunk)
            if whole.hexdigest() != package['sha256'] or size != package['bytes']:
                raise ValueError('Corrupt source package')
        parts = []
        for number, offset in enumerate(range(0, len(data), CHUNK_BYTES)):
            chunk = data[offset:offset + CHUNK_BYTES]
            name = f'packages/story/{number:04d}.part'
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(chunk)
            parts.append({'path': name, 'bytes': len(chunk), 'sha256': digest(chunk)})
        release['packages'] = [dict(id='story', bytes=len(data), sha256=digest(data), chunks=parts)
                               if p['id'] == 'story' else p for p in release['packages']]
        for entry in release['files']:
            if entry['path'] in story:
                payload = story[entry['path']]
                entry.update(bytes=len(payload), sha256=digest(payload))
        release.pop('build_id', None)
        release['build_id'] = digest(json.dumps(release, sort_keys=True, separators=(',', ':')).encode())[:20]
        (stage / 'release.json').write_text(json.dumps(release, indent=2) + '\n', encoding='utf-8')
        stage.rename(output)
        return {'build_id': release['build_id'], 'changes': changes, 'resource_count': release['resource_count']}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-ref', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    print(json.dumps(rebuild(args.repo, args.base_ref, args.output), indent=2))
