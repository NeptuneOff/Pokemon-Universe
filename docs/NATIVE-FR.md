# Jouer sous Windows depuis Git

## Installation et mise à jour

Fermer le jeu, exécuter `git pull --ff-only` dans le dépôt, puis ouvrir **JOUER.bat**. Pour un premier clone :

```bat
git clone https://github.com/NeptuneOff/Pokemon-Universe.git
cd Pokemon-Universe
JOUER.bat
```

Un seul lanceur est nécessaire. Windows PowerShell 5.1, fourni avec Windows 10/11 64 bits, prépare le moteur et les ressources déjà contenus dans le dépôt. Aucun téléchargement supplémentaire, aucune sélection de ROM, aucun Python, Git LFS, émulateur ou compilateur au moment de jouer. Le sous-module du moteur sert uniquement au développement.

Le premier clone récupère environ 92 Mo de données de jeu, en plus des sources. Prévoir environ 1 Go libre pour les fichiers Git, l’installation temporaire et le jeu installé. Les mises à jour conservent les anciennes installations et copies de sauvegarde : leur espace augmente avec les versions.

À chaque lancement, les fichiers installés sont contrôlés par SHA-256. Un fichier absent ou altéré déclenche une préparation depuis les paquets du dépôt. Les paquets sont tous vérifiés avant de remplacer des fichiers du moteur. La configuration et la partie ne font pas partie des fichiers remplacés. Le lanceur applique la version du dépôt local ; il n’exécute pas lui-même `git pull`.

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

Le réglage initial conserve la résolution interne DS ×1, deux écrans verticaux et une fenêtre 512 ×768. Les décors et personnages sont ceux de Platine. Utiliser **SAUVER** dans le menu du jeu avant de quitter.

## Sauvegardes

Le jeu installé et sa partie se trouvent dans `native-runtime/windows-builds/<version>/`. Le fichier `native-runtime/windows-current.json` indique la version utilisée pour la dernière session. Les sauvegardes distinctes sont copiées avant et après la session dans `native-runtime/universe-backups/<sha256>.sav`.

Après une mise à jour, le lanceur importe la partie de la dernière installation utilisée, garde l’original et copie ses réglages si le nouveau dossier n’en a pas. Le même mécanisme conserve la progression la plus récente lorsqu’on revient à une ancienne version compatible. Une sauvegarde déjà présente dans la destination est protégée avant remplacement. Les versions du moteur doivent être compatibles ; sinon le lancement s’arrête en conservant les fichiers.

Lors de la première utilisation, une ancienne partie située dans `native-runtime/windows-fr` est reprise automatiquement si son manifeste indique le même moteur Windows. Une partie issue d’une ancienne archive située ailleurs n’est pas recherchée sur le disque : fermer le jeu et conserver son dossier pour une migration explicite.

Les copies protègent les données déjà écrites sur disque ; elles ne remplacent pas **SAUVER**, ne récupèrent pas les progrès non enregistrés et ne vérifient pas la validité interne de la partie. Une sauvegarde vide ou une copie de secours altérée arrête le lancement. Rien n’est envoyé sur Internet et les anciennes copies ne sont pas supprimées automatiquement.

Éviter de lancer directement `main.exe` : cela contourne les copies et le journal du lanceur. Deux sessions lancées par `JOUER.bat` ne peuvent pas écrire en même temps. Pour restaurer manuellement une copie, fermer le jeu, identifier son dossier dans le dernier journal, mettre le `save.bin` actuel à l’abri, puis copier la sauvegarde choisie à cet emplacement sous le nom `save.bin`.

## Logs et dépannage

Le fichier à transmettre est **`logs/dernier-lancement.log`**. Une copie datée de chaque session est conservée dans le même dossier, avec la sortie standard et les erreurs natives séparées. Le journal indique la version du jeu et du moteur, la révision Git lorsqu’elle est accessible, Windows/PowerShell, les étapes, les chemins, les vérifications, les exceptions, les sauvegardes protégées et le code de sortie. Après la fermeture du jeu, il inclut les dernières lignes des sorties natives et de `DbgLog.txt` si ce fichier a été écrit pendant la session.

Si le jeu se bloque sans se fermer, conserver aussi les fichiers `jeu-*.stdout.log` et `jeu-*.stderr.log` de cette session. Si un second lancement est refusé, son diagnostic daté est affiché dans la console ; le journal de la session active reste intact.

- **Fichier absent / taille ou empreinte incorrecte** : le diagnostic nomme le fichier concerné. Vérifier que `git pull --ff-only` s’est terminé. Ne pas supprimer `native-runtime` ni les sauvegardes.
- **Jeu déjà ouvert / fichier verrouillé** : fermer la session précédente avant de relancer.
- **Copie de secours altérée / sauvegarde vide / installation précédente absente** : conserver les fichiers et transmettre le log pour restaurer la bonne partie.
- **Échec graphique ou fermeture immédiate** : transmettre le log ; il contient les erreurs natives disponibles et le code de sortie. Le port reste expérimental et dépend du pilote graphique de la machine.
- **Échec de pull pour modifications locales** : conserver les modifications et le message Git ; ne pas employer `reset --hard` ou `clean` pour tenter une réparation.

## Outils de développement et Linux

Cette section n’est pas nécessaire pour jouer sous Windows. Les anciens scripts de préparation restent disponibles pour fabriquer une nouvelle distribution ou une installation Linux à partir des sources personnelles :

```bash
python3 tools/native/prepare_platinum.py --us /chemin/usa.zip --fr /chemin/fr.zip
python3 tools/native/launch_platinum.py
```

Sous Linux, Python 3 et un environnement graphique sont nécessaires. Le lanceur utilise l’AppImage amont avec extraction temporaire sans FUSE. `--output DOSSIER` prépare une installation distincte ; `launch_platinum.py --runtime DOSSIER` la lance. `--save-from DOSSIER` importe une sauvegarde compatible en conservant sa source. `--package FICHIER.zip` utilise le paquet moteur local. Les options `--vanilla`, `--intro-only`, `--bonaugure-only` et `--text-only` permettent de comparer les étapes de modification. La préparation refuse une destination déjà existante.

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

## Contrôler les ressources installées

Depuis la racine du dépôt, avec les mêmes ROM personnelles que pour la préparation :

```bash
python tools/native/verify_resources.py --us /chemin/usa.zip --fr /chemin/fr.zip
```

Le contrôle compare les 340 ressources attendues octet par octet aux ROM validées, avec les remplacements français, le prologue et l’enquête Universe. Il ne se fie pas aux empreintes du manifeste local, qui pourrait avoir été modifié. Il indique les fichiers manquants ou différents et ne répare ni ne remplace aucun fichier ; la sauvegarde reste intacte.

Utiliser `--runtime DOSSIER` pour une installation particulière, `--json` pour un résultat exploitable par un script, et les mêmes options `--vanilla`/`--intro-only`/`--text-only` que lors de la préparation si elles avaient été choisies. Codes de sortie : 0 = conforme, 1 = différences, 2 = contrôle impossible. Ce contrôle porte sur les ressources du jeu, pas sur l’exécutable, les réglages, les fichiers supplémentaires ni la validité des sauvegardes.
