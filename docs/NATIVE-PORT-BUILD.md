# Compilation du port PC relié à Universe

Cette chaîne produit un **candidat de développement** à partir du code du port PC de Platine. Elle ne remplace pas automatiquement les fichiers jouables de `distribution/windows`. Le joueur utilise toujours `JOUER.bat` ; les outils ci-dessous servent au développement et à la CI.

## Raccordement au moteur

`tools/native/prepare_universe_port.py` vérifie le commit du sous-module, exporte sa source dans un dossier neuf sous `native-runtime`, puis applique les modifications à cette copie. Le sous-module et les sauvegardes ne sont pas modifiés.

Les empreintes des fichiers concernés et cinq révisions de bibliothèques sont dans `native/universe/port-lock.json`. Une source incompatible, un point d’insertion ambigu ou une destination existante arrête la préparation. Les sources Universe et les modifications appliquées sont recensées dans `universe-port-build.json`.

Le candidat relie le registre C au programme et ajoute trois appels dans la copie du moteur :

- Au démarrage de `NitroMain`, journalisation du registre chargé.
- À la création d’un `BattleContext`, initialisation de l’état Universe du combat.
- À la libération du contexte, nettoyage de cet état.

Ces appels préparent le raccordement des mécanismes de combat. **Ils n’activent pas encore une transformation, une nouvelle espèce ou une commande Méga.** Les statistiques effectives, talents, objets, sprites et choix d’action restent à raccorder.

Le composant `journey.c` contient les règles du nouveau départ et leur conservation. Le diagnostic vérifie aussi un tirage pour deux personnages, un choix, la conservation du trio et l'association du compagnon avec sa gemme. Il ne présente pas encore le nouveau choix dans l'écran natif et n'ajoute pas de Pokémon à une équipe.

Le mode `main.exe --universe-self-test` s’exécute avant l’initialisation graphique et le chargement des ressources du SDK. Il appelle les règles depuis l’exécutable complet relié, vérifie le registre, un changement de forme de test et les statistiques d'un Méga-Dracaufeu X niveau 50 Jovial, puis renvoie un code de sortie. La publication exige aussi le résultat `stats_rules: passed`. Sans cet argument, l’entrée originale du port reste utilisée. Ce contrôle ne constitue pas un combat graphique ni un parcours de l’histoire.

## Chaîne Windows

[Build natif Windows](../.github/workflows/build-native-port.yml) utilise MSYS2 UCRT64 et compile le port complet. Le Python UCRT64 est nécessaire pour Meson ; `PYTHONUTF8=1` permet aux outils amont de lire correctement leurs JSON et textes. L’environnement MSYS2 et certains outils amont restent des dépendances à auditer lors des mises à jour ; ce verrouillage n’est pas une promesse de compilation binaire identique sur toute machine.

Après compilation, la CI prépare la distribution française existante depuis Git, puis `tools/native/stage_linked_runtime.py` associe ses ressources vérifiées au moteur recompilé dans un dossier distinct. Le programme de préparation :

- Vérifie les ressources contre les tailles et empreintes de `release.json`.
- Vérifie les révisions du moteur et des bibliothèques déclarées par la préparation des sources.
- Copie seulement les fichiers autorisés et contrôle le format x64 de l’exécutable.
- Exclut les ROM, sauvegardes, journaux et fichiers supplémentaires des dossiers sources.
- Conserve les empreintes du moteur recompilé et la version des ressources dans la provenance du candidat.

Un second diagnostic du candidat s’exécute avec un `PATH` réduit aux fichiers préparés et à Windows : les DLL du compilateur ne doivent pas masquer un fichier manquant. Les traces et les fichiers du candidat sont conservés comme artefacts de développement de la CI. Ils ne sont pas une nouvelle livraison du jeu final et ne demandent aucun téléchargement manuel supplémentaire au joueur.

## Reproduire en développement

Initialiser le sous-module, puis préparer une copie neuve :

```bash
git submodule update --init engine/platinum
python tools/native/prepare_universe_port.py
```

Dans un environnement MSYS2 UCRT64 disposant des paquets indiqués par le workflow :

```bash
cd native-runtime/universe-port
export PYTHONUTF8=1
make build_win64/build.ninja
subprojects/meson-1.12.0/meson.py compile -C build_win64 main
```

Le workflow collecte ensuite explicitement l’exécutable, les deux fichiers système et les cinq DLL, puis assemble le candidat français après vérification de l’installation de base. Il ne passe pas par le script de conditionnement amont. Les dossiers de travail et leurs journaux restent sous `native-runtime` ; il ne faut pas les copier à la place d’une installation contenant une partie en cours.

## Candidat récupérable par Git

Après réussite des diagnostics, [la publication automatique](../.github/workflows/publish-linked-port.yml) vérifie le résultat émis par l’exécutable, ses empreintes, celles des sources Universe et celles des ressources françaises. Elle prépare les fragments internes consommés par le lanceur et met à jour la branche générée **`builds/windows-linked`**, sans réécrire son historique. Les ROM, sauvegardes, fichiers supplémentaires de l’artefact et fichiers non déclarés de la distribution source sont exclus. La notice des données Showdown est ajoutée aux licences installées.

Cette branche est une **version de développement du moteur relié**, pas la campagne complète demandée. Elle utilise le même `JOUER.bat` que la version principale et ne demande ni ZIP manuel, ni ROM, ni installation de Python pour jouer. Le retour d’un diagnostic natif ne prouve pas encore le rendu graphique d’un combat Méga. La version principale n’est pas remplacée automatiquement par ces candidats.

## Validation

Les tests de préparation contrôlent le maintien des sources originales, les révisions incompatibles, les modifications ambiguës, le refus d’écrasement et le nettoyage d’un échec. Les tests d’assemblage contrôlent la conservation des ressources françaises, le remplacement du moteur, l’exclusion des données personnelles et le refus d’une ressource ou d’un exécutable incompatible.

Le bilan de compilation et les limites de validation graphique sont consignés dans [NATIVE-VALIDATION.md](NATIVE-VALIDATION.md).

## Parcours graphique de développement

Le workflow `visual-native-port.yml` reconstruit le candidat depuis ses paquets Git, vérifie tous les fichiers, puis lance son véritable exécutable Windows sous Wine, Xvfb et Mesa logiciel. Les captures proviennent directement de sa fenêtre ; elles ne sont pas recréées. Les actions clavier et tactiles sont dans `tests/native/visual_recipe.json`. Un résultat positif indique que ce parcours a été exécuté et capturé ; il ne valide pas automatiquement les textes, l'histoire complète, une Méga ou un bureau Windows natif.

Le test utilise une installation neuve et son propre préfixe Wine. Son fichier de mémoire flash `save.bin`, lorsqu'il existe, peut être conservé dans l'artefact `universe-disposable-qa-checkpoint`, avec une empreinte et le numéro exact du build. Il n'est jamais ajouté aux preuves Git ou aux paquets du jeu. Son intégrité ne prouve pas que le jeu a terminé une sauvegarde valide.

Pour reprendre un tel point de test, indiquer le numéro du précédent run dans `tests/native/visual_checkpoint.json` et adapter le parcours à l'écran de reprise. Le checkpoint doit correspondre exactement au build candidat ; un fichier altéré, supplémentaire ou d'un autre build est refusé avant copie. Le test ne cherche aucune sauvegarde sur un poste joueur et refuse d'écraser un fichier flash existant.

Une reprise exige aussi le SHA immuable du candidat dans `candidate_ref`, pour qu'une publication plus récente ne change pas de moteur pendant le test. Le paramètre facultatif `live_seconds` ouvre une session de contrôle bornée à 1 200 secondes au maximum. Les lots de touches et de clics sont lus dans `visual-control.json` de la branche `codex/visual-input` ; chaque lot porte le numéro exact du run, une séquence croissante et des `steps` au même format que le parcours. Un lot d'une autre session ou déjà exécuté est ignoré. `finish: true` termine la session après capture.

Les images et le rapport intermédiaire sont publiés pendant cette session dans la branche de preuves, avec un index Git séparé. Le fichier flash reste dans le checkpoint de CI ; aucune commande shell n'est issue des lots d'entrée. Ce contrôle sert au développement du jeu, pas au lancement sur un PC joueur.
