# Extension native : registre et règles de Méga-Évolution

**Statut : composant C relié au port Windows recompilé, pas encore activé comme mécanique de combat.** Le contenu jouable lancé par `JOUER.bat` reste celui décrit dans le README. Cette étape n’ajoute pas encore d’espèces capturables, de région ou de coopération réseau.

Le [port Windows recompilé](NATIVE-PORT-BUILD.md) contient ce module, avec des appels au démarrage et au cycle de vie des combats. Les diagnostics de l’exécutable et du candidat français portable ont réussi. Ce raccordement ne déclenche pas encore une Méga-Évolution dans un combat du jeu. La branche générée `builds/windows-linked` conserve les nouveaux candidats ; leur promotion dans `main` reste une étape explicite de validation.

## Ce qui est implémenté

- Un registre de **1 025 espèces nationales**, **1 329 entrées avec les formes retenues** et **97 formes Méga**, issu de l’instantané des sources du 26 octobre 2026. Ce nombre de Méga compte les variantes de forme, pas seulement les espèces capables de méga-évoluer.
- Les noms français des espèces, types, statistiques de base, talents et exigences des Méga. Les libellés de formes restent les identifiants techniques de la source ; ils ne sont pas une nouvelle interface localisée.
- Une table C et une recherche par identifiant stable, indépendantes du catalogue de l’ancien prototype web. Le type Fée est ajouté à l’identifiant 18 en conservant les identifiants de types de Platine.
- Les règles de sélection : bonne forme d’origine, pierre ou capacité requise, Gemme Sésame, Pokémon vivant, une Méga par dresseur pour les deux participants du composant. Une tentative refusée ne consomme pas le droit à la Méga ; revenir à la forme initiale ne rend pas ce droit pour le même combat.
- Les variantes X, Y, Z et celles liées aux formes sont conservées. Une forme nommée « Mega-Z » n’est pas une capacité Z. Gigamax, Primo-Résurgence, Ultra et Totem sont exclus de ce registre d’extension.
- Des instantanés de sources compressés et leurs empreintes, versionnés dans Git pour permettre une reconstruction hors connexion.
- Le calcul des six statistiques à partir des bases, du niveau, des IV, des EV et de la nature, dans l'ordre du catalogue. La conversion de l'axe Vitesse des natures suit l'ordre de Platine. Les anciens EV de valeur 255 restent acceptés avec leur contribution entière ; un total supérieur à 510 ou des entrées invalides est refusé sans changer la sortie. Munja conserve son PV unique.
- Une règle d'adaptation des PV lors des changements de maximum : conserver les dégâts déjà reçus, maintenir un Pokémon K.O. à zéro et limiter un Pokémon vivant à au moins un PV lors du retour à une forme plus petite. C'est la règle Universe prévue pour les changements de forme, y compris Zygarde ; ce n'est pas une validation du combat en temps réel de Z-A.

Le module applique un modèle de sélection au tour par tour destiné à Universe. Il ne reproduit pas le système de combat en temps réel de Z-A. Les calculs de statistiques et de PV sont disponibles dans le composant ; **ils ne sont pas encore appliqués aux `BattleMon` du moteur**. Les effets de talents, les animations, les actions de combat et les capacités supplémentaires restent à raccorder.

## Source des données

Les révisions et empreintes exactes sont enregistrées dans `content/native/expansion/sources/provenance.json` et recopiées dans le catalogue.

- [Pokémon Showdown, révision b354a81](https://github.com/smogon/pokemon-showdown/blob/b354a81f11003a03f0dcd1dafd4edc641e6763bd/data/pokedex.ts) : données des espèces et formes. Notice MIT conservée dans `data/SHOWDOWN-LICENSE`.
- [PokéAPI, révision 2bf639e](https://github.com/PokeAPI/pokeapi/blob/2bf639e5572812a67d2b94903fdcb9d095f5aeb2/data/v2/csv/pokemon_species_names.csv) : noms français des espèces. Notice conservée dans `content/native/expansion/sources/POKEAPI-LICENSE.txt`.

Les sources ne sont pas automatiquement actualisées au lancement du jeu. Un changement de catalogue doit être reconstruit, contrôlé et versionné.

## Infinite Fusion et les sprites

Le [dépôt public Infinite Fusion Hoenn](https://github.com/infinitefusion/infinitefusion-hoenn-public) est retenu comme source candidate conformément à la demande. Aucun sprite de ce dépôt n’est encore importé. Son README présente un projet RPG Maker, pas un paquet directement compatible avec les archives graphiques et animations de Platine.

Pour chaque ressource choisie, conserver le chemin source, la révision, l’auteur/crédit, les conditions de réutilisation et l’empreinte ; vérifier ensuite le cadrage, la palette, les vues avant/arrière et l’animation. Une ressource disponible dans Git ne prouve pas sa compatibilité graphique. Les Fakemon et fusions sont désormais explicitement demandés. Leur intégration doit conserver les crédits, un identifiant propre et le style de Platine ; ils ne reçoivent pas de faux numéro national officiel. Voir [les ressources candidates](RESSOURCES-COMMUNAUTAIRES.md).

## Nouveau départ

`journey.c` ajoute le tirage de trois propositions, Plante/Feu/Eau, parmi 27 starters des générations 1 à 9. Deux personnages d'une même campagne ont des propositions différentes pour chaque type. Un enregistrement versionné de 32 octets conserve le trio, les choix, le personnage et la remise du compagnon ; son contrôle d'intégrité détecte une altération avant chargement.

Le choix du second compagnon est refusé tant que le premier n'est pas confirmé. Trois offres sont tirées dans 48 lignées non starters ayant une évolution réelle et un stade final capable de Méga : 53 parcours possibles dans les données épinglées, y compris les variantes Z-A éligibles. Le tirage se fait par famille, sans doublon entre les six offres du duo, puis par forme Méga cible. Les contraintes de sexe des branches évolutives sont conservées. La pierre correspond à la cible tirée. Les clés sauvegardées sont indépendantes de l'ordre du catalogue ; le décodage de l'ancien format de développement à 16 octets conserve ses offres sans nouveau tirage. La validation du don n'est enregistrée qu'après succès du callback chargé de remettre le Pokémon avec sa gemme ; une reprise ne permet pas de doubler le cadeau. Le moteur hôte doit rendre cette remise atomique dans l'équipe et le Sac.

**Il s'agit encore des règles du composant.** Le menu natif, les Pokémon de l'équipe, les objets du Sac et la sauvegarde de Platine ne chargent pas encore cet enregistrement. Les 15 starters postérieurs à la quatrième génération exigent d'abord leur intégration complète : données, sprites, capacités, évolutions et identifiants compatibles. Les numéros nationaux du registre ne doivent pas être donnés directement à `Pokemon_InitWith`.

## Raccordement restant à réaliser

Le registre est relié au port recompilé livré dans Git. Son raccordement aux structures jouables, aux menus et aux visuels demande encore des adaptations du moteur ; le joueur gardera le lanceur unique et n’aura rien à compiler.

1. **Identifiants et sauvegardes.** Ne pas écrire le numéro national directement dans les anciennes tables : le numéro 494 désigne Victini dans le Pokédex national, mais l’Œuf dans Platine. Le catalogue laisse donc `legacy_native_species_id` vide pour les nouvelles espèces et les formes non mappées. Prévoir une sauvegarde versionnée avec migration et refus des retours incompatibles avant de permettre la capture.
2. **Chargement des données.** Brancher les statistiques, talents et formes sur les structures du moteur ; traiter les limites des champs d’origine, notamment les talents sur 8 bits et les formes sur 5 bits. Adapter le Pokédex, les noms, les équipes et le PC.
3. **Combat.** Raccorder les contrôles de Méga au choix d’action, appliquer les statistiques/PV et talents, gérer la forme temporaire sur le terrain et revenir à la forme d’origine à la fin du combat. Ajouter les interactions du type Fée. Le cas de Zygarde, dont les PV de base diffèrent, exige une règle explicitement vérifiée.
4. **Visuels.** Construire les archives nécessaires, puis tester les sprites avant/arrière, variantes et animations dans un véritable combat natif.
5. **Obtention.** Ajouter captures, évolutions et objets dans une progression cohérente. Les six autres régions et la campagne coopérative réseau restent des chantiers distincts, pas des conséquences automatiques de ce registre.

## Reconstruction et tests

Node 24 et Python 3 sont nécessaires uniquement au développement :

```bash
python tools/native/rebuild_expansion.py --check
python tools/native/rebuild_expansion.py --write
python -m unittest discover -s tests/native -v
```

`--check` reconstruit dans un dossier temporaire et compare les fichiers versionnés. `--write` régénère le catalogue JSON et la table C. Les empreintes des sources sont vérifiées avant la génération ; aucune ressource du jeu installé ni sauvegarde n’est touchée.

Les tests compilent et exécutent un programme C indépendant avec GCC/Clang sous Linux ou MSVC sous Windows. Ils parcourent les exigences de chaque Méga et vérifient des refus et cas particuliers. Ils ne constituent pas un combat graphique de Platine ni une validation du duo réseau.
