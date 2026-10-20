"""Patch one French dialogue in local Platinum resources without compiling.

Format reference: engine/platinum/src/message.c and tools/msgenc/MessagesConverter.h.
Other encrypted messages are preserved byte for byte, including control commands.
"""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]


def narc_members(data):
    if len(data) < 16 or data[:4] != b'NARC':
        raise ValueError('Archive NARC invalide.')
    total, header, count = struct.unpack_from('<IHH', data, 8)
    if total != len(data) or header != 16:
        raise ValueError('Taille NARC incohérente.')
    blocks, pos = {}, header
    for _ in range(count):
        if pos + 8 > total:
            raise ValueError('Bloc NARC tronqué.')
        tag, size = struct.unpack_from('<4sI', data, pos)
        if size < 8 or pos + size > total or tag in blocks:
            raise ValueError('Bloc NARC invalide.')
        blocks[tag] = data[pos:pos + size]
        pos += size
    if pos != total or set(blocks) != {b'BTAF', b'BTNF', b'GMIF'}:
        raise ValueError('Structure NARC non prise en charge.')
    fat, payload = blocks[b'BTAF'], blocks[b'GMIF'][8:]
    if len(fat) < 12:
        raise ValueError('Table NARC tronquée.')
    n = struct.unpack_from('<H', fat, 8)[0]
    if len(fat) != 12 + 8 * n:
        raise ValueError('Nombre de membres NARC incohérent.')
    members, previous = [], 0
    for i in range(n):
        start, end = struct.unpack_from('<II', fat, 12 + 8 * i)
        if start < previous or end < start or end > len(payload):
            raise ValueError('Allocation NARC hors limites.')
        members.append(payload[start:end])
        previous = end
    return members, blocks


def replace_narc_member(data, index, replacement):
    members, blocks = narc_members(data)
    if not 0 <= index < len(members):
        raise ValueError('Banque de textes absente.')
    members[index] = replacement
    payload, table = bytearray(), bytearray()
    for member in members:
        start = len(payload)
        payload.extend(member)
        table.extend(struct.pack('<II', start, len(payload)))
        payload.extend(b'\xff' * (-len(payload) % 4))
    fat = struct.pack('<4sIHH', b'BTAF', 12 + len(table), len(members), 0) + table
    image = struct.pack('<4sI', b'GMIF', 8 + len(payload)) + payload
    body = bytes(fat) + blocks[b'BTNF'] + bytes(image)
    header = bytearray(data[:16])
    struct.pack_into('<I', header, 8, 16 + len(body))
    return bytes(header) + body


def encrypted_messages(bank):
    if len(bank) < 4:
        raise ValueError('Banque de messages tronquée.')
    count, seed = struct.unpack_from('<HH', bank)
    end = 4 + count * 8
    if end > len(bank):
        raise ValueError('Table des messages tronquée.')
    result = []
    for i in range(count):
        key = (765 * (i + 1) * seed) & 0xffff
        key |= key << 16
        offset, length = struct.unpack_from('<II', bank, 4 + i * 8)
        offset ^= key
        length ^= key
        if offset < end or offset + length * 2 > len(bank) or length == 0:
            raise ValueError('Message hors limites.')
        result.append(bank[offset:offset + length * 2])
        end = offset + length * 2
    return seed, result


def crypt_message(data, index):
    if len(data) % 2:
        raise ValueError('Message de taille impaire.')
    values = struct.unpack('<' + 'H' * (len(data) // 2), data)
    key = (index + 1) * 596947
    return b''.join(struct.pack('<H', value ^ ((key + i * 18749) & 0xffff))
                    for i, value in enumerate(values))


def character_map():
    chars = {}
    for base, alphabet in [(0x121, '0123456789'), (0x12b, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
                           (0x145, 'abcdefghijklmnopqrstuvwxyz'),
                           (0x15f, 'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿŒœŞşªº¹²³')]:
        chars.update({char: base + i for i, char in enumerate(alphabet)})
    chars.update({' ': 0x1de, '!': 0x1ab, '?': 0x1ac, ',': 0x1ad, '.': 0x1ae,
                  '…': 0x1af, '’': 0x1b3, '-': 0x1be, ':': 0x1c4, ';': 0x1c5,
                  '\n': 0xe000, '\r': 0x25bc, '\f': 0x25bd})
    return chars


def encode_text(text):
    chars = character_map()
    try:
        values = [chars[char] for char in text] + [0xffff]
    except KeyError as error:
        raise ValueError('Caractère non pris en charge : ' + repr(error.args[0])) from error
    if len(values) > 1024:
        raise ValueError('Dialogue trop long pour la fenêtre d’introduction.')
    return struct.pack('<' + 'H' * len(values), *values)


def replace_message(bank, index, text):
    seed, messages = encrypted_messages(bank)
    if not 0 <= index < len(messages):
        raise ValueError('Message absent.')
    messages[index] = crypt_message(encode_text(text), index)
    count = len(messages)
    table, payload = bytearray(), bytearray()
    for i, message in enumerate(messages):
        key = (765 * (i + 1) * seed) & 0xffff
        key |= key << 16
        table.extend(struct.pack('<II', (4 + count * 8 + len(payload)) ^ key,
                                 (len(message) // 2) ^ key))
        payload.extend(message)
    return struct.pack('<HH', count, seed) + bytes(table) + bytes(payload)


def apply_intro(archive, definition=None):
    definition = definition or ROOT / 'content/native/prologue.fr.json'
    patch = json.loads(Path(definition).read_text(encoding='utf-8'))
    bank_id, message_id = patch['bank'], patch['message']
    members, _ = narc_members(archive)
    if not 0 <= bank_id < len(members):
        raise ValueError('Banque d’introduction absente.')
    source = members[bank_id]
    if hashlib.sha256(source).hexdigest() != patch['source_bank_sha256']:
        raise ValueError('Le prologue exige la banque française originale de Platine.')
    patched = replace_narc_member(archive, bank_id,
                                  replace_message(source, message_id, ''.join(patch['text'])))
    return patched, {'id': patch['id'], 'archive': 'msgdata/pl_msg.narc',
                     'bank': bank_id, 'message': message_id,
                     'source_sha256': hashlib.sha256(archive).hexdigest(),
                     'patched_sha256': hashlib.sha256(patched).hexdigest()}
