# Validation de la base native française

## Contrôles réalisés les 19 et 20 octobre 2026

- ROM USA CPUE Rev 1 et France CPUF contrôlées par SHA-1 ; paquets Linux et Windows v0.1.12 contrôlés par SHA-256.
- Installation réelle sous Linux : 340 fichiers nommés, trois archives de textes françaises et 29 correspondances d’archives graphiques vérifiées.
- Les fichiers installés sont recensés avec leur SHA-256 dans `universe-install.json` (local uniquement).
- Sur les 724 banques de `pl_msg.narc`, seule la banque 389 est modifiée ; seul son message 0 change. Les autres messages chiffrés restent identiques. L’original français est conservé.
- Installation Windows également générée : les 340 empreintes de ressources correspondent au manifeste ; `main.exe` est un PE x86-64. Cela ne constitue pas un test d’exécution Windows.
- Dix tests sans ROM : lecture NitroFS, limites/cycles, structure NARC, conservation des messages et commandes inconnues, chiffrement connu, caractères français, correspondances graphiques, extraction ZIP, refus d’écraser une sauvegarde et nettoyage après téléchargement invalide.
- Exécution native sous Linux avec rendu logiciel : démarrage, écran titre « Version Platine », introduction Universe, dialogues Sorbier en français, clavier, interaction avec l’écran tactile et sélection du personnage observés le 19 octobre. AppImage testée sans FUSE.

La source des outils a été restaurée après le nettoyage de l’environnement. Les dix tests ont été relancés ; GitHub Actions est vert pour `a251b08`. Le 20 octobre, l’installation a été recréée puis comparée octet par octet aux ressources sources, à l’exception du dialogue modifié. Les captures ci-dessous ont été prises dans le véritable exécutable natif le 20 octobre.

![Écran titre français](evidence/platine-title-fr.png)

![Introduction Universe dans le moteur natif](evidence/universe-intro-fr.png)

## Contrôles du 22 octobre 2026

- Nouvelle partie native : personnage TEST et rival AMI ; saisie des noms et dialogues en français.
- Arrivée dans la chambre, déplacements, rencontre du rival, passage au rez-de-chaussée, sortie à Bonaugure et entrée dans la maison du rival observés.
- Menu français **SAUVER**, confirmation, écriture de `save.bin`, arrêt complet du processus, redémarrage, écran **CONTINUER** avec TEST, puis retour dans la même chambre : reprise vérifiée. Le déplacement suivant déclenche correctement l’arrivée du rival.
- Copie de cette sauvegarde réelle par le nouvel outil, puis comparaison octet par octet : identique. Les copies restent hors Git.
- Quatorze tests Python locaux passent : les dix tests de ressources et quatre tests du lanceur (première partie sans fichier, conservation des anciens/nouveaux progrès même en cas de code de sortie non nul, échec de copie empêchant le lancement, détection d’une copie altérée).
- La CI des outils Python est désormais configurée pour Linux et Windows. Elle ne lance pas le jeu et ne remplace pas un essai graphique Windows.

![Bonaugure dans le moteur natif](evidence/bonaugure-fr.png)

![Partie retrouvée après redémarrage](evidence/continuer-fr.png)

## Contrôles du 23 octobre 2026

- Comparaison octet par octet de 107 archives installées des familles `fielddata/`, `graphic/`, `battle/graphic/`, `poketool/pokegra/`, `poketool/pokeanm/`, `poketool/icongra/` et `resource/` avec les ROM personnelles validées : aucune différence par rapport aux originaux USA et aux remplacements français déclarés. Ce nombre compte des archives, pas des tuiles individuelles.
- Les 29 correspondances graphiques françaises restent celles de `content/native/graphics.fr.json`. Les cartes et modèles du monde restent ceux de Platine.
- Choix de Tortipouss et combat du rival contre Ouisticram : sprites avant/arrière, décor de combat, interface **ATTAQUE**, capacités **Charge**/**Repli**, PP et évolution de la barre de PV observés. Sélection tactile d’une capacité vérifiée. Combat terminé, retour sur la Route 201 puis scène de la mère à Bonaugure observés.
- Les 14 tests Python passent désormais sur Linux et Windows dans [GitHub Actions](https://github.com/NeptuneOff/Pokemon-Universe/actions/runs/39924992628), commit `2b0f08c`. L’échec Windows précédent venait de la comparaison textuelle des chemins courts/longs dans le test ; la comparaison porte désormais sur l’identité du fichier.

- Le nouvel outil `verify_resources.py` compare toute l’installation aux sources : **340/340 ressources conformes**, 29 correspondances graphiques françaises, aucune ressource manquante ou différente. Les 16 tests locaux passent, dont la détection d’une ressource modifiée malgré un manifeste falsifié et le maintien des sauvegardes intactes.

![Choix de Tortipouss](evidence/choix-tortipouss-fr.png)

![Premier combat natif en français](evidence/combat-tortipouss-fr.png)

## Limites de cette validation

La reprise avec une équipe sauvegardée après le combat reste à contrôler. La session de test a été fermée avant cette sauvegarde ; le dernier point conservé est sur la Route 201 avant le choix du Pokémon. La campagne entière et tous les écrans localisés ne sont pas testés. Aucun essai graphique Windows n’a été effectué. Le son n’a pas été validé (pilote audio factice dans l’environnement de test).

Aucune campagne coopérative, nouvelle région, espèce supplémentaire ni Méga-Évolution n’est livrée par cette étape.

## Reproduire les tests sans ROM

```bash
python -m unittest discover -s tests/native -v
```

## Vérification manuelle à poursuivre

Depuis la sauvegarde de la Route 201, choisir un Pokémon, terminer le combat, finir le dialogue de la mère, sauvegarder puis fermer et reprendre avec l’équipe conservée. Ensuite valider les écrans du sac, de l’équipe, du Pokédex et les boutons français sur Windows et Linux. Conserver les captures réelles et résultats dans Git à chaque étape.
