"""Install the first native Universe investigation into personal resources."""
import hashlib
import json
from pathlib import Path
import struct

if __package__:
    from .field_script import append_events
    from .patch_intro import ROOT, crypt_message, encode_text, encrypted_messages, narc_members, replace_narc_member
else:
    from field_script import append_events
    from patch_intro import ROOT, crypt_message, encode_text, encrypted_messages, narc_members, replace_narc_member

SCRIPTS = 'fielddata/script/scr_seq.narc'
MESSAGES = 'msgdata/pl_msg.narc'


def append_messages(bank, texts):
    seed, messages = encrypted_messages(bank)
    first = len(messages)
    for text in texts:
        messages.append(crypt_message(encode_text(text), len(messages)))
    if len(messages) > 256:
        raise ValueError('Trop de messages pour les événements de cette carte.')
    table, payload = bytearray(), bytearray()
    for index, message in enumerate(messages):
        key = (765 * (index + 1) * seed) & 0xffff
        key |= key << 16
        table.extend(struct.pack('<II', (4 + len(messages) * 8 + len(payload)) ^ key,
                                 (len(message) // 2) ^ key))
        payload.extend(message)
    return struct.pack('<HH', len(messages), seed) + table + payload, first


def apply_investigation(scripts, messages, definition=None):
    definition = definition or ROOT / 'content/native/bonaugure.fr.json'
    quest = json.loads(Path(definition).read_text(encoding='utf-8'))
    script_members, _ = narc_members(scripts)
    text_members, _ = narc_members(messages)
    script = script_members[quest['script_bank']]
    text = text_members[quest['text_bank']]
    for source, digest in [(script, quest['source_script_sha256']), (text, quest['source_text_sha256'])]:
        if hashlib.sha256(source).hexdigest() != digest:
            raise ValueError('L’enquête exige les ressources originales compatibles de Bonaugure.')
    new_text, first = append_messages(text, quest['messages'].values())
    symbols = quest['variables'] | {name: first + i for i, name in enumerate(quest['messages'])}
    new_script = append_events(script, quest['entries'], quest['instructions'], symbols, quest['entry_count'])
    result = {SCRIPTS: replace_narc_member(scripts, quest['script_bank'], new_script),
              MESSAGES: replace_narc_member(messages, quest['text_bank'], new_text)}
    provenance = {'id': quest['id'], 'script_bank': quest['script_bank'], 'text_bank': quest['text_bank'],
                  'entries': quest['entries'], 'variables': quest['variables'],
                  'resources_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in result.items()}}
    return result, provenance
