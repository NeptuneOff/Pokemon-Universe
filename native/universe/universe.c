#include "include/universe.h"
#include <string.h>
#include "generated/catalog.inc"

size_t univ_species_count(void) { return sizeof(catalog) / sizeof(catalog[0]); }

const UnivSpecies *univ_species_find(const char *id)
{
    size_t lo = 0, hi = univ_species_count();
    if (!id) return NULL;
    while (lo < hi) {
        size_t mid = lo + (hi - lo) / 2;
        int order = strcmp(id, catalog[mid].id);
        if (order == 0) return &catalog[mid];
        if (order < 0) hi = mid; else lo = mid + 1;
    }
    return NULL;
}

UnivResult univ_calculate_stats(const UnivSpecies *species, const UnivTraining *training,
                                uint16_t output[6])
{
    static const uint8_t nature_axes[5] = {1, 2, 5, 3, 4};
    uint16_t result[6];
    unsigned i, total_ev = 0, raised, lowered;
    if (!species || !training || !output || training->level < 1 ||
        training->level > 100 || training->nature > 24) return UNIV_INVALID;
    for (i = 0; i < 6; ++i) {
        if (training->iv[i] > 31 || species->base_stats[i] == 0) return UNIV_INVALID;
        total_ev += training->ev[i];
    }
    /* Gen IV saves can contain 255 EV in a stat; division by four gives the
     * same contribution as 252. Keep compatibility with those legal saves. */
    if (total_ev > 510) return UNIV_INVALID;
    raised = nature_axes[training->nature / 5];
    lowered = nature_axes[training->nature % 5];
    for (i = 0; i < 6; ++i) {
        uint32_t value = ((uint32_t)2 * species->base_stats[i] + training->iv[i]
                          + training->ev[i] / 4) * training->level / 100;
        if (i == 0) {
            value = species->national_dex == 292 ? 1 : value + training->level + 10;
        } else {
            value += 5;
            if (raised != lowered) {
                if (i == raised) value = value * 110 / 100;
                if (i == lowered) value = value * 90 / 100;
            }
        }
        if (value > UINT16_MAX) return UNIV_INVALID;
        result[i] = (uint16_t)value;
    }
    memcpy(output, result, sizeof(result));
    return UNIV_OK;
}

UnivResult univ_adjust_hp(uint16_t current, uint16_t old_max, uint16_t new_max,
                          uint16_t *output)
{
    int value;
    if (!output || !old_max || !new_max || current > old_max) return UNIV_INVALID;
    if (!current) { *output = 0; return UNIV_OK; }
    value = (int)current + (int)new_max - (int)old_max;
    if (value < 1) value = 1;
    if (value > new_max) value = new_max;
    *output = (uint16_t)value;
    return UNIV_OK;
}

void univ_battle_init(UnivBattle *battle)
{
    if (battle) memset(battle, 0, sizeof(*battle));
}

UnivResult univ_mon_init(UnivBattleMon *mon, const char *id, unsigned trainer)
{
    const UnivSpecies *species = univ_species_find(id);
    if (!mon || !species || species->mega || trainer > 1) return UNIV_INVALID;
    mon->current = species;
    mon->original = NULL;
    mon->trainer = (uint8_t)trainer;
    return UNIV_OK;
}

UnivResult univ_mega_try(UnivBattle *battle, UnivBattleMon *mon, const char *target_id,
                        int alive, int has_keystone, const char *held_item,
                        const char *const *known_moves, size_t move_count)
{
    const UnivSpecies *target = univ_species_find(target_id);
    size_t i;
    int eligible = 0, knows_move = 0;
    if (!battle || !mon || !mon->current || mon->trainer > 1 || !target ||
        move_count > 4 || (move_count && !known_moves)) return UNIV_INVALID;
    if (!target->mega) return UNIV_NOT_MEGA;
    if (!alive) return UNIV_FAINTED;
    if (!has_keystone) return UNIV_NO_KEYSTONE;
    if (battle->mega_used[mon->trainer] || mon->original || mon->current->mega) return UNIV_ALREADY_USED;
    for (i = 0; i < 4; ++i)
        if (!strcmp(mon->current->id, target->eligible_from[i])) eligible = 1;
    if (!eligible) return UNIV_WRONG_FORM;
    if (target->required_item[0] && (!held_item || strcmp(held_item, target->required_item))) return UNIV_MISSING_ITEM;
    if (target->required_move[0]) {
        for (i = 0; i < move_count; ++i)
            if (known_moves[i] && !strcmp(known_moves[i], target->required_move)) knows_move = 1;
        if (!knows_move) return UNIV_MISSING_MOVE;
    }
    /* The future combat adapter must apply stat, HP and ability changes. */
    mon->original = mon->current;
    mon->current = target;
    battle->mega_used[mon->trainer] = 1;
    return UNIV_OK;
}

void univ_mega_end(UnivBattleMon *mon)
{
    if (mon && mon->original) { mon->current = mon->original; mon->original = NULL; }
    /* Reverting a form does not grant another Mega in the same battle. */
}

const char *univ_result_name(UnivResult result)
{
    static const char *names[] = {"ok", "invalid", "not_mega", "wrong_form", "fainted",
        "no_keystone", "already_used", "missing_item", "missing_move"};
    if ((unsigned)result >= sizeof(names) / sizeof(names[0])) return "unknown";
    return names[result];
}
