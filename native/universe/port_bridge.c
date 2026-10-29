#include "port_bridge.h"
#include "include/universe.h"
#include <stdio.h>
#include <string.h>

static UnivBattle sBattle;
static const void *sActiveContext;
static unsigned long sBattleNumber;

void Universe_PortStartup(void)
{
    printf("[Universe] Native registry linked: %lu forms; battle hooks installed.\n",
           (unsigned long)univ_species_count());
    fflush(stdout);
}

void Universe_BattleBegin(const void *context)
{
    if (!context) return;
    if (sActiveContext) {
        fputs("[Universe] Battle context overlap; no context replaced.\n", stderr);
        return;
    }
    sActiveContext = context;
    ++sBattleNumber;
    univ_battle_init(&sBattle);
    printf("[Universe] Battle %lu: native extension state initialized.\n", sBattleNumber);
    fflush(stdout);
}

void Universe_BattleEnd(const void *context)
{
    if (sActiveContext != context || !context) return;
    memset(&sBattle, 0, sizeof(sBattle));
    sActiveContext = NULL;
    printf("[Universe] Battle %lu: native extension state released.\n", sBattleNumber);
    fflush(stdout);
}

int Universe_PortSelfTest(void)
{
    UnivBattle battle;
    UnivBattleMon mon;
    const UnivTraining training = {50, 13, {31, 31, 31, 31, 31, 31}, {0, 252, 0, 0, 4, 252}};
    const uint16_t expected[6] = {153, 182, 131, 135, 106, 167};
    uint16_t stats[6], hp;
    const UnivSpecies *victini = univ_species_find("victini");
    const UnivSpecies *za = univ_species_find("garchompmegaz");
    if (univ_species_count() != 1329 || !victini || victini->national_dex != 494 || !za || !za->mega)
        return 10;
    univ_battle_init(&battle);
    if (univ_mon_init(&mon, "charizard", 0) != UNIV_OK) return 11;
    if (univ_mega_try(&battle, &mon, "charizardmegax", 1, 1, "charizarditex", NULL, 0) != UNIV_OK)
        return 12;
    if (univ_calculate_stats(mon.current, &training, stats) != UNIV_OK ||
        memcmp(stats, expected, sizeof(stats))) return 14;
    if (univ_adjust_hp(120, 153, stats[0], &hp) != UNIV_OK || hp != 120) return 15;
    univ_mega_end(&mon);
    if (strcmp(mon.current->id, "charizard") || !battle.mega_used[0]) return 13;
    puts("{\"universe_native_linked\":true,\"registry_forms\":1329,\"mega_rules\":\"passed\",\"stats_rules\":\"passed\",\"graphical_battle_tested\":false}");
    fflush(stdout);
    return 0;
}
