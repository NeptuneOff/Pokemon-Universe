#include "starter_port.h"
#include "include/universe.h"
#include "generated/species.h"
#include "generated/trainer_classes.h"
#include "system_vars.h"
#include "save_player.h"
#include "trainer_info.h"
#include <stdio.h>

/* Audited unused persistent variables, not quest flags. Save layout unchanged.
 * Never write national numbers for post-Platinum species into native tables. */
#define OPENING_TAG_VAR 0x4031
#define OPENING_OPTION_VAR 0x406C
#define OPENING_PENDING_VAR 0x406F
#define OPENING_TAG 0x5541
#define NATIVE_FAMILIES 4
static const u16 roots[3][NATIVE_FAMILIES] = {
    {1, 152, 252, 387}, {4, 155, 255, 390}, {7, 158, 258, 393}
};
static const u16 story[3] = {SPECIES_TURTWIG, SPECIES_CHIMCHAR, SPECIES_PIPLUP};

static u16 get(VarsFlags *vars, u16 id) { return *VarsFlags_GetVarAddress(vars, id); }
static void set(VarsFlags *vars, u16 id, u16 value) { *VarsFlags_GetVarAddress(vars, id) = value; }

static int has_opening(VarsFlags *vars)
{
    unsigned i, k;
    if (get(vars, OPENING_TAG_VAR) != OPENING_TAG) return 0;
    for (i = 0; i < 3; ++i) {
        for (k = 0; k < NATIVE_FAMILIES; ++k)
            if (get(vars, (u16)(OPENING_OPTION_VAR + i)) == roots[i][k]) break;
        if (k == NATIVE_FAMILIES) return 0;
    }
    return 1;
}

static int selected_slot(VarsFlags *vars)
{
    unsigned i;
    u16 selected = SystemVars_GetPlayerStarter(vars);
    for (i = 0; i < 3; ++i)
        if (get(vars, (u16)(OPENING_OPTION_VAR + i)) == selected) return (int)i;
    return -1;
}

void Universe_StarterEnsure(SaveData *save)
{
    VarsFlags *vars = SaveData_GetVarsFlags(save);
    UnivJourney journey;
    unsigned i;
    if (has_opening(vars)) return;
    /* Existing completed choices and unknown reserved data are not rewritten. */
    if (SystemVars_GetPlayerStarter(vars) != SPECIES_NONE || get(vars, OPENING_TAG_VAR)) return;
    if (univ_journey_begin_supported(&journey, TrainerInfo_ID(SaveData_GetTrainerInfo(save)), 0, NATIVE_FAMILIES) != UNIV_OK) return;
    for (i = 0; i < 3; ++i) set(vars, (u16)(OPENING_OPTION_VAR + i), roots[i][journey.options[i]]);
    set(vars, OPENING_PENDING_VAR, 0);
    set(vars, OPENING_TAG_VAR, OPENING_TAG);
    printf("[Universe] Native starter draw saved: Grass=%u Fire=%u Water=%u; pool=12.\n",
        (unsigned)get(vars, OPENING_OPTION_VAR), (unsigned)get(vars, OPENING_OPTION_VAR + 1),
        (unsigned)get(vars, OPENING_OPTION_VAR + 2));
    fflush(stdout);
}

void Universe_StarterOptions(SaveData *save, u16 options[3])
{
    VarsFlags *vars = SaveData_GetVarsFlags(save);
    unsigned i;
    Universe_StarterEnsure(save);
    for (i = 0; i < 3; ++i) options[i] = has_opening(vars) ? get(vars, (u16)(OPENING_OPTION_VAR + i)) : story[i];
}

BOOL Universe_StarterCommit(SaveData *save, u16 species)
{
    VarsFlags *vars = SaveData_GetVarsFlags(save);
    unsigned i;
    u16 current = SystemVars_GetPlayerStarter(vars);
    if (!has_opening(vars)) return SystemVars_SetPlayerStarter(vars, species);
    for (i = 0; i < 3; ++i) if (get(vars, (u16)(OPENING_OPTION_VAR + i)) == species) break;
    if (i == 3 || (current && current != species)) return FALSE;
    if (current) return TRUE;
    if (!SystemVars_SetPlayerStarter(vars, species)) return FALSE;
    set(vars, OPENING_PENDING_VAR, 1);
    printf("[Universe] Native starter confirmed: species=%u slot=%u.\n", (unsigned)species, i);
    fflush(stdout);
    return TRUE;
}

u16 Universe_StarterStorySpecies(VarsFlags *vars)
{
    int slot = selected_slot(vars);
    if (has_opening(vars) && slot >= 0) return story[slot];
    return SystemVars_GetPlayerStarter(vars);
}

u16 Universe_StarterOtherSpecies(VarsFlags *vars, unsigned offset)
{
    int slot = selected_slot(vars);
    if (!has_opening(vars) || slot < 0 || offset > 2) return SPECIES_NONE;
    return get(vars, (u16)(OPENING_OPTION_VAR + ((unsigned)slot + offset) % 3));
}

u16 Universe_StarterGiftSpecies(SaveData *save, u16 requested, u16 level)
{
    VarsFlags *vars = SaveData_GetVarsFlags(save);
    if (has_opening(vars) && get(vars, OPENING_PENDING_VAR) == 1 && level == 5 &&
        requested == Universe_StarterStorySpecies(vars)) return SystemVars_GetPlayerStarter(vars);
    return requested;
}

void Universe_StarterGiftComplete(SaveData *save, u16 requested, u16 level, BOOL success)
{
    VarsFlags *vars = SaveData_GetVarsFlags(save);
    if (success && has_opening(vars) && get(vars, OPENING_PENDING_VAR) == 1 && level == 5 &&
        requested == Universe_StarterStorySpecies(vars)) {
        set(vars, OPENING_PENDING_VAR, 0);
        printf("[Universe] Native starter received: species=%u.\n", (unsigned)SystemVars_GetPlayerStarter(vars));
        fflush(stdout);
    }
}

u16 Universe_StarterTrainerSpecies(SaveData *save, unsigned trainerClass, u16 original)
{
    u16 root;
    unsigned stage;
    if (!save || original < SPECIES_TURTWIG || original > SPECIES_EMPOLEON) return original;
    if (trainerClass == TRAINER_CLASS_RIVAL) root = Universe_StarterOtherSpecies(SaveData_GetVarsFlags(save), 1);
    else if (trainerClass == TRAINER_CLASS_DP_PLAYER_MALE || trainerClass == TRAINER_CLASS_DP_PLAYER_FEMALE)
        root = Universe_StarterOtherSpecies(SaveData_GetVarsFlags(save), 2);
    else return original;
    if (!root) return original;
    stage = (original - SPECIES_TURTWIG) % 3;
    if (root + stage != original) {
        printf("[Universe] Native NPC starter mapped: %u -> %u; stage=%u.\n", (unsigned)original, root + stage, stage);
        fflush(stdout);
    }
    return (u16)(root + stage);
}
