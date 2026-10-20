# Pokémon Universe — base Platine PC

**Changement de base : le prototype web Méridien 0.2 est abandonné comme moteur du jeu final.** Il ne respecte pas les visuels demandés. Ses fichiers restent disponibles pour conserver les essais de scénario et de coopération, mais ne constituent pas la nouvelle version du jeu.

## Le code du jeu existant

La nouvelle référence technique est [Pokémon Platinum PC Port](https://github.com/cybervisi0n/pokeplatinum), dérivé de [pret/pokeplatinum](https://github.com/pret/pokeplatinum) et des bibliothèques libntr.

Le sous-module [engine/platinum](engine/platinum) référence exactement le commit `35067868f64f23d25d17ac3e536cfdd9a7f40523`. Il contient le code existant de Platine porté vers PC, sans modification de sa source. Les outils Universe appliquent séparément un premier dialogue aux ressources françaises locales. Il ne s’agit pas d’un nouveau moteur web imitant Pokémon.

```bash
git clone --recurse-submodules https://github.com/NeptuneOff/Pokemon-Universe.git
```

Pour un clone déjà présent :

```bash
git pull --ff-only
git submodule update --init engine/platinum
```

## Lancer la base native en français

Sous Windows : **`PREPARER-PLATINE.bat`**, sélectionner ses ROM personnelles USA Rev 1 et France (`.nds` ou ZIP), puis **`JOUER-PLATINE.bat`**. Python 3 est requis pour la préparation. Le port est téléchargé et vérifié automatiquement ; aucune compilation n’est demandée.

Le ZIP du dépôt suffit pour cette préparation. Pour développer le moteur, utiliser Git et `INITIALISER-SOURCES-PLATINE.bat`.

Sous Linux :

```bash
python3 tools/native/prepare_platinum.py --us /chemin/usa.zip --fr /chemin/fr.zip
python3 tools/native/launch_platinum.py
```

[Mode d’emploi et dépannage](docs/NATIVE-FR.md).

## Direction visuelle obligatoire

- Reprendre les ressources, la caméra, les personnages, les interfaces et les animations de Platine comme référence.
- Garder son monde mêlant décors/modèles 3D et sprites 2D, ses proportions et ses palettes.
- Les nouvelles régions et espèces absentes de Platine nécessitent des ressources nouvelles compatibles avec cette direction ; leurs graphismes officiels « Platine » n’existent pas.
- Les décors procéduraux et l’interface web de Méridien ne sont pas la direction artistique du jeu final.
- Valider d’abord une scène issue de Platine et un combat avant de développer de nouvelles régions.

## État réel

**La base native démarre sous Linux avec les textes français et une première introduction Universe.** Voir [les contrôles et limites de validation](docs/NATIVE-VALIDATION.md). Le port amont reste expérimental ; Windows et la campagne complète ne sont pas encore validés ici.

L’amont propose ses propres exécutables dans ses [releases](https://github.com/cybervisi0n/pokeplatinum/releases). L’outil Universe prépare les ressources depuis une ROM personnelle **USA Rev 1, CPUE**, puis importe les textes et plusieurs interfaces de la ROM **France, CPUF**. Aucun fichier ROM ni ensemble de ressources extraites n’est ajouté ici. Le code référencé est celui de l’amont, pas un travail de portage réalisé par Universe.

La coopération narrative à deux PC, les sept régions, les espèces supplémentaires et les Méga-Évolutions restent à intégrer dans cette base. Le multijoueur existant de Platine n’est pas déjà notre campagne coopérative. Les sauvegardes et le serveur JavaScript de Méridien ne sont pas compatibles avec ce moteur C.

Les exigences sont conservées dans [le cahier des charges](docs/CAHIER-DES-CHARGES.md). Voir [le dossier de migration](docs/PLATINUM-BASE.md). L’ancien mode d’emploi web est conservé dans [ARCHIVE-WEB.md](docs/ARCHIVE-WEB.md), uniquement pour référence.
