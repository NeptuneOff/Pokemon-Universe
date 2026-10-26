# Pokémon Universe — base Platine PC

**Changement de base : le prototype web Méridien 0.2 est abandonné comme moteur du jeu final.** Il ne respecte pas les visuels demandés. Ses fichiers restent disponibles pour conserver les essais de scénario et de coopération, mais ne constituent pas la nouvelle version du jeu.

## Le code du jeu existant

La nouvelle référence technique est [Pokémon Platinum PC Port](https://github.com/cybervisi0n/pokeplatinum), dérivé de [pret/pokeplatinum](https://github.com/pret/pokeplatinum) et des bibliothèques libntr.

Le sous-module [engine/platinum](engine/platinum) référence exactement le commit `35067868f64f23d25d17ac3e536cfdd9a7f40523`. Il contient le code existant de Platine porté vers PC, sans modification de sa source. Les outils Universe appliquent séparément un prologue et une première enquête aux ressources françaises locales. Il ne s’agit pas d’un nouveau moteur web imitant Pokémon.

```bash
git clone --recurse-submodules https://github.com/NeptuneOff/Pokemon-Universe.git
```

Pour un clone déjà présent :

```bash
git pull --ff-only
git submodule update --init engine/platinum
```

## Lancer la base native en français

**Avec une archive Windows déjà préparée :** extraire tout le ZIP, puis ouvrir **`JOUER.cmd`**. Aucun choix de ROM, aucune installation de Python et aucun émulateur ne sont nécessaires. Le lanceur conserve les sauvegardes avec Windows PowerShell. Cette archive privée est préparée séparément ; le ZIP public du code GitHub ne contient pas les ressources du jeu.

**Préparation depuis le code source** (développement ou nouvelle installation) :

Sous Windows : **`PREPARER-PLATINE.bat`**, sélectionner ses ROM personnelles USA Rev 1 et France (`.nds` ou ZIP), puis **`JOUER-PLATINE.bat`**. Python 3 est requis pour la préparation. Le port est téléchargé et vérifié automatiquement ; aucune compilation n’est demandée.

Le ZIP du dépôt suffit pour cette préparation. Pour développer le moteur, utiliser Git et `INITIALISER-SOURCES-PLATINE.bat`.

Sous Linux :

```bash
python3 tools/native/prepare_platinum.py --us /chemin/usa.zip --fr /chemin/fr.zip
python3 tools/native/launch_platinum.py
```

[Mode d’emploi et dépannage](docs/NATIVE-FR.md).

**Première quête : [Les oiseaux de Bonaugure](docs/NATIVE-INVESTIGATION.md).** Parler au chercheur au sud du village, choisir analyste ou éclaireur, recueillir un indice puis revenir pour une récompense unique. Le rôle, la piste tirée au départ et la progression utilisent la sauvegarde native. Le guide explique aussi comment reprendre une ancienne partie dans une installation séparée avec `--save-from`.

**Suite : [Avant le départ, à Littorella](docs/NATIVE-INVESTIGATION.md#suite--avant-le-départ).** Après avoir rendu le premier rapport et obtenu le Pokédex, reparler à Sorbier et choisir **Enquête**. L’analyste examine le PC du laboratoire ; l’éclaireur interroge l’éleveur près de la maison de l’assistant. Le rapport final tient compte du rôle et de la direction observée. L’option **Pokédex** conserve les interactions habituelles de Sorbier.

Les lanceurs conservent une copie de chaque sauvegarde distincte avant et après le jeu. La commande **SAUVER** du menu reste nécessaire. `DEMARRER-DUO.bat` indique l’état du duo natif ; l’ancien essai web dispose d’un lanceur explicitement nommé `DEMARRER-PROTOTYPE-WEB-ARCHIVE.bat`.

## Direction visuelle obligatoire

- Reprendre les ressources, la caméra, les personnages, les interfaces et les animations de Platine comme référence.
- Garder son monde mêlant décors/modèles 3D et sprites 2D, ses proportions et ses palettes.
- Les nouvelles régions et espèces absentes de Platine nécessitent des ressources nouvelles compatibles avec cette direction ; leurs graphismes officiels « Platine » n’existent pas.
- Les décors procéduraux et l’interface web de Méridien ne sont pas la direction artistique du jeu final.
- Valider d’abord une scène issue de Platine et un combat avant de développer de nouvelles régions.

## État réel

**La base native fonctionne sous Linux avec les textes français et une première introduction Universe : exploration, premier combat et sauvegarde/reprise avant le combat vérifiés.** Voir [les contrôles et limites de validation](docs/NATIVE-VALIDATION.md). Le port amont reste expérimental ; Windows et la campagne complète ne sont pas encore validés ici.

L’amont propose ses propres exécutables dans ses [releases](https://github.com/cybervisi0n/pokeplatinum/releases). L’outil Universe prépare les ressources depuis une ROM personnelle **USA Rev 1, CPUE**, puis importe les textes et plusieurs interfaces de la ROM **France, CPUF**. Aucun fichier ROM ni ensemble de ressources extraites n’est ajouté ici. Le code référencé est celui de l’amont, pas un travail de portage réalisé par Universe.

La coopération narrative à deux PC, les sept régions, les espèces supplémentaires et les Méga-Évolutions restent à intégrer dans cette base. Le multijoueur existant de Platine n’est pas déjà notre campagne coopérative. Les sauvegardes et le serveur JavaScript de Méridien ne sont pas compatibles avec ce moteur C.

Les exigences sont conservées dans [le cahier des charges](docs/CAHIER-DES-CHARGES.md). Voir [le dossier de migration](docs/PLATINUM-BASE.md). L’ancien mode d’emploi web est conservé dans [ARCHIVE-WEB.md](docs/ARCHIVE-WEB.md), uniquement pour référence.
