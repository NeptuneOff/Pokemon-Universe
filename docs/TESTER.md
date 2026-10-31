# Tester les étapes de développement

Après chaque étape jouable publiée sur `main` : `git pull`, puis ouvrir **JOUER.bat**. Le même lanceur vérifie et installe automatiquement les fichiers de cette révision. Il n'effectue pas de `git pull` pendant une partie.

## Choix du lanceur

| Choix | Fonction |
|---|---|
| 1 — Campagne | Reprendre sa partie normale |
| 2 — Admin | Commencer ou reprendre une partie de test indépendante |
| 3 — Copier ma campagne | Copier la campagne dans le profil admin, puis tester cette copie |

Le choix 3 remplace la progression admin après sauvegarde de secours. Il ne remplace jamais la campagne. Le choix 2 crée une nouvelle partie admin si aucune n'existe. Les profils conservent chacun leur progression lors des mises à jour.

Dans le profil admin, **F10**, puis **Application** ouvre les outils du port Platine :

| Outil | Utilisation |
|---|---|
| Gen Pokemon | Choisir une espèce native et son niveau ; il faut une place dans l'équipe |
| Gen Items | Ajouter un objet natif et une quantité |
| Jump to Map | Aller dans une ville de Sinnoh ou indiquer un identifiant de carte |
| Cheats | Désactiver les rencontres, traverser les murs, fuir un combat de Dresseur |

Attendre d'être sur une carte, sans dialogue, animation ou menu actif avant d'utiliser ces outils. Une téléportation ne joue pas les scènes précédentes et ne valide pas leurs événements : elle sert à inspecter une zone, pas à simuler une progression cohérente. Sauvegarder dans le jeu pour conserver les modifications admin. Les menus techniques hérités sont actuellement en anglais.

**Ces outils ne débloquent que le contenu déjà installé dans le moteur** : ils ne rendent pas jouables les espèces supplémentaires, les Méga ou les régions encore en développement. L'entrée « Multiplayer » du débogueur libntr n'est pas la coopération Universe.

Invocation facultative depuis un terminal Windows, toujours avec le même fichier : `JOUER.bat -Admin` ou `JOUER.bat -Admin -CopyCampaign`. Le double-clic affiche les choix.

## Livraisons et retours

Les versions testables restent sur `main`. La branche `builds/windows-linked` contient les moteurs candidats produits par les vérifications ; elle n'est pas une mise à jour à installer manuellement. Une livraison jouable comprend son moteur et ses ressources dans Git. Un commit de règles ou de documentation n'est pas présenté comme un nouveau contenu activé.

Chaque étape est décrite dans [VERSIONS-TESTABLES.md](VERSIONS-TESTABLES.md), avec le contenu actif, le parcours de vérification et les limites. Les nouveaux mécanismes passent par des étapes séparées : choix initiaux, distribution des espèces, combat Méga, puis campagne et coopération. Chaque publication doit donner un changement observable et indiquer si une nouvelle partie est nécessaire.

Pour un retour : indiquer le choix du lanceur, l'action faite, le résultat attendu et joindre `logs/dernier-lancement.log`. Ce journal contient la révision Git, l'identifiant du moteur, le profil, les vérifications et les sorties natives. Aucun fichier de sauvegarde personnel n'est publié dans Git.
