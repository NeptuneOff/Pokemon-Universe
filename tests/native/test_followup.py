"""Exercise a quest crossing map banks and the existing native save variables."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_investigation import EventRunner, QUEST, original_script
from test_resources import archive, message_bank
from tools.native.patch_intro import ROOT, narc_members
from tools.native.patch_investigation import apply_followup

LAB = json.loads((ROOT / 'content/native/littorella-labo.fr.json').read_text(encoding='utf-8'))
TOWN = json.loads((ROOT / 'content/native/littorella-temoin.fr.json').read_text(encoding='utf-8'))


def change_map(game, quest):
    # New interpreter, only native persistent variables and inventory survive.
    return EventRunner(state=game.state, potions=game.potions, quest=quest,
                       first_message=61 if quest is LAB else 30, inventory=game.inventory)


class FollowupTests(unittest.TestCase):
    def test_pokedex_intro_transitions_and_unrelated_events_stay_byte_identical(self):
        for quest in (LAB, TOWN):
            game = EventRunner(quest=quest)
            redirected = {int(index) for index in quest['entries']}
            for index in range(game.count):
                if index not in redirected:
                    self.assertEqual(game.code[4 * index:4 * index + 4],
                                     game.original[4 * index:4 * index + 4])
            self.assertEqual(game.code[game.count * 4:len(game.original)],
                             game.original[game.count * 4:])

    def finished_bonaugure(self, role, variant):
        game = EventRunner(variant)
        game.run(4, [role - 1])
        game.run(6 if role == 1 else 5, [variant if role == 1 else 0])
        game.run(4)
        self.assertEqual(game.potions, 1)
        return game

    def test_both_roles_and_reports_cross_maps_and_reward_once_after_reload(self):
        for role in (1, 2):
            for variant in (0, 1):
                with self.subTest(role=role, variant=variant):
                    prior = self.finished_bonaugure(role, variant)
                    lab = change_map(prior, LAB)
                    lab.run(2, [0])
                    self.assertTrue(lab.saw('intro_east' if variant == 0 else 'intro_west'))
                    self.assertTrue(lab.saw('analyst_task' if role == 1 else 'scout_task'))
                    self.assertEqual(lab.value('followup'), 1)
                    lab.run(2, [0])
                    self.assertFalse(lab.saw('intro_east') or lab.saw('intro_west'))
                    if role == 1:
                        wrong = change_map(lab, TOWN)
                        wrong.run(4)
                        self.assertTrue(wrong.fallback)
                        evidence = change_map(lab, LAB)
                        evidence.run(11, [0])
                    else:
                        lab.run(11)
                        self.assertTrue(lab.fallback)
                        evidence = change_map(lab, TOWN)
                        evidence.run(4, [0])
                    self.assertEqual(evidence.value('followup'), 2)
                    restored = change_map(evidence, LAB)
                    restored.run(2, [0])
                    self.assertTrue(restored.saw('analyst_report' if role == 1 else 'scout_report'))
                    self.assertTrue(restored.saw('conclusion_east' if variant == 0 else 'conclusion_west'))
                    self.assertEqual((restored.value('followup'), restored.inventory[4]), (3, 3))
                    self.assertEqual(restored.inventory[17], 1)
                    restored = change_map(restored, LAB)
                    restored.run(2, [0])
                    self.assertTrue(restored.saw('done_east' if variant == 0 else 'done_west'))
                    self.assertEqual(restored.inventory[4], 3)
                    # The original professor and PC remain accessible after the quest.
                    restored.run(2, [1])
                    self.assertTrue(restored.fallback)
                    restored.run(11)
                    self.assertTrue(restored.fallback)
                    town = change_map(restored, TOWN)
                    town.run(4)
                    self.assertTrue(town.fallback)
                    self.assertEqual(restored.random_calls, 0)
                    self.assertEqual(restored.value('variant'), variant)

    def test_no_early_reward_and_original_story_before_bonaugure_completion(self):
        for stage in (0, 1, 2):
            game = EventRunner(state={QUEST['variables']['stage']:stage}, quest=LAB)
            game.run(2)
            self.assertTrue(game.fallback)
            self.assertEqual(game.value('followup'), 0)
            self.assertEqual(game.inventory, {})
        for role in (1, 2):
            lab = change_map(self.finished_bonaugure(role, 0), LAB)
            lab.run(11)
            self.assertTrue(lab.fallback)
            town = change_map(lab, TOWN)
            town.run(4)
            self.assertTrue(town.fallback)
            lab.run(2, [1])
            self.assertTrue(lab.fallback)
            self.assertEqual(lab.value('followup'), 0)

    def test_cancels_wrong_answers_and_full_bag_keep_progress_retryable(self):
        for role in (1, 2):
            lab = change_map(self.finished_bonaugure(role, 1), LAB)
            for cancel in (2, 0xfffe):
                lab.run(2, [cancel])
                self.assertEqual(lab.value('followup'), 0)
            lab.run(2, [0])
            evidence = change_map(lab, LAB if role == 1 else TOWN)
            entry = 11 if role == 1 else 4
            for answer in (2, 0xfffe, 1):
                evidence.run(entry, [answer])
                self.assertEqual(evidence.value('followup'), 1)
                self.assertNotIn(4, evidence.inventory)
            self.assertTrue(evidence.saw('wrong'))
            evidence.run(entry, [0])
            restored = change_map(evidence, LAB)
            restored.run(2, [0], bag_full=True)
            self.assertEqual(restored.value('followup'), 2)
            self.assertTrue(restored.saw('bag_full'))
            self.assertNotIn(4, restored.inventory)
            # Declining or consulting the Pokédex never loses the unclaimed reward.
            restored.run(2, [1])
            self.assertTrue(restored.fallback)
            self.assertEqual(restored.value('followup'), 2)
            restored.run(2, [0])
            restored.run(2, [0])
            self.assertEqual((restored.value('followup'), restored.inventory[4]), (3, 3))

    def test_both_banks_are_checked_before_the_caller_can_install_anything(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'content/native').mkdir(parents=True)
            originals = [original_script(15), original_script(12)]
            text = message_bank()
            for i, (quest, name) in enumerate(((LAB, 'littorella-labo.fr.json'), (TOWN, 'littorella-temoin.fr.json'))):
                definition = quest | {'script_bank':i, 'text_bank':i,
                    'source_script_sha256':hashlib.sha256(originals[i]).hexdigest(),
                    'source_text_sha256':hashlib.sha256(text).hexdigest()}
                (root / 'content/native' / name).write_text(json.dumps(definition), encoding='utf-8')
            scripts, texts = archive(originals + [b'untouched']), archive([text, text, b'untouched'])
            with patch('tools.native.patch_investigation.ROOT', root):
                patched, provenance = apply_followup(scripts, texts)
                self.assertEqual(len(provenance), 2)
                for content in patched.values():
                    self.assertEqual(narc_members(content)[0][2], b'untouched')
                with self.assertRaisesRegex(ValueError, 'originales compatibles'):
                    apply_followup(archive([originals[0], originals[1] + b'bad']), texts)
                with self.assertRaisesRegex(ValueError, 'originales compatibles'):
                    apply_followup(scripts, archive([text, text + b'bad']))
            self.assertEqual(narc_members(scripts)[0][:2], originals)
            self.assertEqual(narc_members(texts)[0][:2], [text, text])


if __name__ == '__main__':
    unittest.main()
