"""Exercise compiled native event paths without distributing ROM data.

The bytecode runner below reads numeric opcodes independently of the assembler.
It models the relevant C commands, not rendering, timing or the native save file.
"""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from tools.native.field_script import append_events, assemble, entry_targets
from tools.native.patch_intro import ROOT, crypt_message, encode_text, encrypted_messages, narc_members
from tools.native.patch_investigation import append_messages, apply_investigation
from test_resources import archive, message_bank

QUEST = json.loads((ROOT / 'content/native/bonaugure.fr.json').read_text(encoding='utf-8'))


def original_script():
    # Nine harmless original entries, at distinct addresses after their table.
    return b''.join(struct.pack('<i', 38 + 2 * i - (4 * i + 4)) for i in range(9)) + b'\x13\xfd' + b'\x02\0' * 9


class EventRunner:
    def __init__(self, variant=0, state=None, potions=0):
        self.original = original_script()
        self.symbols = QUEST['variables'] | {key: 15 + i for i, key in enumerate(QUEST['messages'])}
        self.code = append_events(self.original, QUEST['entries'], QUEST['instructions'], self.symbols, 9)
        self.state = dict(state or {})
        self.variant = variant
        self.random_calls = 0
        self.potions = potions

    def run(self, entry, choices=(), *, bag_full=False):
        code = self.code
        pc = entry_targets(code, 9)[entry]
        self.messages, self.fallback = [], False
        locked, comparison, selected = False, None, None
        answers = iter(choices)

        def read(fmt):
            nonlocal pc
            values = struct.unpack_from('<' + fmt, code, pc)
            pc += struct.calcsize('<' + fmt)
            return values

        for _ in range(400):
            if pc < len(self.original):
                assert not locked, 'Fallback must not double-lock the native NPC'
                self.fallback = True
                return
            opcode, = read('H')
            if opcode == 0x02:
                assert not locked, 'Script left player movement locked'
                return
            elif opcode == 0x11:
                var, value = read('HH')
                comparison = self.state.get(var, 0) == value
            elif opcode == 0x16:
                offset, = read('i')
                pc += offset
            elif opcode == 0x1c:
                condition, offset = read('Bi')
                assert condition == 1
                if comparison:
                    pc += offset
            elif opcode == 0x28:
                var, value = read('HH')
                self.state[var] = value
            elif opcode == 0x2c:
                msg, = read('B')
                self.messages.append(msg)
            elif opcode == 0x41:
                _, _, _, cancel, selected = read('BBBBH')
                assert cancel == 1
            elif opcode == 0x42:
                read('BB')
            elif opcode == 0x43:
                self.state[selected] = next(answers)
            elif opcode == 0x60:
                assert not locked
                locked = True
            elif opcode == 0x61:
                assert locked
                locked = False
            elif opcode == 0x7b:
                item, count, result = read('HHH')
                assert item == 17 and count == 1
                self.state[result] = 0 if bag_full else 1
                if not bag_full:
                    self.potions += 1
            elif opcode == 0x1b7:
                var, bound = read('HH')
                assert bound == 2
                self.random_calls += 1
                self.state[var] = self.variant
            elif opcode in (0x31, 0x34, 0x68):
                pass  # Wait, close window, face player: exercised graphically separately.
            else:
                raise AssertionError(f'Unexpected native opcode {opcode:#x}')
        raise AssertionError('Event did not terminate')

    def value(self, name):
        return self.state.get(self.symbols[name], 0)

    def saw(self, name):
        return self.symbols[name] in self.messages


class InvestigationTests(unittest.TestCase):
    def test_both_roles_and_variants_reach_one_reward_and_keep_the_report(self):
        for role in (1, 2):
            for variant in (0, 1):
                with self.subTest(role=role, variant=variant):
                    game = EventRunner(variant)
                    game.run(4, [role - 1])
                    self.assertEqual((game.value('role'), game.value('stage'), game.random_calls), (role, 1, 1))
                    game.run(4)
                    self.assertEqual(game.random_calls, 1)
                    game.run(5 if role == 1 else 6)
                    self.assertTrue(game.fallback)
                    game.run(6 if role == 1 else 5, [variant if role == 1 else 0])
                    self.assertEqual(game.value('stage'), 2)
                    self.assertTrue(game.saw('evidence_east' if variant == 0 else 'evidence_west'))
                    # Reconstruct a new runner using only persistent state and inventory.
                    restored = EventRunner(1 - variant, game.state, game.potions)
                    restored.run(4)
                    self.assertEqual((restored.value('stage'), restored.potions), (3, 1))
                    restored.run(4)
                    self.assertTrue(restored.saw('done_east' if variant == 0 else 'done_west'))
                    self.assertEqual((restored.potions, restored.random_calls), (1, 0))
                    restored.run(5)
                    self.assertTrue(restored.fallback)
                    restored.run(6)
                    self.assertTrue(restored.fallback)

    def test_cancel_does_not_choose_a_role_or_reroll_an_existing_clue(self):
        for cancel in (2, 0xfffe):
            game = EventRunner()
            game.run(4, [cancel])
            self.assertEqual((game.value('role'), game.value('stage'), game.random_calls), (0, 0, 0))
            game.run(4, [0])
            game.run(6, [cancel])
            self.assertEqual((game.value('stage'), game.random_calls), (1, 1))
            game.run(4)
            self.assertEqual(game.random_calls, 1)

    def test_wrong_inference_or_disturbing_birds_is_retryable(self):
        for role in (1, 2):
            game = EventRunner(0)
            game.run(4, [role - 1])
            game.run(6 if role == 1 else 5, [1])
            self.assertEqual((game.value('stage'), game.potions), (1, 0))
            self.assertTrue(game.saw('wrong_reading' if role == 1 else 'startled'))
            game.run(6 if role == 1 else 5, [0])
            self.assertEqual(game.value('stage'), 2)

    def test_full_bag_does_not_lose_reward_or_duplicate_it_after_retry(self):
        game = EventRunner()
        game.run(4, [0])
        game.run(6, [0])
        game.run(4, bag_full=True)
        self.assertEqual((game.value('stage'), game.potions), (2, 0))
        self.assertTrue(game.saw('bag_full'))
        game.run(4)
        game.run(4)
        self.assertEqual((game.value('stage'), game.potions), (3, 1))

    def test_assembler_matches_native_relative_branch_encoding(self):
        code, _ = assemble([['label', 'start'], ['set', 0x40ea, 1],
                            ['compare', 0x40ea, 1], ['if_eq', 'end'],
                            ['goto', 'start'], ['label', 'end'], ['end']], base=100)
        self.assertEqual(code.hex(), '2800ea4001001100ea4001001c0001060000001600e7ffffff0200')
        for code in ([['message', 256]], [['goto', 'missing']],
                     [['label', 'a'], ['label', 'a']], [['unknown']], [['set', 'missing', 1]]):
            with self.subTest(code=code), self.assertRaises(ValueError):
                assemble(code)

    def test_original_entries_and_code_are_preserved(self):
        game = EventRunner()
        for index in (0, 1, 2, 3, 7, 8):
            self.assertEqual(game.code[index * 4:index * 4 + 4], game.original[index * 4:index * 4 + 4])
        self.assertEqual(game.code[36:len(game.original)], game.original[36:])
        with self.assertRaises(ValueError):
            entry_targets(b'\0' * 40, 9)

    def test_appended_messages_preserve_unknown_native_control_codes(self):
        before = message_bank()
        after, first = append_messages(before, ['Enquête à Bonaugure.'])
        self.assertEqual(first, 2)
        self.assertEqual(encrypted_messages(before)[1], encrypted_messages(after)[1][:2])
        self.assertEqual(crypt_message(encrypted_messages(after)[1][2], 2), encode_text('Enquête à Bonaugure.'))

    def test_patch_checks_both_source_banks_and_only_changes_selected_members(self):
        script, text = original_script(), message_bank()
        definition = QUEST | {'script_bank': 1, 'text_bank': 1,
                              'source_script_sha256': hashlib.sha256(script).hexdigest(),
                              'source_text_sha256': hashlib.sha256(text).hexdigest()}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'quest.json'
            path.write_text(json.dumps(definition), encoding='utf-8')
            scripts, texts = archive([b'untouched', script]), archive([b'untouched', text])
            result, _ = apply_investigation(scripts, texts, path)
            for data in result.values():
                self.assertEqual(narc_members(data)[0][0], b'untouched')
            with self.assertRaisesRegex(ValueError, 'originales compatibles'):
                apply_investigation(archive([b'untouched', script + b'bad']), texts, path)
            with self.assertRaisesRegex(ValueError, 'originales compatibles'):
                apply_investigation(scripts, archive([b'untouched', text + b'bad']), path)


if __name__ == '__main__':
    unittest.main()
