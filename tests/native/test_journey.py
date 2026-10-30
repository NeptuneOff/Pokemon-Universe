import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from tests.native.native_harness import ROOT, run_native
from tools.native.build_start_options import compile_partners, c_partners


class JourneyTests(unittest.TestCase):
    def definition(self):
        return json.loads((ROOT / 'content/native/start-options.fr.json').read_text(encoding='utf-8'))

    def test_partner_lines_are_non_starters_with_real_evolutions_and_a_matching_stone(self):
        config = self.definition()
        catalog = {e['id']: e for e in json.loads((ROOT / 'content/native/expansion/catalog.json').read_text(encoding='utf-8'))['entries']}
        starters = {e['id'] for pool in config['classic_pools'].values() for e in pool}
        self.assertEqual(len(starters), 27)
        for slot, expected_type in zip(config['classic_order'], ('Grass', 'Fire', 'Water')):
            self.assertEqual(len(config['classic_pools'][slot]), 9)
            for option in config['classic_pools'][slot]:
                mon = catalog[option['id']]
                self.assertIn(expected_type, mon['types'])
                self.assertFalse(mon['mega'])
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'pokedex.json'
            result = subprocess.run(['node', str(ROOT / 'tools/native/read_showdown.mjs'),
                str(ROOT / 'content/native/expansion/sources/pokedex.ts.gz'), str(output)],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            dex = json.loads(output.read_text())
        self.assertEqual(compile_partners(dex, {'entries': list(catalog.values())}, config['classic_pools']), config['partner_choices'])
        self.assertEqual((ROOT / 'native/universe/generated/journey.inc').read_text(), c_partners(config['partner_choices']))
        self.assertEqual(config['partner_draw']['families'], 48)
        self.assertEqual(len(config['partner_choices']), 53)
        for partner in config['partner_choices']:
            chain = partner['evolution_chain']
            self.assertGreaterEqual(len(chain), 2)
            self.assertNotIn(chain[0], starters)
            self.assertFalse(dex[chain[-1]].get('evos'))
            for previous, following in zip(chain, chain[1:]):
                prevo = re.sub('[^a-z0-9]', '', dex[following]['prevo'].lower())
                self.assertEqual(prevo, previous)
            mega = catalog[partner['mega_id']]
            self.assertTrue(mega['mega'])
            self.assertIn(chain[-1], mega['requirements']['from'])
            self.assertEqual(mega['requirements']['item'], partner['stone_id'])

    def test_c_draws_save_round_trip_order_and_single_partner_delivery(self):
        config = self.definition()
        rows = ','.join('{' + ','.join(json.dumps(e['id']) for e in config['classic_pools'][slot]) + '}'
                        for slot in config['classic_order'])
        partner_rows = ','.join('{' + ','.join(json.dumps(v) for v in (p['evolution_chain'][0],
                        p['evolution_chain'][-1], p['mega_id'], p['stone_id'], p['required_gender'] or '-')) + '}' for p in config['partner_choices'])
        source = r'''
#include "universe.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); return 1; } } while (0)
static const char *expected[3][9] = { STARTERS };
static const char *partners[][5] = { PARTNERS };
typedef struct { int accept, calls; const char *pokemon, *stone; } Delivery;
static int deliver(void *context, const UnivPartnerGift *gift) {
    Delivery *d = context;
    d->calls++;
    if (!d->accept) return 0;
    d->pokemon = gift->pokemon->id;
    d->stone = gift->stone_id;
    return 1;
}
int main(void) {
    UnivJourney left, right, saved, before;
    uint8_t bytes[UNIV_JOURNEY_BYTES], changed[UNIV_JOURNEY_BYTES];
    unsigned seed, type, i, k, seen[3][9] = {{0}}, partners_seen[sizeof(partners)/sizeof(partners[0])] = {0};
    UnivPartnerGift gift;
    Delivery delivery = {0, 0, NULL, NULL};
    CHECK(univ_partner_count() == sizeof(partners)/sizeof(partners[0]));
    for (seed = 0; seed < 512; ++seed) {
        CHECK(univ_journey_begin(&left, seed, 0) == UNIV_OK);
        CHECK(univ_journey_begin(&right, seed, 1) == UNIV_OK);
        for (type = 0; type < 3; ++type) {
            CHECK(left.options[type] < 9 && right.options[type] < 9);
            CHECK(left.options[type] != right.options[type]);
            CHECK(!strcmp(univ_journey_option(&left, type)->id, expected[type][left.options[type]]));
            CHECK(!strcmp(univ_journey_option(&right, type)->id, expected[type][right.options[type]]));
            seen[type][left.options[type]]++;
            seen[type][right.options[type]]++;
        }
        for (i = 0; i < 6; ++i) {
            UnivPartnerGift offer, other;
            CHECK(univ_journey_partner_option(i < 3 ? &left : &right, i % 3, &offer) == UNIV_OK);
            for (k = 0; k < univ_partner_count(); ++k) {
                CHECK(univ_partner_option(k, &other) == UNIV_OK);
                if (other.key == offer.key) partners_seen[k]++;
            }
            for (k = 0; k < i; ++k) {
                CHECK(univ_journey_partner_option(k < 3 ? &left : &right, k % 3, &other) == UNIV_OK);
                CHECK(strcmp(offer.pokemon->id, other.pokemon->id));
            }
        }
    }
    for (type = 0; type < 3; ++type) for (i = 0; i < 9; ++i) CHECK(seen[type][i] > 0);
    for (i = 0; i < univ_partner_count(); ++i) CHECK(partners_seen[i] > 0);
    CHECK(univ_journey_begin(&left, 98765, 0) == UNIV_OK);
    before = left;
    CHECK(univ_journey_choose_partner(&left, 0) == UNIV_WRONG_STAGE);
    CHECK(!memcmp(&left, &before, sizeof(left)));
    CHECK(univ_journey_receive_partner(&left, deliver, &delivery) == UNIV_WRONG_STAGE);
    CHECK(delivery.calls == 0);
    CHECK(univ_journey_choose_primary(&left, 1) == UNIV_OK);
    CHECK(univ_journey_choose_primary(&left, 0) == UNIV_ALREADY_CHOSEN && left.primary == 1);
    CHECK(univ_journey_encode(&left, bytes, sizeof(bytes)) == UNIV_OK);
    CHECK(univ_journey_decode(&saved, bytes, sizeof(bytes)) == UNIV_OK);
    CHECK(!memcmp(&saved, &left, sizeof(saved)));
    CHECK(!strcmp(univ_journey_option(&saved, 1)->id, univ_journey_option(&left, 1)->id));
    CHECK(univ_journey_choose_partner(&left, 2) == UNIV_OK);
    CHECK(univ_journey_choose_partner(&left, 1) == UNIV_ALREADY_CHOSEN && left.partner == 2);
    before = left;
    CHECK(univ_journey_receive_partner(&left, deliver, &delivery) == UNIV_DELIVERY_FAILED);
    CHECK(!memcmp(&before, &left, sizeof(left)) && delivery.calls == 1);
    delivery.accept = 1;
    CHECK(univ_journey_receive_partner(&left, deliver, &delivery) == UNIV_OK);
    CHECK(left.partner_received == 1 && delivery.calls == 2);
    CHECK(univ_journey_partner_option(&left, left.partner, &gift) == UNIV_OK);
    CHECK(!strcmp(delivery.pokemon, gift.pokemon->id) && !strcmp(delivery.stone, gift.stone_id));
    CHECK(univ_journey_receive_partner(&left, deliver, &delivery) == UNIV_ALREADY_CHOSEN && delivery.calls == 2);
    CHECK(univ_journey_encode(&left, bytes, sizeof(bytes)) == UNIV_OK);
    CHECK(univ_journey_decode(&saved, bytes, sizeof(bytes)) == UNIV_OK && saved.partner_received == 1);
    for (i = 0; i < sizeof(bytes); ++i) {
        before = saved;
        memcpy(changed, bytes, sizeof(bytes)); changed[i] ^= 1;
        CHECK(univ_journey_decode(&saved, changed, sizeof(changed)) == UNIV_INVALID);
        CHECK(!memcmp(&saved, &before, sizeof(saved)));
    }
    for (i = 0; i < univ_partner_count(); ++i) {
        UnivBattle battle;
        UnivBattleMon mon;
        CHECK(univ_partner_option(i, &gift) == UNIV_OK);
        CHECK(!strcmp(gift.pokemon->id, partners[i][0]));
        CHECK(!strcmp(gift.final_form->id, partners[i][1]));
        CHECK(!strcmp(gift.mega->id, partners[i][2]));
        CHECK(!strcmp(gift.stone_id, partners[i][3]));
        CHECK(gift.required_gender == partners[i][4][0]);
        univ_battle_init(&battle);
        CHECK(univ_mon_init(&mon, gift.pokemon->id, 0) == UNIV_OK);
        CHECK(univ_mega_try(&battle, &mon, gift.mega->id, 1, 1, gift.stone_id, NULL, 0) == UNIV_WRONG_FORM);
        CHECK(!battle.mega_used[0]);
        CHECK(univ_mon_init(&mon, gift.final_form->id, 0) == UNIV_OK);
        CHECK(univ_mega_try(&battle, &mon, gift.mega->id, 1, 1, gift.stone_id, NULL, 0) == UNIV_OK);
    }
    {
        uint8_t legacy[16] = {'U','J','P','1',0,0,1,1,0,1,2,0};
        uint32_t sum = UINT32_C(2166136261);
        for (i = 0; i < 12; ++i) sum = (sum ^ legacy[i]) * UINT32_C(16777619);
        for (i = 0; i < 4; ++i) legacy[12+i] = (uint8_t)(sum >> (8*i));
        CHECK(univ_journey_decode(&saved, legacy, 16) == UNIV_OK);
        CHECK(saved.partner_received && saved.partner == 1);
        CHECK(univ_journey_partner_option(&saved, 1, &gift) == UNIV_OK);
        CHECK(!strcmp(gift.pokemon->id, "mareep"));
        CHECK(univ_journey_encode(&saved, bytes, sizeof(bytes)) == UNIV_OK);
        CHECK(!memcmp(bytes, "UJP2", 4));
    }
    CHECK(univ_partner_option((unsigned)univ_partner_count(), &gift) == UNIV_INVALID);
    CHECK(univ_partner_option(0, NULL) == UNIV_INVALID);
    CHECK(univ_journey_begin(&left, 1, 2) == UNIV_INVALID);
    CHECK(univ_journey_begin(NULL, 1, 0) == UNIV_INVALID);
    CHECK(univ_journey_choose_primary(&left, 3) == UNIV_INVALID);
    CHECK(univ_journey_option(&left, 3) == NULL);
    CHECK(univ_journey_decode(&left, bytes, sizeof(bytes) - 1) == UNIV_INVALID);
    CHECK(univ_journey_encode(&left, changed, sizeof(changed) - 1) == UNIV_INVALID);
    puts("journey draws, saved choices and partner gift contract passed");
    return 0;
}
'''.replace('STARTERS', rows).replace('PARTNERS', partner_rows)
        run = run_native(source)
        self.assertIn('partner gift contract passed', run.stdout)
