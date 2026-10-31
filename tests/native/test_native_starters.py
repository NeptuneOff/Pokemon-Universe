"""Compile the actual native adapter and test persistent save variables/gifts/NPCs."""
from pathlib import Path
import tempfile
import unittest

from tests.native.native_harness import ROOT, run_native

HEADER = r'''
#ifndef STARTER_ENGINE_FIXTURE_H
#define STARTER_ENGINE_FIXTURE_H
#include <stdint.h>
typedef unsigned char u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int BOOL;
#define TRUE 1
#define FALSE 0
typedef struct VarsFlags { u16 values[0x300]; u16 chosen; } VarsFlags;
typedef struct TrainerInfo { u32 id; } TrainerInfo;
typedef struct SaveData { VarsFlags vars; TrainerInfo trainer; } SaveData;
VarsFlags *SaveData_GetVarsFlags(SaveData *save);
u16 *VarsFlags_GetVarAddress(VarsFlags *vars, u16 id);
u16 SystemVars_GetPlayerStarter(VarsFlags *vars);
BOOL SystemVars_SetPlayerStarter(VarsFlags *vars, u16 value);
TrainerInfo *SaveData_GetTrainerInfo(SaveData *save);
u32 TrainerInfo_ID(const TrainerInfo *info);
#endif
'''


class NativeStarterTests(unittest.TestCase):
    def test_native_save_choices_gifts_story_branches_and_npc_evolutions(self):
        with tempfile.TemporaryDirectory() as folder:
            includes = Path(folder)
            (includes / 'generated').mkdir()
            for name in ('nitro.h', 'savedata.h', 'vars_flags.h', 'system_vars.h', 'save_player.h', 'trainer_info.h'):
                (includes / name).write_text('#include "fixture.h"\n')
            (includes / 'fixture.h').write_text(HEADER)
            (includes / 'generated/species.h').write_text('enum {SPECIES_NONE=0,SPECIES_TURTWIG=387,SPECIES_CHIMCHAR=390,SPECIES_PIPLUP=393,SPECIES_EMPOLEON=395};\n')
            (includes / 'generated/trainer_classes.h').write_text('enum {TRAINER_CLASS_RIVAL=63,TRAINER_CLASS_DP_PLAYER_MALE=95,TRAINER_CLASS_DP_PLAYER_FEMALE=96};\n')
            run = run_native(r'''
#include "starter_port.h"
#include "universe.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"line %d: %s\n",__LINE__,#x); return 1; } } while(0)
VarsFlags *SaveData_GetVarsFlags(SaveData *s) { return &s->vars; }
u16 *VarsFlags_GetVarAddress(VarsFlags *v,u16 id) { return &v->values[id-0x4000]; }
u16 SystemVars_GetPlayerStarter(VarsFlags *v) { return v->chosen; }
BOOL SystemVars_SetPlayerStarter(VarsFlags *v,u16 id) { v->chosen=id; return 1; }
TrainerInfo *SaveData_GetTrainerInfo(SaveData *s) { return &s->trainer; }
u32 TrainerInfo_ID(const TrainerInfo *t) { return t->id; }
int main(void) {
    SaveData a, b, saved, before;
    UnivJourney left, right;
    u16 offers[3], loaded[3];
    unsigned seed, slot, k, stage, seen[3][4]={{0}};
    const u16 roots[3][4]={{1,152,252,387},{4,155,255,390},{7,158,258,393}};
    const u16 story[3]={387,390,393};
    for(seed=0;seed<512;++seed) {
        CHECK(univ_journey_begin_supported(&left,seed,0,4)==UNIV_OK);
        CHECK(univ_journey_begin_supported(&right,seed,1,4)==UNIV_OK);
        memset(&a,0,sizeof(a)); a.trainer.id=seed;
        Universe_StarterOptions(&a,offers);
        for(slot=0;slot<3;++slot) {
            CHECK(left.options[slot]<4 && right.options[slot]<4);
            CHECK(left.options[slot]!=right.options[slot]);
            CHECK(offers[slot]==roots[slot][left.options[slot]]);
            seen[slot][left.options[slot]]++;
        }
        saved=a; a.trainer.id=999999;
        Universe_StarterOptions(&a,loaded);
        CHECK(!memcmp(offers,loaded,sizeof(offers)));
        a.trainer=saved.trainer;
        CHECK(!memcmp(&a,&saved,sizeof(a)));
        b=saved; Universe_StarterOptions(&b,loaded);
        CHECK(!memcmp(offers,loaded,sizeof(offers)));
    }
    for(slot=0;slot<3;++slot) for(k=0;k<4;++k) CHECK(seen[slot][k]>0);
    CHECK(univ_journey_begin_supported(&left,1,0,1)==UNIV_INVALID);
    CHECK(univ_journey_begin_supported(&left,1,0,10)==UNIV_INVALID);
    for(slot=0;slot<3;++slot) {
        memset(&a,0,sizeof(a));a.trainer.id=12345+slot;
        Universe_StarterOptions(&a,offers);
        before=a;
        CHECK(!Universe_StarterCommit(&a,25));
        CHECK(!memcmp(&a,&before,sizeof(a)));
        CHECK(Universe_StarterCommit(&a,offers[slot]));
        CHECK(a.vars.chosen==offers[slot]);
        CHECK(Universe_StarterStorySpecies(&a.vars)==story[slot]);
        CHECK(Universe_StarterOtherSpecies(&a.vars,1)==offers[(slot+1)%3]);
        CHECK(Universe_StarterOtherSpecies(&a.vars,2)==offers[(slot+2)%3]);
        CHECK(!Universe_StarterCommit(&a,offers[(slot+1)%3]));
        CHECK(Universe_StarterGiftSpecies(&a,story[slot],5)==offers[slot]);
        CHECK(Universe_StarterGiftSpecies(&a,story[slot],6)==story[slot]);
        CHECK(Universe_StarterGiftSpecies(&a,25,5)==25);
        Universe_StarterGiftComplete(&a,story[slot],5,0);
        CHECK(a.vars.values[0x6F]==1);
        CHECK(Universe_StarterGiftSpecies(&a,story[slot],5)==offers[slot]);
        Universe_StarterGiftComplete(&a,story[slot],5,1);
        CHECK(a.vars.values[0x6F]==0);
        CHECK(Universe_StarterGiftSpecies(&a,story[slot],5)==story[slot]);
        CHECK(Universe_StarterCommit(&a,offers[slot]));
        CHECK(a.vars.values[0x6F]==0);
        saved=a;memset(&a,0,sizeof(a));a=saved;
        CHECK(Universe_StarterStorySpecies(&a.vars)==story[slot]);
        for(stage=0;stage<3;++stage) for(k=0;k<3;++k) {
            u16 source=(u16)(387+3*k+stage);
            CHECK(Universe_StarterTrainerSpecies(&a,63,source)==offers[(slot+1)%3]+stage);
            CHECK(Universe_StarterTrainerSpecies(&a,95,source)==offers[(slot+2)%3]+stage);
            CHECK(Universe_StarterTrainerSpecies(&a,96,source)==offers[(slot+2)%3]+stage);
            CHECK(Universe_StarterTrainerSpecies(&a,12,source)==source);
        }
        CHECK(Universe_StarterTrainerSpecies(&a,63,25)==25);
    }
    memset(&a,0,sizeof(a));a.vars.chosen=393;before=a;
    Universe_StarterOptions(&a,offers);
    CHECK(!memcmp(&a,&before,sizeof(a)));
    CHECK(!memcmp(offers,story,sizeof(story)));
    CHECK(Universe_StarterStorySpecies(&a.vars)==393);
    CHECK(Universe_StarterOtherSpecies(&a.vars,1)==0);
    CHECK(Universe_StarterTrainerSpecies(&a,63,390)==390);
    CHECK(Universe_StarterGiftSpecies(&a,387,5)==387);
    memset(&a,0,sizeof(a));a.vars.values[0x31]=0x9999;before=a;
    Universe_StarterOptions(&a,offers);
    CHECK(!memcmp(&a,&before,sizeof(a)));
    puts("Native adapter persistence, real-species gift, story branches and NPC lines passed");
    return 0;
}
''', extra_sources=[ROOT / 'native/universe/starter_port.c'], include_paths=[includes])
            self.assertIn('NPC lines passed', run.stdout)
