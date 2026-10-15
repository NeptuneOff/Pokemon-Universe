/* Resolve bundled, byte-identical PNG resources before the game starts. */
for (const species of Object.values(window.GAME_DATA.pokemon)) {
  for (const field of ['sprite', 'back']) {
    if (species[field]) species[field] = window.POKEMON_SPRITES[species[field]] || null;
  }
}
