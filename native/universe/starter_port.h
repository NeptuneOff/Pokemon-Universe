#ifndef UNIVERSE_STARTER_PORT_H
#define UNIVERSE_STARTER_PORT_H
#include <nitro.h>
#include "savedata.h"
#include "vars_flags.h"

void Universe_StarterEnsure(SaveData *save);
void Universe_StarterOptions(SaveData *save, u16 options[3]);
BOOL Universe_StarterCommit(SaveData *save, u16 species);
u16 Universe_StarterStorySpecies(VarsFlags *vars);
u16 Universe_StarterOtherSpecies(VarsFlags *vars, unsigned offset);
u16 Universe_StarterGiftSpecies(SaveData *save, u16 requested, u16 level);
void Universe_StarterGiftComplete(SaveData *save, u16 requested, u16 level, BOOL success);
u16 Universe_StarterTrainerSpecies(SaveData *save, unsigned trainerClass, u16 original);
#endif
