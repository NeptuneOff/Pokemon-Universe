"""Compile and execute the C component. These tests do not run the PC game."""
import gzip
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tests.native.native_harness import run_native
from tools.native.build_expansion_catalog import compile_catalog, c_catalog
from tools.native.rebuild_expansion import ROOT, rebuild


class ExpansionTests(unittest.TestCase):
    def test_generated_catalog_is_reproducible_from_pinned_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            counts = rebuild(ROOT / 'content/native/expansion/sources', folder)
            self.assertEqual(counts, {'national_species': 1025, 'forms': 1329, 'mega_forms': 97})
            for name, target in [('catalog.json', 'content/native/expansion/catalog.json'),
                                 ('catalog.inc', 'native/universe/generated/catalog.inc')]:
                self.assertEqual((Path(folder) / name).read_bytes(), (ROOT / target).read_bytes().replace(b'\r\n', b'\n'))

    def test_corrupt_source_is_refused_before_generation(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'sources'
            shutil.copytree(ROOT / 'content/native/expansion/sources', source)
            (source / 'pokedex.ts.gz').write_bytes(gzip.compress(b'changed data'))
            output = Path(folder) / 'output'
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                rebuild(source, output)
            self.assertFalse(output.exists())

    def test_all_species_french_names_and_special_mega_forms_are_present(self):
        catalog = json.loads((ROOT / 'content/native/expansion/catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(c_catalog(catalog), (ROOT / 'native/universe/generated/catalog.inc').read_text(encoding='utf-8'))
        entries = {e['id']: e for e in catalog['entries']}
        bases = {e['national_dex']: e for e in entries.values() if e['id'] == e['base_id']}
        self.assertEqual(set(bases), set(range(1, 1026)))
        self.assertEqual(sum(e['mega'] for e in entries.values()), 97)
        self.assertIsNone(entries['victini']['legacy_native_species_id'])
        self.assertEqual(entries['arceus']['legacy_native_species_id'], 493)
        for name in ('meowsticfmega', 'magearnaoriginalmega', 'tatsugiridroopymega', 'garchompmegaz'):
            self.assertTrue(entries[name]['mega'])
        for name in ('charizardgmax', 'kyogreprimal', 'necrozmaultra'):
            self.assertNotIn(name, entries)
        for e in entries.values():
            self.assertTrue(e['name_fr'])
            if e['mega']:
                for before in e['requirements']['from']:
                    self.assertIn(before, entries)
                    self.assertEqual(entries[before]['national_dex'], e['national_dex'])

    def test_compiler_refuses_incomplete_or_inconsistent_data(self):
        base = {'num': 1, 'name': 'Bulbasaur', 'types': ['Grass', 'Poison'],
                'baseStats': dict.fromkeys(('hp', 'atk', 'def', 'spa', 'spd', 'spe'), 45),
                'abilities': {'0': 'Overgrow'}}
        source = {'bulbasaur': base}
        self.assertEqual(compile_catalog(source, {1: 'Bulbizarre'}, {})['counts']['national_species'], 1)
        with self.assertRaisesRegex(ValueError, 'French'):
            compile_catalog(source, {}, {})
        base['num'] = 2
        with self.assertRaisesRegex(ValueError, 'gaps'):
            compile_catalog(source, {2: 'Herbizarre'}, {})
        base['num'] = 1
        base['baseStats']['hp'] = -1
        with self.assertRaisesRegex(ValueError, 'stats'):
            compile_catalog(source, {1: 'Bulbizarre'}, {})
        base['baseStats']['hp'] = 45
        source['bulbasaurmega'] = {**base, 'name': 'Bulbasaur-Mega', 'baseSpecies': 'Bulbasaur',
                                 'forme': 'Mega', 'requiredItem': 'Testite', 'battleOnly': 'Missing'}
        with self.assertRaisesRegex(ValueError, 'source form'):
            compile_catalog(source, {1: 'Bulbizarre'}, {})
        source['bulbasaurmega']['battleOnly'] = 'Bulbasaur'
        del source['bulbasaurmega']['requiredItem']
        with self.assertRaisesRegex(ValueError, 'requirements'):
            compile_catalog(source, {1: 'Bulbizarre'}, {})

    def test_c_rules_all_mega_variants_failure_atomicity_and_two_trainers(self):
        catalog = json.loads((ROOT / 'content/native/expansion/catalog.json').read_text(encoding='utf-8'))
        cases = []
        for e in catalog['entries']:
            if e['mega']:
                for before in e['requirements']['from']:
                    cases.append([before, e['id'], e['requirements']['item'] or '', e['requirements']['move'] or ''])
        rows = ',\n'.join('{' + ','.join(json.dumps(x) for x in row) + '}' for row in cases)
        source = r'''
#include "universe.h"
#include "port_bridge.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); return 1; } } while (0)
static const char *cases[][4] = { ROWS };
static int test_stats(void) {
    UnivTraining training = {50, 13, {31, 31, 31, 31, 31, 31}, {0, 252, 0, 0, 4, 252}};
    const uint16_t charizard_x[6] = {153, 182, 131, 135, 106, 167};
    const uint16_t slowbro_mega[6] = {202, 85, 255, 150, 101, 50};
    uint16_t stats[6], before[6], hp;
    UnivSpecies oversized = *univ_species_find("bulbasaur");
    CHECK(univ_calculate_stats(univ_species_find("charizardmegax"), &training, stats) == UNIV_OK);
    CHECK(!memcmp(stats, charizard_x, sizeof(stats)));
    training.ev[1] = 255; training.ev[4] = 0;
    CHECK(univ_calculate_stats(univ_species_find("charizardmegax"), &training, stats) == UNIV_OK);
    CHECK(stats[1] == 182 && stats[5] == 167);
    training.nature = 5;
    memset(training.ev, 0, sizeof(training.ev));
    training.ev[0] = 252; training.ev[2] = 252; training.ev[4] = 4;
    CHECK(univ_calculate_stats(univ_species_find("slowbro"), &training, before) == UNIV_OK);
    CHECK(before[0] == 202 && before[2] == 178 && before[3] == 120);
    CHECK(univ_calculate_stats(univ_species_find("slowbromega"), &training, stats) == UNIV_OK);
    CHECK(!memcmp(stats, slowbro_mega, sizeof(stats)));
    training.level = 1; training.nature = 0;
    memset(training.iv, 0, sizeof(training.iv));
    memset(training.ev, 0, sizeof(training.ev));
    CHECK(univ_calculate_stats(univ_species_find("bulbasaur"), &training, stats) == UNIV_OK);
    CHECK(stats[0] == 11 && stats[1] == 5 && stats[2] == 5 && stats[3] == 6 && stats[4] == 6 && stats[5] == 5);
    CHECK(univ_calculate_stats(univ_species_find("shedinja"), &training, stats) == UNIV_OK && stats[0] == 1);
    training.level = 100;
    CHECK(univ_calculate_stats(univ_species_find("shedinja"), &training, stats) == UNIV_OK && stats[0] == 1);
    memcpy(before, stats, sizeof(stats));
    training.iv[0] = 32;
    CHECK(univ_calculate_stats(univ_species_find("slowbro"), &training, stats) == UNIV_INVALID);
    CHECK(!memcmp(before, stats, sizeof(stats)));
    training.iv[0] = 0; training.nature = 25;
    CHECK(univ_calculate_stats(univ_species_find("slowbro"), &training, stats) == UNIV_INVALID);
    training.nature = 0; training.level = 0;
    CHECK(univ_calculate_stats(univ_species_find("slowbro"), &training, stats) == UNIV_INVALID);
    training.level = 101;
    CHECK(univ_calculate_stats(univ_species_find("slowbro"), &training, stats) == UNIV_INVALID);
    training.level = 100;
    memset(training.ev, 255, sizeof(training.ev));
    CHECK(univ_calculate_stats(univ_species_find("slowbro"), &training, stats) == UNIV_INVALID);
    memset(training.ev, 0, sizeof(training.ev));
    oversized.base_stats[1] = UINT16_MAX;
    CHECK(univ_calculate_stats(&oversized, &training, stats) == UNIV_INVALID);
    CHECK(!memcmp(before, stats, sizeof(stats)));
    CHECK(univ_calculate_stats(NULL, &training, stats) == UNIV_INVALID);
    CHECK(univ_calculate_stats(univ_species_find("slowbro"), NULL, stats) == UNIV_INVALID);
    CHECK(univ_calculate_stats(univ_species_find("slowbro"), &training, NULL) == UNIV_INVALID);
    CHECK(univ_adjust_hp(120, 153, 252, &hp) == UNIV_OK && hp == 219);
    CHECK(univ_adjust_hp(200, 252, 153, &hp) == UNIV_OK && hp == 101);
    CHECK(univ_adjust_hp(1, 252, 153, &hp) == UNIV_OK && hp == 1);
    CHECK(univ_adjust_hp(0, 252, 153, &hp) == UNIV_OK && hp == 0);
    CHECK(univ_adjust_hp(153, 153, 252, &hp) == UNIV_OK && hp == 252);
    CHECK(univ_adjust_hp(154, 153, 252, &hp) == UNIV_INVALID && hp == 252);
    CHECK(univ_adjust_hp(1, 0, 252, &hp) == UNIV_INVALID && hp == 252);
    CHECK(univ_adjust_hp(1, 153, 0, &hp) == UNIV_INVALID && hp == 252);
    CHECK(univ_adjust_hp(1, 153, 252, NULL) == UNIV_INVALID);
    training.level = 50;
    memset(training.iv, 31, sizeof(training.iv));
    CHECK(univ_calculate_stats(univ_species_find("zygarde"), &training, before) == UNIV_OK && before[0] == 183);
    CHECK(univ_calculate_stats(univ_species_find("zygardemega"), &training, stats) == UNIV_OK && stats[0] == 291);
    CHECK(univ_adjust_hp(100, before[0], stats[0], &hp) == UNIV_OK && hp == 208);
    puts("native battle stat calculations passed");
    return 0;
}
int main(void) {
    size_t i;
    int first_context = 0, next_context = 0;
    UnivBattle battle;
    UnivBattleMon left, right;
    const char *dragon_ascent[] = {"dragonascent"};
    CHECK(test_stats() == 0);
    CHECK(univ_species_count() == 1329);
    CHECK(univ_species_find(NULL) == NULL && univ_species_find("missing") == NULL);
    CHECK(univ_species_find("victini")->national_dex == 494);
    CHECK(univ_species_find("charizardmegax")->base_stats[1] == 130);
    CHECK(univ_species_find("gardevoirmega")->types[1] == 18);
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        const char *moves[] = {cases[i][3]};
        univ_battle_init(&battle);
        CHECK(univ_mon_init(&left, cases[i][0], 0) == UNIV_OK);
        CHECK(univ_mon_init(&right, cases[i][0], 1) == UNIV_OK);
        CHECK(univ_mega_try(&battle, &left, cases[i][1], 1, 1, cases[i][2], moves, 1) == UNIV_OK);
        CHECK(left.current->mega && left.original && battle.mega_used[0] && !battle.mega_used[1]);
        CHECK(univ_mega_try(&battle, &right, cases[i][1], 1, 1, cases[i][2], moves, 1) == UNIV_OK);
        CHECK(battle.mega_used[0] && battle.mega_used[1]);
        univ_mega_end(&left);
        CHECK(!strcmp(left.current->id, cases[i][0]) && !left.original);
        CHECK(univ_mega_try(&battle, &left, cases[i][1], 1, 1, cases[i][2], moves, 1) == UNIV_ALREADY_USED);
        univ_mega_end(&right);
        CHECK(!strcmp(right.current->id, cases[i][0]));
    }
    univ_battle_init(&battle);
    CHECK(univ_mon_init(&left, "charizard", 0) == UNIV_OK);
    CHECK(univ_mon_init(&right, "venusaur", 1) == UNIV_OK);
    CHECK(univ_mega_try(&battle, &left, "charizardmegax", 1, 1, "wrong", NULL, 0) == UNIV_MISSING_ITEM);
    CHECK(!battle.mega_used[0] && !left.original && !strcmp(left.current->id, "charizard"));
    CHECK(univ_mega_try(&battle, &left, "charizardmegax", 0, 1, "charizarditex", NULL, 0) == UNIV_FAINTED);
    CHECK(univ_mega_try(&battle, &left, "charizardmegax", 1, 0, "charizarditex", NULL, 0) == UNIV_NO_KEYSTONE);
    CHECK(univ_mega_try(&battle, &left, "venusaurmega", 1, 1, "venusaurite", NULL, 0) == UNIV_WRONG_FORM);
    CHECK(univ_mega_try(&battle, &left, "charizard", 1, 1, "", NULL, 0) == UNIV_NOT_MEGA);
    CHECK(!battle.mega_used[0] && !left.original);
    CHECK(univ_mon_init(&left, "rayquaza", 0) == UNIV_OK);
    CHECK(univ_mega_try(&battle, &left, "rayquazamega", 1, 1, "", NULL, 0) == UNIV_MISSING_MOVE);
    CHECK(univ_mega_try(&battle, &left, "rayquazamega", 1, 1, "", dragon_ascent, 1) == UNIV_OK);
    CHECK(univ_mega_try(&battle, &right, "venusaurmega", 1, 1, "venusaurite", NULL, 0) == UNIV_OK);
    univ_mega_end(&left);
    univ_mega_end(&right);
    univ_battle_init(&battle);
    CHECK(univ_mon_init(&left, "floette", 0) == UNIV_OK);
    CHECK(univ_mega_try(&battle, &left, "floettemega", 1, 1, "floettite", NULL, 0) == UNIV_WRONG_FORM);
    CHECK(univ_mon_init(&left, "floetteeternal", 0) == UNIV_OK);
    CHECK(univ_mega_try(&battle, &left, "floettemega", 1, 1, "floettite", NULL, 0) == UNIV_OK);
    CHECK(univ_mon_init(&right, "venusaurmega", 0) == UNIV_INVALID);
    CHECK(univ_mon_init(&right, "venusaur", 2) == UNIV_INVALID);
    CHECK(univ_mega_try(NULL, &left, "floettemega", 1, 1, "", NULL, 0) == UNIV_INVALID);
    CHECK(!strcmp(univ_result_name(UNIV_MISSING_ITEM), "missing_item"));
    CHECK(!strcmp(univ_result_name((UnivResult)99), "unknown"));
    Universe_BattleBegin(&first_context);
    Universe_PortStartup();
    Universe_BattleBegin(&next_context);
    Universe_BattleEnd(&next_context);
    puts("native registry and Mega rules passed");
    return 0;
}
'''.replace('ROWS', rows)
        run = run_native(source)
        self.assertIn('Mega rules passed', run.stdout)
        self.assertIn('battle stat calculations passed', run.stdout)
        self.assertEqual(run.stdout.count('native extension state initialized.'), 2)
        self.assertEqual(run.stdout.count('native extension state released.'), 1)
        self.assertNotIn('overlap', run.stderr)
