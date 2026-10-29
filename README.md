# Pokémon Universe — Platine PC en français

## Jouer sous Windows

Dans ton dépôt existant, ferme le jeu, puis :

```bat
git pull --ff-only
JOUER.bat
```

Tu peux aussi double-cliquer sur **JOUER.bat** après le pull. C’est le seul lanceur à utiliser. Il prépare les fichiers, vérifie l’installation, reprend ta sauvegarde compatible et démarre le jeu. **Aucun ZIP à récupérer, aucune ROM à sélectionner, aucun Python à installer, aucune compilation.**

Pour une première installation, avec Git déjà installé :

```bat
git clone https://github.com/NeptuneOff/Pokemon-Universe.git
cd Pokemon-Universe
JOUER.bat
```

Windows 10/11 **64 bits**, un pilote graphique compatible avec le port et environ **1 Go libre** sont recommandés pour le dépôt, les fichiers préparés et les copies de sauvegarde. Les données Windows représentent environ 92 Mo dans Git. Le sous-module du moteur n’est pas nécessaire pour jouer. Une fois le clone ou le pull terminé, le lanceur fonctionne hors connexion et sans droits administrateur.

**En cas d’erreur : transmettre `logs/dernier-lancement.log`.** Les journaux détaillent les étapes, la version, les fichiers vérifiés, les erreurs natives et le code de sortie. Ils restent sur ton PC. [Commandes, sauvegardes et dépannage](docs/NATIVE-FR.md).

## Contenu actuel

La base est le [port PC de Pokémon Platine](https://github.com/cybervisi0n/pokeplatinum), avec les ressources de Platine, ses cartes, ses personnages, son interface et ses combats. Le préréglage conserve la résolution interne DS ×1 et les deux écrans verticaux. L’ancien prototype web ne sert plus de moteur.

Le jeu comprend le prologue Universe, **Les oiseaux de Bonaugure**, puis sa suite **Avant le départ** à Littorella. Le rôle analyste ou éclaireur, la piste initiale et la progression sont persistants. Après le rapport de Bonaugure et l’obtention du Pokédex, parler à Sorbier et choisir **Enquête**. [Parcours des quêtes](docs/NATIVE-INVESTIGATION.md).

**C’est une version de développement de la base Platine, pas encore le jeu final à sept régions.** La coopération narrative à deux PC, les espèces supplémentaires et les Méga-Évolutions restent à intégrer. Le reste du parcours suit Platine. Les textes et 29 archives graphiques sont localisés ; certains éléments et menus techniques restent à auditer.

[Les validations](docs/NATIVE-VALIDATION.md) distinguent les tests du lanceur Windows, les vérifications des ressources et les parcours graphiques réellement effectués. La campagne entière n’a pas été validée.

## Développement

Le [registre natif et les règles de Méga-Évolution](docs/NATIVE-EXPANSION.md) sont en cours de développement : 1 025 espèces et 97 formes Méga dans l’instantané du 26 octobre 2026. **Ce composant C n’est pas encore raccordé aux combats du jeu distribué.**

Les sources Universe, les outils et la distribution préparée sont versionnés ensemble. Le moteur existant est référencé dans `engine/platinum`, au commit `35067868f64f23d25d17ac3e536cfdd9a7f40523`, sans modification de sa source. Ses notices et celles de ses bibliothèques sont conservées dans [content/native/portable/licenses](content/native/portable/licenses) et installées avec le jeu.

Pour consulter les sources du moteur uniquement :

```bash
git submodule update --init engine/platinum
```

[Format de la distribution Git](distribution/README.md) · [Outils de préparation et Linux](docs/NATIVE-FR.md#outils-de-développement-et-linux) · [Cahier des charges](docs/CAHIER-DES-CHARGES.md) · [Migration vers Platine](docs/PLATINUM-BASE.md) · [Ancien prototype archivé](docs/ARCHIVE-WEB.md).
