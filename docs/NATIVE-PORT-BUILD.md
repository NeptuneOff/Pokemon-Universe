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

Le mode `main.exe --universe-self-test` s’exécute avant l’initialisation graphique et le chargement des ressources du SDK. Il appelle les règles depuis l’exécutable complet relié, vérifie le registre et un changement de forme de test, puis renvoie un code de sortie. Sans cet argument, l’entrée originale du port reste utilisée. Ce contrôle ne constitue pas un combat graphique ni un parcours de l’histoire.

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
