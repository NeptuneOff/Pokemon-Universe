"""Patch only exported pinned PC sources for the playable native starter draw."""

STARTER_FILES = [
    'include/struct_defs/choose_starter_data.h', 'src/choose_starter/choose_starter_app.c',
    'src/scrcmd.c', 'src/scrcmd_party.c', 'src/system_vars.c', 'src/trainer_data.c', 'src/game_start.c',
]


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Starter source anchor absent or ambiguous: ' + old[:90])
    return text.replace(old, new, 1)


def patch_starters(original):
    result = {}
    header = original[STARTER_FILES[0]]
    result[STARTER_FILES[0]] = once(header, '    const Options *options;', '    const Options *options;\n    u16 universeSpecies[3];')
    app = original[STARTER_FILES[1]]
    for index, species in enumerate(('TURTWIG', 'CHIMCHAR', 'PIPLUP')):
        app = once(app, '#define STARTER_OPTION_%d    SPECIES_%s' % (index, species),
                   '#define STARTER_OPTION_%d    (app->universeSpecies[%d])' % (index, index))
    app = once(app, '    enum CursorPosition cursorPosition;', '    enum CursorPosition cursorPosition;\n    u16 universeSpecies[3];')
    app = app.replace('GetSelectedSpecies(u16 cursorPosition)', 'GetSelectedSpecies(ChooseStarterApp *app, u16 cursorPosition)')
    if app.count('GetSelectedSpecies(app->cursorPosition)') != 2:
        raise ValueError('Unexpected starter preview/selection calls')
    app = app.replace('GetSelectedSpecies(app->cursorPosition)', 'GetSelectedSpecies(app, app->cursorPosition)')
    app = once(app, '    app->messageFrame = Options_Frame(data->options);',
        '    memcpy(app->universeSpecies, data->universeSpecies, sizeof(app->universeSpecies));\n    app->messageFrame = Options_Frame(data->options);')
    app = once(app, '#include "message.h"', '#include "message.h"\n#include "message_util.h"\n#include "constants/charcode.h"')
    app = once(app, 'static u8 SetMessageWindowText(Window *window, enum HeapID heapID, int bankID, int entryID, TextColor textColor, u32 renderDelay);',
        'static void SetStarterQuestion(ChooseStarterApp *app, enum HeapID heapID);\nstatic u8 SetMessageWindowText(Window *window, enum HeapID heapID, int bankID, int entryID, TextColor textColor, u32 renderDelay);')
    app = once(app, '        SetMessageWindowText(app->messageWindow, heapID, 360, 1 + app->cursorPosition, TEXT_COLOR(1, 2, 15), TEXT_SPEED_NO_TRANSFER);',
        '        SetStarterQuestion(app, heapID);')
    anchor = 'static u8 SetMessageWindowText(Window *window, enum HeapID heapID, int bankID, int entryID, TextColor textColor, u32 renderDelay)\n{'
    question = '''/* Localized species names from the French runtime, never the fixed Sinnoh text. */
static void SetStarterQuestion(ChooseStarterApp *app, enum HeapID heapID)
{
    static const charcode_t prefix[] = {CHAR_C, CHAR_h, CHAR_o, CHAR_i, CHAR_s, CHAR_i, CHAR_r, CHAR_SPACE, CHAR_EOS};
    String *name = MessageUtil_SpeciesName(GetSelectedSpecies(app, app->cursorPosition), heapID);
    String *text = String_Init(64, heapID);
    String_CopyChars(text, prefix);
    String_Concat(text, name);
    String_AppendChar(text, CHAR_SPACE);
    String_AppendChar(text, CHAR_QUESTION);
    Window_FillTilemap(app->messageWindow, 15);
    Text_AddPrinterWithParamsAndColor(app->messageWindow, FONT_MESSAGE, text, 0, 0,
        TEXT_SPEED_NO_TRANSFER, TEXT_COLOR(1, 2, 15), NULL);
    Window_DrawMessageBoxWithScrollCursor(app->messageWindow, FALSE, FRAME_TEXT_START, FRAME_TEXT_PALETTE_INDEX);
    String_Free(text);
    String_Free(name);
}

'''
    result[STARTER_FILES[1]] = once(app, anchor, question + anchor)
    include = '#include "universe_native/starter_port.h"\n'
    script = include + original['src/scrcmd.c']
    script = once(script, '    chooseStarterData->options = SaveData_GetOptions(ctx->fieldSystem->saveData);',
        '    chooseStarterData->options = SaveData_GetOptions(ctx->fieldSystem->saveData);\n    Universe_StarterOptions(ctx->fieldSystem->saveData, chooseStarterData->universeSpecies);')
    script = once(script, '    SystemVars_SetPlayerStarter(SaveData_GetVarsFlags(ctx->fieldSystem->saveData), chooseStarterData->species);',
        '    BOOL committed = Universe_StarterCommit(ctx->fieldSystem->saveData, chooseStarterData->species);\n    GF_ASSERT(committed);')
    script = once(script, '    *species = SystemVars_GetPlayerStarter(SaveData_GetVarsFlags(ctx->fieldSystem->saveData));',
        '    *species = Universe_StarterStorySpecies(SaveData_GetVarsFlags(ctx->fieldSystem->saveData));')
    result['src/scrcmd.c'] = script
    gift = include + original['src/scrcmd_party.c']
    gift = once(gift, '    *success = Pokemon_GiveMonFromScript(HEAP_ID_FIELD2, fieldSystem->saveData, species, level, heldItem, metLocation, metTerrain);',
        '    u16 actualSpecies = Universe_StarterGiftSpecies(fieldSystem->saveData, species, level);\n    *success = Pokemon_GiveMonFromScript(HEAP_ID_FIELD2, fieldSystem->saveData, actualSpecies, level, heldItem, metLocation, metTerrain);\n    Universe_StarterGiftComplete(fieldSystem->saveData, species, level, *success);')
    result['src/scrcmd_party.c'] = gift
    vars_source = include + original['src/system_vars.c']
    for name, offset in [('Rival', 1), ('PlayerCounterpart', 2)]:
        anchor = 'u16 SystemVars_Get%sStarter(VarsFlags *varsFlags)\n{' % name
        vars_source = once(vars_source, anchor, anchor + '\n    u16 drawn = Universe_StarterOtherSpecies(varsFlags, %d);\n    if (drawn) return drawn;' % offset)
    result['src/system_vars.c'] = vars_source
    trainer = include + original['src/trainer_data.c']
    anchor = '            u16 species = trmon[i].species & 0x3FF;'
    if trainer.count(anchor) != 4:
        raise ValueError('Unexpected trainer party formats')
    trainer = trainer.replace(anchor,
        '            u16 originalSpecies = trmon[i].species & 0x3FF;\n            u16 species = Universe_StarterTrainerSpecies(dto->saveData, dto->trainer[battler].header.trainerType, originalSpecies);')
    anchor = '            for (j = 0; j < 4; j++) {\n                Pokemon_SetMoveSlot(mon, trmon[i].moves[j], j);\n            }'
    if trainer.count(anchor) != 2:
        raise ValueError('Unexpected explicit trainer move formats')
    trainer = trainer.replace(anchor, '            if (species == originalSpecies) {\n' + anchor + '\n            }')
    result['src/trainer_data.c'] = trainer
    game = include + original['src/game_start.c']
    game = once(game, '    TrainerInfo_SetAppearance(trainerInfo, Appearance_CalculateFromTrainerInfo(rnd, TrainerInfo_Gender(trainerInfo), 0));',
        '    TrainerInfo_SetAppearance(trainerInfo, Appearance_CalculateFromTrainerInfo(rnd, TrainerInfo_Gender(trainerInfo), 0));\n    Universe_StarterEnsure(saveData);')
    result['src/game_start.c'] = game
    return result
