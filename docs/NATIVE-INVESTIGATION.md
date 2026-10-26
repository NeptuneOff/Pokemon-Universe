# Les oiseaux de Bonaugure

Première courte quête Universe dans le moteur natif de Platine. Elle est incluse dans les nouvelles préparations. Elle utilise les décors, les personnages et les fenêtres de dialogue du jeu existant. Aucune image de remplacement n’est ajoutée.

## Parcours

Parler au personnage au sud de Bonaugure, près de la mare : il devient le chercheur qui étudie une migration inhabituelle d’Étourmi. La quête est facultative et accessible dès la sortie de la maison.

| Choix | Interaction | Résolution |
|---|---|---|
| Analyste | Examiner le panneau au centre de Bonaugure | Comparer deux heures de passage pour retrouver la direction du vol |
| Éclaireur | Parler à l’éleveuse près du panneau | Choisir une observation discrète pour obtenir un témoignage exploitable |

Le rôle reste choisi pour cette partie. Une des deux directions de migration est tirée à l’acceptation et mémorisée. Revenir parler au chercheur ou changer de carte ne relance pas ce tirage. Ce tirage utilise le générateur du jeu ; il n’est pas encore lié à la personnalisation du personnage ou à une graine de campagne commune.

Une erreur permet de réessayer. « Plus tard » ou B ferme le choix sans faire avancer l’enquête. Le mauvais interlocuteur conserve son interaction d’origine. Une fois l’indice obtenu, revenir voir le chercheur donne une Potion et conserve un rapport différent selon la direction observée. Si le Sac est plein, la récompense reste à récupérer. Les visites suivantes ne donnent pas de Potion supplémentaire.

Utiliser **SAUVER** pour conserver le rôle, l’indice, le rapport et le Sac. Cette étape est une quête solo ; elle ne connecte pas encore deux joueurs et ne modifie pas les dialogues ultérieurs de Sorbier.

## Reprendre une installation existante

Fermer le jeu. Créer une installation séparée avec les ressources mises à jour et une copie de la sauvegarde :

```bash
python tools/native/prepare_platinum.py --gui --output native-runtime/universe-fr --save-from native-runtime/windows-fr
python tools/native/launch_platinum.py --runtime native-runtime/universe-fr
```

Sous Linux, remplacer `windows-fr` par `linux-fr`, ou fournir `--us` et `--fr` au lieu de `--gui`. Une installation et une sauvegarde du même système et du même port v0.1.12 sont requises. L’ancienne installation reste intacte ; la nouvelle reçoit aussi une copie de secours de la sauvegarde importée. La copie ne convertit pas une sauvegarde DS ou celle du prototype web. Si aucune partie n’a encore été sauvegardée, omettre `--save-from`.

Pour une installation sans enquête, utiliser `--intro-only`. `--vanilla` omet aussi le prologue Universe. Le vérificateur accepte les mêmes options ; une installation de la version précédente avec uniquement le prologue se vérifie avec `--intro-only`.

## Intégration native

La définition française et les instructions sont dans `content/native/bonaugure.fr.json`. `tools/native/field_script.py` encode un sous-ensemble des commandes existantes de la machine de scripts de Platine. Aucun binaire du moteur n’est compilé ou modifié.

Les formats sont contrôlés contre la source épinglée : `asm/macros/scrcmd.inc`, `include/data/scripts/scrcmd.h`, `src/scrcmd.c`, `src/scrcmd_item.c`, `src/vars_flags.c`, `generated/vars_flags.txt` et `include/data/map_headers.h`, sous `engine/platinum`.

| Ressource | Modification |
|---|---|
| `fielddata/script/scr_seq.narc`, membre 1052 | Ajouter les nouveaux scripts en fin de membre ; rediriger les entrées 4, 5 et 6, numérotées à partir de zéro |
| `msgdata/pl_msg.narc`, membre 554 | Ajouter 24 messages après les 15 originaux, dont les données chiffrées sont conservées |
| Variable persistante `0x40EA` | Rôle : 0 aucun, 1 analyste, 2 éclaireur |
| Variable persistante `0x40EB` | Étape : 0 non commencée, 1 acceptée, 2 indice obtenu, 3 récompense reçue |
| Variable persistante `0x40EC` | Direction : 0 Littorella, 1 lac |

Ces trois variables sont marquées inutilisées dans la révision amont épinglée et n’y ont pas de références dans les scripts ou la source. Elles sont désormais réservées à Universe. Il faudra revoir cette allocation lors d’un changement de moteur ; ce n’est pas une compatibilité générale avec tous les ROM hacks.

Les empreintes des deux membres sources sont exigées avant toute transformation. Le code original des événements reste en place ; les entrées de transitions, de cinématiques et de boîtes aux lettres sont conservées. Le panneau et l’éleveuse reprennent leurs scripts d’origine hors de leur étape de quête. Les autres membres des deux archives restent identiques. Le prologue garde sa modification séparée dans la banque 389.

Les tests sans ROM exécutent les instructions binaires produites avec un lecteur indépendant : deux rôles × deux variantes, annulation, mauvais choix, mauvaise interaction, Sac plein, reprise de l’état et récompense unique. Ils contrôlent aussi les offsets relatifs et la conservation des données d’origine. Cette simulation ne remplace pas l’exécution graphique ni une sauvegarde native ; voir [les vérifications effectuées](NATIVE-VALIDATION.md).
