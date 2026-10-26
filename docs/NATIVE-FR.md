# Lancer la base Platine PC en français

Cette étape installe le port natif existant de Platine, ses textes et interfaces français, le prologue Universe et une première enquête facultative à Bonaugure. Le reste du parcours reste celui de Platine. La campagne à sept régions et la coopération Universe ne sont pas encore intégrées.

## Windows 64 bits

1. Récupérer ce dépôt avec Git ou **Code → Download ZIP**, puis extraire le ZIP.
2. Installer Python 3 avec Tcl/Tk depuis [python.org](https://www.python.org/downloads/windows/) si nécessaire.
3. Ouvrir `PREPARER-PLATINE.bat`.
4. Choisir sa ROM personnelle **USA Rev 1**, puis sa ROM personnelle **France**. Les `.nds` et les ZIP contenant une seule ROM sont acceptés.
5. Attendre la fin de la préparation, puis ouvrir `JOUER-PLATINE.bat`.

Le port natif est téléchargé automatiquement et son empreinte est contrôlée. Aucune compilation n’est nécessaire. Git et `INITIALISER-SOURCES-PLATINE.bat` servent à récupérer le code du moteur pour le développement ; le sous-module n’est pas requis par l’installateur.

Le paquet Windows a été téléchargé et son empreinte vérifiée. L’exécution graphique a été testée sous Linux ; Windows reste à valider sur une machine Windows.

## Linux x86-64

Python 3 et un environnement graphique sont nécessaires. Depuis la racine du dépôt :

```bash
python3 tools/native/prepare_platinum.py --us /chemin/platine-usa.zip --fr /chemin/platine-fr.zip
python3 tools/native/launch_platinum.py
```

Le lanceur utilise l’AppImage amont et ses bibliothèques, avec extraction temporaire sans FUSE. Les dépendances graphiques du système restent nécessaires. Les ROM ne sont jamais envoyées sur Internet ; le téléchargement concerne uniquement le port natif.

Options :

- `--gui` : sélectionner les ROM dans des fenêtres.
- `--output DOSSIER` : créer une installation distincte ; la lancer ensuite avec `launch_platinum.py --runtime DOSSIER`.
- `--package FICHIER.zip` : utiliser un paquet natif déjà téléchargé.
- `--vanilla` : omettre l’enquête et conserver le premier dialogue français original.
- `--intro-only` : installer uniquement le prologue Universe, sans l’enquête.
- `--save-from DOSSIER` : copier une sauvegarde existante dans la nouvelle installation, avec copie de secours ; l’ancienne installation reste intacte. Fermer le jeu avant cette opération. Voir [le guide de reprise](NATIVE-INVESTIGATION.md).
- `--text-only` : conserver les graphismes USA pour diagnostiquer la localisation.

## Versions reconnues

| Entrée | Code | SHA-1 |
|---|---|---|
| Platine USA Rev 1 | CPUE | `0862ec35b24de5c7e2dcb88c9eea0873110d755c` |
| Platine France | CPUF | `41ea92f794560e347cd9509f5ec9e9d479a4bbf1` |

Chaque ROM complète fait 134 217 728 octets. Une ROM modifiée, tronquée ou d’une autre révision est refusée.

Le port précompilé vient de [cybervisi0n/pokeplatinum v0.1.12](https://github.com/cybervisi0n/pokeplatinum/releases/tag/v0.1.12). La source dans `engine/platinum` est épinglée séparément ; elle n’est pas compilée par l’installateur.

## Localisation et modification

Les 340 fichiers nommés de la ROM USA sont extraits. Trois archives de textes sont remplacées par leurs versions françaises : `msgdata/msg.narc` (624 banques), `msgdata/pl_msg.narc` (724) et `msgdata/scenario/scr_msg.narc` (16).

Vingt-neuf archives graphiques françaises sont importées aux chemins USA attendus par le moteur : titre, saisie de nom, boutons tactiles, polices et plusieurs interfaces (sac, équipe, combat, PC, Pokédex, etc.). Les correspondances explicites et nombres de membres sont dans `content/native/graphics.fr.json`. Chaque nombre est contrôlé avant installation. Ce contrôle structurel ne remplace pas un parcours de tous les menus.

Le premier dialogue d’introduction (banque 389, message 0) présente Universe et une enquête sur les migrations de Pokémon. Son texte source est dans `content/native/prologue.fr.json`. L’enquête **Les oiseaux de Bonaugure**, définie dans `content/native/bonaugure.fr.json`, ajoute 24 messages à la banque 554 et trois interactions aux scripts de cette carte. Les autres messages sont conservés à l’identique, commandes de texte comprises. [Parcours, choix et intégration](NATIVE-INVESTIGATION.md).

Les archives originales sont conservées dans `universe-original/msgdata/pl_msg.narc` et `universe-original/fielddata/script/scr_seq.narc`. Pour comparer sans les événements Universe, créer une installation distincte avec `--vanilla`.

La vidéo d’ouverture garde son archive USA : son équivalent français contient 113 membres contre 116 et ne peut pas être remplacé intégralement sans adaptation. Certains mini-jeux et données propres aux versions commerciales restent à auditer. Les menus techniques du port restent anglais. La localisation intégrale n’est donc pas encore garantie.

## Commandes

| Action | Touche par défaut |
|---|---|
| Se déplacer / choisir | Flèches |
| Confirmer / parler (A) | Z |
| Annuler / courir lorsque disponible (B) | X |
| Menu (X DS) | C |
| Objet enregistré (Y DS) | V |
| Start | Entrée |
| Écran tactile | Clic dans l’écran inférieur |

Le préréglage conserve la résolution interne DS ×1, deux écrans verticaux et une fenêtre 512 ×768. Les décors et personnages proviennent de Platine, pas de l’ancien prototype web.

## Sauvegardes et dépannage

Les lanceurs se placent dans `native-runtime/windows-fr` ou `native-runtime/linux-fr`, où résident les ressources et la sauvegarde `save.bin`. Conserver le dossier entier avant une mise à jour. Python 3 sert aussi au lancement Windows pour activer les copies de secours.

Le lanceur copie `save.bin` avant de démarrer le jeu et après sa fermeture, y compris si le jeu renvoie une erreur. Chaque contenu distinct est conservé dans `universe-backups/<sha256>.sav`, sans écraser les copies précédentes. Une copie identique n’est pas dupliquée. Si la copie préalable échoue, le lancement s’arrête et indique l’erreur. Les copies restent locales, sans envoi réseau ni suppression automatique.

Ce mécanisme ne remplace pas **SAUVER** dans le menu du jeu : il copie uniquement les progrès déjà écrits sur disque. Il ne vérifie pas la validité interne de la partie. Fermer le jeu avant de restaurer une copie ; mettre d’abord le `save.bin` actuel à l’abri, puis copier le fichier `.sav` choisi sous le nom `save.bin` dans le même dossier. Trier les copies par date de modification pour les retrouver. Lancer directement `main.exe` ou l’AppImage contourne ce mécanisme.

L’installateur **refuse toute destination déjà existante**. Il ne supprime ni ne remplace une sauvegarde. Utiliser `--output` pour une autre installation. En cas d’échec, seul son dossier temporaire est nettoyé.

- **ROM incompatible** : vérifier région et révision ; renommer le fichier ne change pas sa compatibilité.
- **Empreinte incorrecte** : le paquet n’est pas celui attendu ; aucune extraction n’est effectuée.
- **Dossier déjà présent** : conserver ses sauvegardes et choisir une autre destination.
- **Sélecteur indisponible** : utiliser `--us` et `--fr` dans un terminal.
- **Plantage** : conserver les journaux du jeu. Le port amont reste expérimental.

Aucune ROM, ressource extraite ou sauvegarde n’est publiée dans Git. Les exécutables sont téléchargés depuis leur auteur ; ses crédits et notices restent applicables.

## Contrôler les ressources installées

Depuis la racine du dépôt, avec les mêmes ROM personnelles que pour la préparation :

```bash
python tools/native/verify_resources.py --us /chemin/usa.zip --fr /chemin/fr.zip
```

Le contrôle compare les 340 ressources attendues octet par octet aux ROM validées, avec les remplacements français, le prologue et l’enquête Universe. Il ne se fie pas aux empreintes du manifeste local, qui pourrait avoir été modifié. Il indique les fichiers manquants ou différents et ne répare ni ne remplace aucun fichier ; la sauvegarde reste intacte.

Utiliser `--runtime DOSSIER` pour une installation particulière, `--json` pour un résultat exploitable par un script, et les mêmes options `--vanilla`/`--intro-only`/`--text-only` que lors de la préparation si elles avaient été choisies. Codes de sortie : 0 = conforme, 1 = différences, 2 = contrôle impossible. Ce contrôle porte sur les ressources du jeu, pas sur l’exécutable, les réglages, les fichiers supplémentaires ni la validité des sauvegardes.
