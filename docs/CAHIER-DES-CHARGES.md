# Pokémon Universe : contrat de réalisation

Ce document conserve les demandes de l’utilisateur pour les reprises du développement.

## Produit final demandé

- Jeu PC complet, intégralement français, basé sur du code existant : le port natif de Platine.
- Aspect très proche de Platine : sprites, décors 3D, perspective, palettes, proportions, interfaces et animations cohérents. Le prototype web a été rejeté comme base visuelle.
- Sept régions complètes : Kanto, Johto, Hoenn, Sinnoh, Unys, Kalos et Alola. Un récit adapté et une progression cohérente les relient, au-delà d’un assemblage de cartes.
- Toutes les espèces Pokémon existantes, y compris celles de régions non cartographiées. Vérifier le catalogue à la date d’intégration ; une liste de noms ne vaut pas intégration jouable.
- Toutes les Méga-Évolutions, y compris celles de Légendes Pokémon : Z-A. Pas de capacités Z, Dynamax, Gigamax ni autres mécaniques de transformation concurrentes.
- Deux joueurs sur deux PC dans une campagne commune. Identités, équipes, objets et décisions distincts ; la coopération modifie le scénario et les situations de jeu.
- Personnalisation initiale et événements personnels issus d’un hasard persistant. Actions différentes et complémentaires selon les rôles. La reconnexion ne relance pas les résultats aléatoires.
- Sauvegarde fiable, reprise de partie, désaccords résolubles, combats communs et échanges sans duplication.
- Lancement sous Windows 64 bits depuis Git : un seul `JOUER.bat` qui prépare, vérifie et lance le jeu, conserve les sauvegardes et écrit des logs exploitables. Aucun ZIP manuel, aucune ROM ni installation de Python au moment de jouer.
- Suivi sur `NeptuneOff/Pokemon-Universe`. Les sources, le lanceur et les fichiers de la base Windows sont inclus dans Git ; les mises à jour se récupèrent avec `git pull --ff-only`. Une Release ou une archive séparée ne doit pas être nécessaire.

## État natif

L’étape actuelle installe le port existant avec les ressources françaises, un prologue et une enquête à Bonaugure prolongée à Littorella. Deux rôles solo conduisent à des interactions différentes, à un rapport persistant et à des récompenses uniques. Le parcours analyste de Bonaugure, sa sauvegarde et sa reprise ont été exécutés dans le moteur natif sous Linux ; les autres parcours ont des limites de validation détaillées dans NATIVE-VALIDATION.md. Le reste de la campagne suit Platine. La coopération, le catalogue étendu et les Méga-Évolutions du prototype JavaScript ne sont pas intégrés au moteur natif.

Le prologue à Sinnoh valide une première scène sur la base d’origine ; il ne verrouille pas l’ordre final des sept régions.

## Prochain jalon de gameplay

Une petite zone native doit prouver le duo avant l’extension du monde : deux identités persistantes, deux positions visibles, deux équipes, un objectif nécessitant deux actions différentes, une conséquence partagée et une reconnexion vérifiée. Le scénario envisagé associe l’observation des migrations à l’analyse de balises ; il doit être implémenté dans les scripts et systèmes du moteur, au-delà des dialogues.

Les espèces et Méga-Évolutions supplémentaires doivent fonctionner dans les combats et sauvegardes. Les ressources postérieures à Platine nécessitent une création ou adaptation artistique ; elles n’existent pas toutes dans un style Platine officiel.
