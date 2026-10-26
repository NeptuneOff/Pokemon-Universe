# Distribution Windows dans Git

Le joueur utilise uniquement `JOUER.bat` à la racine après le clone ou le pull. Les fragments de ce dossier sont des données internes, à laisser en place ; aucune manipulation manuelle ni extraction d’archive n’est demandée.

## Contenu et contrôle

`windows/release.json` décrit chaque fichier installé, sa taille et son SHA-256, ainsi que les paquets et leurs fragments de 512 Kio. Ils sont de vrais fichiers Git, sans LFS. Les paquets internes sont reconstruits et extraits avec .NET, fourni avec Windows.

- `engine` : les huit fichiers du paquet Windows amont v0.1.12, octet pour octet ; SHA-256 du paquet `0db11b84199b1b7cebdbdb8ceca26fc4c2a2a1c2f448aef86bfde8b26f49e5ec`.
- `assets` : ressources graphiques, cartes, son et données non modifiées par les quêtes.
- `story` : archive de scripts, trois archives de textes, manifeste d’installation et notices des dépendances.

La distribution contient 340 ressources du jeu, huit fichiers moteur, un manifeste d’installation et six notices : **355 fichiers installés**, **91 516 448 octets compressés**, **223 757 732 octets installés**. Le build initial est `e54911cd93dbf5e82db0`. Les 340 ressources ont été comparées aux sources personnelles validées, en tenant compte des remplacements français, du prologue et des enquêtes de Bonaugure et Littorella.

Aucun fichier NDS complet, sauvegarde personnelle, réglage utilisateur ou journal n’entre dans la distribution. Les notices sont aussi lisibles dans `content/native/portable/licenses/`. Les sources du moteur sont référencées par `engine/platinum` et son dépôt amont.

## Reconstruction pour le développement

Après préparation et vérification d’un dossier Windows neuf :

```bash
python tools/native/verify_resources.py --us /chemin/usa.zip --fr /chemin/fr.zip --runtime native-runtime/windows-git-source
python tools/native/build_git_distribution.py --runtime native-runtime/windows-git-source --package native-runtime/packages/release_win64.zip --output native-runtime/distribution-candidate
```

Le constructeur refuse une destination existante. Comparer le candidat à `distribution/windows`, puis remplacer les fichiers versionnés concernés et contrôler la CI. Il produit des paquets déterministes : modifier uniquement une quête ne modifie pas les paquets moteur et graphismes. Ne jamais régénérer les ressources à partir d’une installation contenant des fichiers modifiés non vérifiés.

Le build est identifié par les 20 premiers caractères SHA-256 du manifeste canonique avant ajout de `build_id`. Le lanceur vérifie toutes les empreintes de fichiers, fragments et paquets utilisés, refuse les chemins inattendus et prépare les données avant de toucher à l’installation cible. Les sauvegardes sont gérées séparément et conservées par contenu.

La CI Windows exécute des tests d’installation, réparation, mise à jour/retour de version, import de sauvegarde, erreurs natives et verrouillage avec un exécutable de test indépendant. Elle prépare également la vraie distribution depuis le checkout Git et vérifie une seconde ouverture déjà installée. Cette vérification n’est pas un parcours graphique du jeu sous Windows.
