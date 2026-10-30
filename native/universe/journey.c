#include "include/universe.h"
#include <string.h>

/* Grass, Fire, Water; one initial form per main-series family, generations 1-9.
 * Hisui and Z-A reuse families already represented here. */
static const char *const starters[3][UNIV_STARTER_FAMILIES] = {
    {"bulbasaur", "chikorita", "treecko", "turtwig", "snivy", "chespin", "rowlet", "grookey", "sprigatito"},
    {"charmander", "cyndaquil", "torchic", "chimchar", "tepig", "fennekin", "litten", "scorbunny", "fuecoco"},
    {"squirtle", "totodile", "mudkip", "piplup", "oshawott", "froakie", "popplio", "sobble", "quaxly"}
};
typedef struct {
    uint32_t key;
    const char *root, *final, *mega;
    char gender;
} PartnerRecord;
typedef struct { unsigned first, count; } PartnerGroup;
#include "generated/journey.inc"

static const PartnerRecord *by_key(uint32_t key)
{
    unsigned i;
    for (i = 0; i < PARTNER_POOL_COUNT; ++i)
        if (partner_pool[i].key == key) return &partner_pool[i];
    return NULL;
}

static int valid(const UnivJourney *j)
{
    unsigned i;
    if (!j || j->version != 2 || j->player > 1 || j->partner_received > 1) return 0;
    for (i = 0; i < 3; ++i)
        if (j->options[i] >= UNIV_STARTER_FAMILIES) return 0;
    for (i = 0; i < UNIV_PARTNER_OPTIONS; ++i) {
        const PartnerRecord *p = by_key(j->partner_options[i]);
        unsigned k;
        if (!p) return 0;
        for (k = 0; k < i; ++k)
            if (!strcmp(p->root, by_key(j->partner_options[k])->root)) return 0;
    }
    if (j->primary != UNIV_NO_CHOICE && j->primary > 2) return 0;
    if (j->partner != UNIV_NO_CHOICE && j->partner >= UNIV_PARTNER_OPTIONS) return 0;
    if (j->primary == UNIV_NO_CHOICE && j->partner != UNIV_NO_CHOICE) return 0;
    if (j->partner == UNIV_NO_CHOICE && j->partner_received) return 0;
    return 1;
}

static uint32_t next(uint32_t *state)
{
    uint32_t value = *state;
    value ^= value << 13;
    value ^= value >> 17;
    value ^= value << 5;
    *state = value;
    return value;
}

static unsigned bounded(uint32_t *state, unsigned count)
{
    uint32_t value, limit = UINT32_MAX - UINT32_MAX % count;
    do { value = next(state) - 1; } while (value >= limit);
    return (unsigned)(value % count);
}

UnivResult univ_journey_begin(UnivJourney *journey, uint32_t seed, unsigned player)
{
    UnivJourney result;
    unsigned i, groups[PARTNER_ROOT_COUNT];
    uint32_t state = seed ? seed : UINT32_C(0x9e3779b9);
    if (!journey || player > 1) return UNIV_INVALID;
    memset(&result, 0, sizeof(result));
    result.version = 2;
    result.player = (uint8_t)player;
    result.primary = result.partner = UNIV_NO_CHOICE;
    for (i = 0; i < 3; ++i) {
        unsigned first = bounded(&state, UNIV_STARTER_FAMILIES);
        unsigned offset = 1 + bounded(&state, UNIV_STARTER_FAMILIES - 1);
        result.options[i] = (uint8_t)(player ? (first + offset) % UNIV_STARTER_FAMILIES : first);
    }
    /* Draw all six offers identically for both peers. Distinct root families
     * avoid duplicate Ralts branches and avoid weighting multi-Mega families. */
    for (i = 0; i < PARTNER_ROOT_COUNT; ++i) groups[i] = i;
    for (i = 0; i < 2 * UNIV_PARTNER_OPTIONS; ++i) {
        unsigned index = i + bounded(&state, PARTNER_ROOT_COUNT - i);
        unsigned temp = groups[i];
        const PartnerGroup *group;
        const PartnerRecord *record;
        groups[i] = groups[index]; groups[index] = temp;
        group = &partner_groups[groups[i]];
        record = &partner_pool[group->first + bounded(&state, group->count)];
        if (i / UNIV_PARTNER_OPTIONS == player)
            result.partner_options[i % UNIV_PARTNER_OPTIONS] = record->key;
    }
    *journey = result;
    return UNIV_OK;
}

const UnivSpecies *univ_journey_option(const UnivJourney *journey, unsigned type_slot)
{
    if (!valid(journey) || type_slot > 2) return NULL;
    return univ_species_find(starters[type_slot][journey->options[type_slot]]);
}

UnivResult univ_journey_choose_primary(UnivJourney *journey, unsigned type_slot)
{
    if (!valid(journey) || type_slot > 2) return UNIV_INVALID;
    if (journey->primary != UNIV_NO_CHOICE) return UNIV_ALREADY_CHOSEN;
    journey->primary = (uint8_t)type_slot;
    return UNIV_OK;
}

size_t univ_partner_count(void) { return PARTNER_POOL_COUNT; }

static UnivResult resolve_partner(const PartnerRecord *record, UnivPartnerGift *gift)
{
    UnivPartnerGift result;
    if (!gift || !record) return UNIV_INVALID;
    result.pokemon = univ_species_find(record->root);
    result.final_form = univ_species_find(record->final);
    result.mega = univ_species_find(record->mega);
    if (!result.pokemon || !result.final_form || !result.mega || !result.mega->mega ||
        !result.mega->required_item[0]) return UNIV_INVALID;
    result.stone_id = result.mega->required_item;
    result.key = record->key;
    result.required_gender = record->gender;
    *gift = result;
    return UNIV_OK;
}

UnivResult univ_partner_option(unsigned option, UnivPartnerGift *gift)
{
    if (option >= PARTNER_POOL_COUNT) return UNIV_INVALID;
    return resolve_partner(&partner_pool[option], gift);
}

UnivResult univ_journey_partner_option(const UnivJourney *journey, unsigned slot, UnivPartnerGift *gift)
{
    if (!valid(journey) || slot >= UNIV_PARTNER_OPTIONS) return UNIV_INVALID;
    return resolve_partner(by_key(journey->partner_options[slot]), gift);
}

UnivResult univ_journey_choose_partner(UnivJourney *journey, unsigned option)
{
    if (!valid(journey) || option >= UNIV_PARTNER_OPTIONS) return UNIV_INVALID;
    if (journey->primary == UNIV_NO_CHOICE) return UNIV_WRONG_STAGE;
    if (journey->partner != UNIV_NO_CHOICE) return UNIV_ALREADY_CHOSEN;
    journey->partner = (uint8_t)option;
    return UNIV_OK;
}

UnivResult univ_journey_receive_partner(UnivJourney *journey, UnivGiftApply apply, void *context)
{
    UnivPartnerGift gift;
    if (!valid(journey) || !apply) return UNIV_INVALID;
    if (journey->partner == UNIV_NO_CHOICE) return UNIV_WRONG_STAGE;
    if (journey->partner_received) return UNIV_ALREADY_CHOSEN;
    if (univ_journey_partner_option(journey, journey->partner, &gift) != UNIV_OK) return UNIV_INVALID;
    if (!apply(context, &gift)) return UNIV_DELIVERY_FAILED;
    journey->partner_received = 1;
    return UNIV_OK;
}

static uint32_t checksum(const uint8_t *bytes, unsigned count)
{
    unsigned i;
    uint32_t result = UINT32_C(2166136261);
    for (i = 0; i < count; ++i) result = (result ^ bytes[i]) * UINT32_C(16777619);
    return result;
}

static void write32(uint8_t *bytes, uint32_t value)
{
    unsigned i;
    for (i = 0; i < 4; ++i) bytes[i] = (uint8_t)(value >> (8 * i));
}

static uint32_t read32(const uint8_t *bytes)
{
    unsigned i;
    uint32_t value = 0;
    for (i = 0; i < 4; ++i) value |= (uint32_t)bytes[i] << (8 * i);
    return value;
}

UnivResult univ_journey_encode(const UnivJourney *journey, uint8_t *output, size_t capacity)
{
    uint8_t data[UNIV_JOURNEY_BYTES] = {'U', 'J', 'P', '2'};
    unsigned i;
    if (!valid(journey) || !output || capacity < sizeof(data)) return UNIV_INVALID;
    data[4] = journey->player;
    data[5] = journey->primary;
    data[6] = journey->partner;
    data[7] = journey->partner_received;
    memcpy(data + 8, journey->options, 3);
    for (i = 0; i < UNIV_PARTNER_OPTIONS; ++i) write32(data + 12 + 4 * i, journey->partner_options[i]);
    write32(data + 28, checksum(data, 28));
    memcpy(output, data, sizeof(data));
    return UNIV_OK;
}

UnivResult univ_journey_decode(UnivJourney *journey, const uint8_t *input, size_t size)
{
    UnivJourney result;
    unsigned i;
    if (!journey || !input || (size != UNIV_JOURNEY_BYTES && size != 16)) return UNIV_INVALID;
    memset(&result, 0, sizeof(result));
    if (size == 16) {
        /* Preserve the old development offers exactly, never reroll on load. */
        static const char *const legacy[3] = {"lucariomega", "ampharosmega", "aggronmega"};
        if (memcmp(input, "UJP1", 4) || input[11] || read32(input + 12) != checksum(input, 12)) return UNIV_INVALID;
        for (i = 0; i < 3; ++i) {
            unsigned k;
            for (k = 0; k < PARTNER_POOL_COUNT; ++k)
                if (!strcmp(partner_pool[k].mega, legacy[i])) { result.partner_options[i] = partner_pool[k].key; break; }
        }
    } else {
        if (memcmp(input, "UJP2", 4) || input[11] || input[24] || input[25] || input[26] || input[27] ||
            read32(input + 28) != checksum(input, 28)) return UNIV_INVALID;
        for (i = 0; i < 3; ++i) result.partner_options[i] = read32(input + 12 + 4 * i);
    }
    result.version = 2;
    result.player = input[4];
    result.primary = input[5];
    result.partner = input[6];
    result.partner_received = input[7];
    memcpy(result.options, input + 8, 3);
    if (!valid(&result)) return UNIV_INVALID;
    *journey = result;
    return UNIV_OK;
}
