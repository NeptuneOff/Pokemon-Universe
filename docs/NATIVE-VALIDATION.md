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

## Première enquête Universe — 26 octobre 2026

- Ajout des événements natifs de Bonaugure : choix de rôle, piste persistante, collecte d’indice et Potion unique. Les scènes obligatoires de Platine restent en place.
- Les 25 tests Python passent localement, dont les deux rôles et les deux variantes dans un lecteur de bytecode indépendant, les annulations, les erreurs rattrapables, le Sac plein et la reprise de l’état. Cette reprise simulée ne constitue pas encore une vérification de la sauvegarde native de la quête.
- Vérification sur les ROM personnelles : seul le membre 1052 de l’archive de scripts change ; dans les textes, seule la banque 554 change en plus du prologue 389. Les 15 messages originaux de Bonaugure restent identiques. Les 14 identifiants de commandes émis correspondent à la source moteur épinglée.
- Nouvelle préparation Windows générée avec l’enquête ; le moteur graphique Windows n’est pas exécuté ici. Les 12 tests du prototype web archivé passent aussi et ne valident pas la coopération native.
- Lors de cette première livraison, le parcours graphique et la reprise de l’enquête restaient à valider. Ils ont depuis été contrôlés pour le rôle analyste, ci-dessous.

## Parcours natif de l’enquête — 26 octobre 2026

- Reprise d’une sauvegarde de TEST dans sa chambre, puis scènes du rival et de la mère, sortie à Bonaugure et rencontre du chercheur : parcours exécuté dans le port Linux sans modifier la sauvegarde ni téléporter le personnage.
- Choix **Analyste** dans la fenêtre native. Le capteur indique Littorella à 6 h et le lac à 6 h 10. Une réponse erronée affiche l’explication et laisse réessayer ; **Vers le lac** donne l’indice.
- Retour au chercheur, compte rendu correspondant, réception d’une Potion. Une nouvelle visite affiche le rapport au lieu de donner une deuxième récompense. Le Sac français indique **Potion × 1**.
- Sauvegarde avec **SAUVER**, fermeture complète du processus, redémarrage puis **CONTINUER** : retour au même endroit, même rapport vers le lac, **Potion × 1** conservée après une nouvelle interaction. L’étape de quête et l’inventaire ont donc persisté dans une véritable sauvegarde native.
- Le rôle éclaireur et la direction vers Littorella restent couverts par le lecteur de bytecode indépendant ; leur parcours graphique n’a pas encore été exécuté.

![Choix du rôle dans le moteur natif](evidence/enquete-choix-role-fr.png)

![Indice obtenu au panneau](evidence/enquete-indice-fr.png)

![Rapport retrouvé après fermeture et relance](evidence/enquete-rapport-repris-fr.png)

![Une seule Potion, conservée après relance](evidence/enquete-sac-repris-fr.png)

## Suite à Littorella — 26 octobre 2026

- Ajout de deux banques de scripts : laboratoire (1064) et ville (1059), avec textes ajoutés dans les banques 565 et 561. La première enquête reste inchangée. Aucune archive graphique, carte ou animation n’est modifiée.
- Après le rapport de Bonaugure, Sorbier offre **Enquête**, **Pokédex** et **Plus tard**. Les scènes d’obtention du Pokédex et les autres entrées de scripts restent identiques. Le PC pour l’analyste et l’éleveur pour l’éclaireur donnent un indice distinct ; le rapport final dépend aussi de la direction initiale.
- 32 tests Python : 31 exécutés localement, un test PowerShell réservé à Windows. Les nouveaux cas couvrent les quatre combinaisons rôle/direction, les changements de carte, la reconstitution de l’état persistant, les annulations, les mauvaises réponses, le Sac plein, les trois Poké Balls uniques, les dialogues Pokédex accessibles et le refus de ressources incompatibles.
- Installations Linux et Windows préparées et comparées aux ROM personnelles : **340/340 ressources conformes** pour chacune. La sauvegarde de la première enquête est copiée octet pour octet dans une nouvelle installation ; l’ancienne reste intacte.
- Le parcours graphique de cette suite reste à valider ; les tests de scripts ne constituent pas une exécution de l’ensemble de la campagne.

## Archive Windows prête à extraire

- Outil `package_windows.py` : copie uniquement les huit fichiers du paquet moteur vérifié, les 340 ressources recensées, la configuration et les fichiers du lanceur. Les ROM, sauvegardes de test, journaux et fichiers sans rapport sont exclus.
- `JOUER.cmd` utilise Windows PowerShell ; Python n’est pas une dépendance de cette archive. Les sauvegardes distinctes sont conservées avant et après le jeu. Deux lanceurs ne peuvent pas partager simultanément le même dossier de sauvegarde.
- Test du paquet : contenu autorisé, sauvegardes exclues, originaux inchangés, exécutable altéré refusé. Un test Windows exécute le lanceur avec un petit programme de test pour contrôler la reprise après un code de sortie non nul et le refus d’une copie de secours corrompue. Ce programme de test n’est pas le jeu.

## Limites de cette validation

La reprise avec une équipe sauvegardée après le combat reste à contrôler. Le point de test durable actuel est à Bonaugure après l’enquête analyste, avant le premier Pokémon. Les anciens essais de combat n’ont pas laissé une sauvegarde exploitable après le combat. La campagne entière et tous les écrans localisés ne sont pas testés. Aucun essai graphique Windows n’a été effectué. Le son n’a pas été validé (pilote audio factice dans l’environnement de test).

Aucune campagne coopérative, nouvelle région, espèce supplémentaire ni Méga-Évolution n’est livrée par cette étape.

## Reproduire les tests sans ROM

```bash
python -m unittest discover -s tests/native -v
```

## Vérification manuelle à poursuivre

Depuis le point de Bonaugure, poursuivre les scènes du rival, choisir un Pokémon, terminer le combat, finir le dialogue de la mère, sauvegarder puis fermer et reprendre avec l’équipe conservée. Rejoindre Littorella, obtenir le Pokédex et exécuter la suite de l’enquête. Valider aussi le parcours éclaireur, les écrans d’équipe et du Pokédex, puis le lancement et les boutons français sur Windows. Conserver les captures réelles et résultats dans Git à chaque étape.
