# Crédits et provenance

## Code original de cette version

Moteur client, serveur de coopération, cartes programmatiques et scénario Méridien : développement pour le projet **NeptuneOff/Pokemon-Universe**.

Ce prototype PC ne reprend pas le moteur Nintendo DS de Platine. Le dépôt `pret/pokeplatinum` a été étudié et récupéré dans le travail initial ; son code n’est pas présenté ici comme un port PC réalisé. Les projets `pret/pokeheartgold` et `pret/pokeemerald` ont été identifiés comme références possibles, mais leurs régions n’ont pas été importées dans cette version.

## Données Pokémon

- Pokémon Showdown / Smogon : https://github.com/smogon/pokemon-showdown — `data/pokedex.ts`, `data/learnsets.ts`, `data/moves.ts`. Licence amont conservée dans `data/SHOWDOWN-LICENSE`.
- PokéAPI : https://github.com/PokeAPI/pokeapi — noms français des espèces, taux de capture et catégories légendaire/fabuleux.
- L’extraction produit un sous-ensemble de données. Elle n’intègre pas le simulateur complet Pokémon Showdown ; ses talents et effets de capacités ne sont pas automatiquement pris en charge.

## Illustrations

- Smogon / Pokémon Showdown sprite repository : https://github.com/smogon/sprites
- Révision utilisée : `8d8d474e677e5a524f6564f2f208111d70cc3a4a`.
- Fichiers sources : `src/sprites/gen5/`.
- Les images fournies sont la première image des animations sources, recadrée sur la transparence, sans rééchantillonnage. Chaque source et son empreinte figurent dans `docs/sprites-manifest.json`.
- Le README amont est conservé dans `docs/SMOGON-SPRITES-README.md`. Il distingue la licence MIT du code des droits sur les sprites Nintendo / Game Freak / The Pokémon Company et des conditions des créations communautaires. **Ces images ne sont pas déclarées MIT par ce projet.**
- La notice du dépôt de sprites PokéAPI consulté est conservée à titre de référence dans `data/SPRITES-LICENSE` ; elle ne remplace pas les conditions du dépôt Smogon effectivement utilisé.

Pokémon, ses personnages, noms et ressources tiers restent attribués à leurs titulaires respectifs. Projet de fan non officiel, non affilié à Nintendo, Game Freak ou The Pokémon Company. La publication d’une version finale nécessite un contrôle des droits de distribution, particulièrement pour les sprites communautaires.

## Sources officielles consultées pour Z-A

- https://legends.pokemon.com/en-us/dlc
- https://legends.pokemon.com/en-gb/news/mega_lucario_z

Les variantes de Méga-Évolutions du catalogue sont importées depuis les données Showdown. Leur présence ne certifie ni une illustration achevée ni une reproduction complète de leurs règles particulières.
