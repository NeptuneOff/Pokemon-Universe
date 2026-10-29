#ifndef UNIVERSE_EXTENSION_H
#define UNIVERSE_EXTENSION_H
#include <stddef.h>
#include <stdint.h>

/* Rules component linked into the development PC port. */
typedef struct {
    const char *id;
    uint16_t national_dex;
    uint8_t mega;
    uint16_t base_stats[6]; /* HP, Attack, Defense, SpA, SpD, Speed */
    uint8_t types[2];      /* Platinum IDs retained, Fairy appended as 18 */
    const char *abilities[3];
    const char *eligible_from[4];
    const char *required_item;
    const char *required_move;
} UnivSpecies;

typedef struct { uint8_t mega_used[2]; } UnivBattle;
typedef struct {
    const UnivSpecies *current;
    const UnivSpecies *original;
    uint8_t trainer;
} UnivBattleMon;
typedef enum {
    UNIV_OK = 0, UNIV_INVALID, UNIV_NOT_MEGA, UNIV_WRONG_FORM,
    UNIV_FAINTED, UNIV_NO_KEYSTONE, UNIV_ALREADY_USED,
    UNIV_MISSING_ITEM, UNIV_MISSING_MOVE
} UnivResult;

/* Catalog order: HP, Attack, Defense, SpA, SpD, Speed. Nature IDs retain the
 * native Platinum order (Hardy=0 ... Quirky=24), whose Speed axis differs. */
typedef struct {
    uint8_t level;
    uint8_t nature;
    uint8_t iv[6];
    uint8_t ev[6];
} UnivTraining;

size_t univ_species_count(void);
const UnivSpecies *univ_species_find(const char *id);
UnivResult univ_calculate_stats(const UnivSpecies *species, const UnivTraining *training,
                                uint16_t output[6]);
/* Preserve damage when maximum HP changes; a fainted mon stays fainted.
 * An alive mon is clamped to at least one HP on return to a smaller form. */
UnivResult univ_adjust_hp(uint16_t current, uint16_t old_max, uint16_t new_max,
                          uint16_t *output);
void univ_battle_init(UnivBattle *battle);
UnivResult univ_mon_init(UnivBattleMon *mon, const char *id, unsigned trainer);
UnivResult univ_mega_try(UnivBattle *battle, UnivBattleMon *mon, const char *target_id,
                        int alive, int has_keystone, const char *held_item,
                        const char *const *known_moves, size_t move_count);
void univ_mega_end(UnivBattleMon *mon);
const char *univ_result_name(UnivResult result);
#endif
