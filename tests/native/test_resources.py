"""ROM-free regression tests: corrupt archives, untouched messages and save protection."""
import io
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import zipfile

from tools.native.patch_intro import (apply_intro, character_map, crypt_message, encode_text,
                                      encrypted_messages, narc_members, replace_message,
                                      replace_narc_member)
from tools.native.prepare_platinum import (FRENCH, ROOT, RELEASE, extract_package, french_resources,
                                           nitro_files, prepare, safe_path, saved_progress)


def archive(members):
    payload, entries = bytearray(), bytearray()
    for member in members:
        start = len(payload)
        payload.extend(member)
        entries.extend(struct.pack('<II', start, len(payload)))
        payload.extend(b'\xff' * (-len(payload) % 4))
    fat = struct.pack('<4sIHH', b'BTAF', 12 + len(entries), len(members), 0) + entries
    names = b'BTNF\x10\0\0\0\x04\0\0\0\0\0\x01\0'
    image = struct.pack('<4sI', b'GMIF', 8 + len(payload)) + payload
    body = fat + names + image
    return b'NARC\xff\xfe\0\x01' + struct.pack('<IHH', 16 + len(body), 16, 3) + body


def message_bank():
    messages = [crypt_message(encode_text('A'), 0),
                crypt_message(struct.pack('<6H', 0xfffe, 0x100, 1, 17, 0x145, 0xffff), 1)]
    table, content = bytearray(), bytearray()
    for i, message in enumerate(messages):
        key = (765 * (i + 1) * 7) & 0xffff
        key |= key << 16
        table += struct.pack('<II', (20 + len(content)) ^ key, (len(message) // 2) ^ key)
        content += message
    return struct.pack('<HH', 2, 7) + table + content


def nds_file(name=b'a', payload=b'test'):
    names = struct.pack('<IHH', 8, 0, 1) + bytes([len(name)]) + name + b'\0'
    fat_at = 0x50 + len(names)
    data_at = fat_at + 8
    header = bytearray(0x50)
    struct.pack_into('<4I', header, 0x40, 0x50, len(names), fat_at, 8)
    return header + names + struct.pack('<II', data_at, data_at + len(payload)) + payload


class ResourceTests(unittest.TestCase):
    def test_nds_named_resource_and_invalid_bounds(self):
        data = nds_file()
        self.assertEqual(nitro_files(data), {'a': b'test'})
        with self.assertRaises(ValueError):
            nitro_files(data[:-1])
        with self.assertRaises(ValueError):
            nitro_files(nds_file(b'../escape'))

    def test_nds_directory_cycle_is_rejected(self):
        data = bytearray(0x50)
        names = struct.pack('<IHH', 8, 0, 1) + b'\x81a\x00\xf0\x00'
        struct.pack_into('<4I', data, 0x40, 0x50, len(names), 0x50 + len(names), 0)
        with self.assertRaises(ValueError):
            nitro_files(data + names)

    def test_narc_replacement_preserves_other_members_and_names(self):
        original = archive([b'a', b'bc', b'defgh'])
        updated = replace_narc_member(original, 1, b'longer replacement')
        members, blocks = narc_members(updated)
        self.assertEqual(members, [b'a', b'longer replacement', b'defgh'])
        self.assertEqual(blocks[b'BTNF'], narc_members(original)[1][b'BTNF'])
        invalid = bytearray(updated)
        struct.pack_into('<I', invalid, 16 + 12 + 4, 9999999)
        with self.assertRaises(ValueError):
            narc_members(invalid)
        with self.assertRaises(ValueError):
            narc_members(updated[:-1])

    def test_encryption_known_vector_and_unknown_commands_unchanged(self):
        self.assertEqual(crypt_message(encode_text('A'), 0), bytes.fromhex('f81aef9a'))
        bank = message_bank()
        text = 'Été à Sinnoh !\nPokémon Universe !\r'
        updated = replace_message(bank, 0, text)
        seed, before = encrypted_messages(bank)
        new_seed, after = encrypted_messages(updated)
        self.assertEqual(seed, new_seed)
        self.assertEqual(before[1], after[1])
        self.assertEqual(crypt_message(after[0], 0), encode_text(text))
        with self.assertRaises(ValueError):
            encode_text('Unsupported 🐱')

    def test_wrong_language_or_version_cannot_receive_intro(self):
        with self.assertRaisesRegex(ValueError, 'française originale'):
            apply_intro(archive([message_bank()] * 724))

    def test_latin_character_values(self):
        chars = character_map()
        self.assertEqual([chars[x] for x in 'Aéàœ '], [0x12b, 0x188, 0x17f, 0x1a0, 0x1de])

    def test_graphics_use_explicit_paths_and_compatible_members(self):
        entries = json.loads((ROOT / 'content/native/graphics.fr.json').read_text())['archives']
        self.assertEqual(len(entries), len({entry['target'] for entry in entries}))
        us = {name: archive([b'text']) for name in FRENCH}
        fr = dict(us)
        for entry in entries:
            us[entry['target']] = archive([b'USA'] * entry['members'])
            fr[entry['source']] = archive([b'France'] * entry['members'])
        localized, _, mapping = french_resources(us, fr)
        self.assertEqual(localized['graphic/touch_subwindow.narc'], fr['resource/fra/touch_subwindow/touch_subwindow.narc'])
        self.assertEqual(len(mapping), 29)
        self.assertNotIn('demo/title/op_demo.narc', localized)
        fr[entries[0]['source']] = archive([b'incompatible'])
        with self.assertRaisesRegex(ValueError, 'graphique incompatible'):
            french_resources(us, fr)

    def test_zip_paths_and_symlinks_cannot_escape(self):
        for name in ('../outside', '/absolute', 'C:/absolute', 'a\\b', 'a//b', './a'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_path(name)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, attr in [('../outside', 0), ('link', 0o120777 << 16)]:
                data = io.BytesIO()
                with zipfile.ZipFile(data, 'w') as z:
                    info = zipfile.ZipInfo(name)
                    info.external_attr = attr
                    z.writestr(info, 'payload')
                data.seek(0)
                with self.assertRaises(ValueError):
                    extract_package(data, root / 'target')
            self.assertFalse((root / 'outside').exists())

    def test_existing_save_directory_is_never_touched(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'game'
            target.mkdir()
            save = target / 'pokeplatinum.sav'
            save.write_bytes(b'valuable save')
            with self.assertRaisesRegex(ValueError, 'déjà présent'):
                prepare('unneeded-us.nds', 'unneeded-fr.nds', 'windows', target)
            self.assertEqual(save.read_bytes(), b'valuable save')

    def test_bad_download_leaves_no_partial_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / 'bad.zip'
            package.write_bytes(b'incomplete download')
            resources = {name: archive([b'hello']) for name in FRENCH}
            with patch('tools.native.prepare_platinum.read_rom', return_value=b''), \
                    patch('tools.native.prepare_platinum.nitro_files', return_value=resources):
                with self.assertRaisesRegex(ValueError, 'Empreinte'):
                    prepare('us', 'fr', 'windows', root / 'game', package, vanilla=True, text_only=True)
            self.assertFalse((root / 'game').exists())
            self.assertEqual(list(root.glob('.platinum-*')), [])

    def test_save_import_preserves_source_and_creates_a_backup_in_the_new_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'previous'
            source.mkdir()
            (source / 'universe-install.json').write_text(json.dumps({
                'platform': 'windows', 'upstream_release': RELEASE}), encoding='utf-8')
            progress = b'personal native save: role=analyst; quest=started'
            (source / 'save.bin').write_bytes(progress)
            package = root / 'runtime.zip'
            with zipfile.ZipFile(package, 'w') as z:
                z.writestr('main.exe', b'not executed in this test')
            resources = {name: archive([b'text']) for name in FRENCH}
            before = {p.name: p.read_bytes() for p in source.iterdir()}
            with patch('tools.native.prepare_platinum.read_rom', return_value=b''), \
                    patch('tools.native.prepare_platinum.nitro_files', return_value=resources), \
                    patch.dict('tools.native.prepare_platinum.PACKAGES', {'windows': (
                        'runtime.zip', hashlib.sha256(package.read_bytes()).hexdigest(), 'main.exe')}):
                manifest = prepare('us', 'fr', 'windows', root / 'new', package,
                                   vanilla=True, text_only=True, save_from=source)
            digest = hashlib.sha256(progress).hexdigest()
            self.assertEqual((root / 'new/save.bin').read_bytes(), progress)
            self.assertEqual((root / 'new/universe-backups' / (digest + '.sav')).read_bytes(), progress)
            self.assertEqual(manifest['imported_save_sha256'], digest)
            self.assertEqual(before, {p.name: p.read_bytes() for p in source.iterdir()})
            with self.assertRaisesRegex(ValueError, 'même port'):
                saved_progress(source, 'linux')
            (source / 'save.bin').write_bytes(b'')
            with self.assertRaisesRegex(ValueError, 'vide'):
                saved_progress(source, 'windows')


if __name__ == '__main__':
    unittest.main()
