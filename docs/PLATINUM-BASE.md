# Migration vers le code de Platine

## Correction de conception

La demande porte sur les visuels de Pokémon Platine, pas sur une interface web avec une interprétation graphique personnelle. Le prototype 0.2 ne satisfait pas cette demande. Il est conservé comme expérience technique, et son moteur ne sert plus de base au produit.

La base retenue est le port PC de cybervisi0n, lui-même dérivé de la décompilation pret et utilisant libntr. Le code du jeu existant est référencé comme sous-module épinglé, sans modification amont. Les contributions IA ne sont pas acceptées par l’amont : aucune pull request ou suggestion de code ne lui est envoyée. L’intégration décrite ici concerne uniquement le dépôt indépendant Universe.

## Évaluation des bases

| Base inspectée | Constat | Décision |
|---|---|---|
| pret/pokeplatinum | Décompilation visant la production de ROMs DS ; systèmes de cartes et ressources de Platine | Référence d’origine |
| cybervisi0n/pokeplatinum | Port PC 64 bits ; exécutables amont ; chargement des ressources d’une ROM USA personnelle ; limitations expérimentales annoncées | Base PC retenue ; monde, introduction FR et sauvegarde/reprise vérifiés sous Linux |
| arcanite24/pokeplatinum-portable | Port SDL3 dont le README indique encore une intégration du jeu en cours et des couches audio/fichiers planifiées | Pas retenu pour cette migration |

Révision sélectionnée : `35067868f64f23d25d17ac3e536cfdd9a7f40523`, branche amont `pc_port`. Les dépendances Meson amont incluent des branches mobiles : épingler le seul sous-module ne garantit pas encore la reproductibilité de toutes les bibliothèques.

## Points du code à conserver et étendre

Chemins relatifs à `engine/platinum` :

- `src/main.c` : démarrage et boucle du jeu.
- `src/map_header.c` et `src/map_header_data.c` : données et métadonnées des lieux.
- `src/map_object.c` : personnages et objets du monde.
- `src/scrcmd.c` : commandes des scripts d’événements.
- `src/battle_anim/` : animations des combats.
- `src/field_comm_manager.c` et `src/comm_manager.c` : communications existantes, à analyser pour une coopération de campagne.
- `res/` : structure des ressources d’origine ; ne pas substituer les décors de la démo.
- `docs/maps/` : matrices, modèles, textures et collisions du monde.

La logique de règles doit venir du jeu existant. Les tests et le scénario du prototype peuvent servir de cahier des charges, mais son moteur de combat simplifié ne doit pas remplacer celui de Platine.

## Ordre de migration

1. Initialiser la source PC épinglée. **Fait dans le dépôt sous forme de sous-module.**
2. Valider le lancement avec une ROM USA CPUE01 personnelle, puis comparer une scène et un combat avec Platine. **Démarrage, introduction FR, scène du monde et premier combat vérifiés sous Linux.**
3. Définir et vérifier les réglages de rendu conservant l’apparence d’origine, y compris caméra, proportions et interface. **Préréglage DS ×1, 512 ×768 et écrans verticaux appliqués.**
4. Produire une modification minimale du scénario sur cette base et vérifier la sauvegarde. **Prologue et première enquête à rôles distincts ajoutés ; sauvegarde et reprise du jeu de base vérifiées à Bonaugure. Voir [la quête](NATIVE-INVESTIGATION.md) et ses validations.**
5. Réaliser une petite zone réellement coopérative sur deux PC, avec deux identités, décisions et équipes distinctes. **Non réalisé.**
6. Étendre ensuite le catalogue, les Méga-Évolutions, les cartes et l’histoire par étapes vérifiées.

## Ressources et distribution

La préparation de développement part des sources personnelles USA/France validées. Le lancement Windows Universe utilise maintenant les fichiers préparés et versionnés dans `distribution/windows`, sans ROM demandée au joueur. Voir [la distribution Git](../distribution/README.md).

Les notices et crédits du moteur et des dépendances, notamment libntr, sont conservés et installés avec le jeu. L’amont demeure un projet distinct ; aucun travail de portage de son moteur n’est attribué à Universe.

Aucune image « officielle Platine » n’existe pour les Pokémon ou régions apparus après ce jeu. Leur intégration exigera du pixel art et des modèles compatibles, puis une validation visuelle ; elle ne sera pas annoncée comme déjà faite.

## Validation de cette étape

Outils de préparation USA/FR, lanceurs Windows/Linux, prologue et première enquête solo Universe ajoutés. L’exécutable utilisé est celui de l’amont v0.1.12, sans compilation Universe. Aucune nouvelle région ni coopération native livrée. Voir [NATIVE-FR.md](NATIVE-FR.md) et [NATIVE-VALIDATION.md](NATIVE-VALIDATION.md).
