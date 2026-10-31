# Versions testables

## Premier choix — starters aléatoires natifs

Distribution Windows : `74a08fe19741926b6c30`. Moteur compilé depuis `7bd2e2e0f7eae6dcc6177a7c78987e5f7ab094a9` ; les 340 ressources françaises et les décors de Platine sont conservés.

- **Actif** : trois propositions persistantes, une Plante, une Feu et une Eau, tirées parmi les 12 starters des générations 1 à 4 ; sprites, cris, noms français et Pokémon remis raccordés au choix. Le rival et l'autre personnage prennent les offres restantes ; leurs évolutions et capacités suivent la bonne lignée.
- **À essayer** : `git pull --ff-only`, puis `JOUER.bat`. Choisir **4 — Nouvelle partie Admin**, puis atteindre la mallette de Sorbier sur la Route 201, regarder les trois propositions, choisir son Pokémon et faire le premier combat. Le trio Sinnoh reste un résultat possible du tirage.
- **Compatibilité** : une partie antérieure au choix bénéficie du tirage ; une partie ayant déjà reçu son starter conserve son Pokémon. Les propositions ne changent pas lors d'une reprise. Ne pas effacer sa campagne pour tester.
- **Limites** : les 15 starters postérieurs à Platine, le second compagnon et sa gemme, les Méga en combat, les nouveaux habitats et le duo réseau restent à intégrer. Le choix 4 du lanceur permet de recommencer les tests en protégeant la partie admin précédente ; les outils natifs existants restent accessibles.

[Compilation Windows et diagnostic portable](https://github.com/NeptuneOff/Pokemon-Universe/actions/runs/41225809067) réussis. [76 tests natifs sous Windows et contrôles Linux](https://github.com/NeptuneOff/Pokemon-Universe/actions/runs/41232153107) réussis. Le test du véritable adaptateur C couvre la conservation, le don et les lignées des personnages. Le menu, le don de Gobou, le combat contre Germignon, la sauvegarde et la reprise ont été parcourus dans le véritable exécutable sous Wine. Les preuves graphiques du parcours sont décrites dans [NATIVE-VALIDATION.md](NATIVE-VALIDATION.md).

## Résonance — début du récit et profil admin

Distribution Windows : `47cbbf0e8630133f0426`. Moteur Universe compilé depuis `55f930ab529a74f2c461bb7703c393cea831a5d3` ; ressources françaises conservées.

- **Actif** : nouvelle introduction sur les Méga-Gemmes et les migrations ; dialogues réécrits dans les deux enquêtes existantes de Bonaugure et du laboratoire de Littorella ; lanceur à choix Campagne/Admin/Copie de campagne ; outils natifs de test accessibles par F10 dans le profil admin.
- **À essayer** : lancer le choix 2 pour une partie indépendante, lire l'introduction, atteindre une carte, ouvrir F10 > Application. Sur une copie de campagne, créer un Pokémon avec une place libre, ajouter un objet et inspecter une ville via Jump to Map. Revenir au choix 1 pour vérifier que la campagne est intacte.
- **Compatibilité** : une campagne existante peut être reprise. Une nouvelle partie admin permet de relire l'introduction. Les récompenses et l'état des deux enquêtes restent compatibles.
- **Limites** : le jeu conserve actuellement les trois starters de Sinnoh dans l'écran natif. La sélection aléatoire élargie, le second compagnon, les Méga en combat, les nouveaux habitats et la coopération ne sont pas encore activés. Les outils admin portent sur les tables natives de Platine.

Validation technique : 70 tests natifs sous Windows, tests Linux et diagnostic du nouvel exécutable portable réussis. Le diagnostic inclut les tirages et le format de conservation du nouveau départ ; le menu de sélection et le don ne sont pas encore raccordés.

Les vérifications automatisées de Windows et les captures du jeu sont visibles dans l'onglet Actions du dépôt. Une capture du jeu sous Wine ne vaut pas un test audio ou un test sur le bureau Windows du joueur.

Preuves de cette livraison : [70 tests Windows et contrôles Linux](https://github.com/NeptuneOff/Pokemon-Universe/actions/runs/41062831820) ; [captures réelles du prologue et de F10 > Application](https://github.com/NeptuneOff/Pokemon-Universe/actions/runs/41062831832). La création effective d'un Pokémon ou d'un objet et la téléportation restent à essayer sur une carte native ; l'ouverture des menus seule ne valide pas ces actions. Voir [le bilan détaillé](NATIVE-VALIDATION.md).
