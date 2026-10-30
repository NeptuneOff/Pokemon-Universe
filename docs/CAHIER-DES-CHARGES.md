# Pokémon Universe : contrat de réalisation

Ce document conserve les demandes de l’utilisateur pour les reprises du développement.

## Produit final demandé

- Jeu PC complet, intégralement français, basé sur du code existant : le port natif de Platine.
- Aspect très proche de Platine : sprites, décors 3D, perspective, palettes, proportions, interfaces et animations cohérents. Le prototype web a été rejeté comme base visuelle.
- Sept régions complètes : Kanto, Johto, Hoenn, Sinnoh, Unys, Kalos et Alola. Un récit adapté et une progression cohérente les relient, au-delà d’un assemblage de cartes.
- Toutes les espèces Pokémon existantes, y compris celles de régions non cartographiées. Vérifier le catalogue à la date d’intégration ; une liste de noms ne vaut pas intégration jouable.
- Toutes les Méga-Évolutions, y compris celles de Légendes Pokémon : Z-A. Pas de capacités Z, Dynamax, Gigamax ni autres mécaniques de transformation concurrentes.
- À chaque nouvelle partie, proposer trois starters tirés au sort : un Plante, un Feu et un Eau, parmi les familles de starters existantes de ces types. Enregistrer les propositions et le choix pour empêcher un nouveau tirage au chargement.
- Chaque joueur choisit ensuite, très tôt, un second compagnon qui n'est pas un starter classique. Sa lignée comporte au moins une évolution et son stade final possède une Méga-Évolution. Le professeur remet le compagnon et la gemme correspondante ensemble, une seule fois par joueur.
- Les Méga-Évolutions structurent l'histoire principale, ses enquêtes et ses conflits à travers les sept régions. Le projet doit ajouter des quêtes, personnages, lieux, situations et conséquences originales ; les cartes et le scénario de Platine sont une base, pas le contenu final.
- Deux joueurs sur deux PC dans une campagne commune. Identités, équipes, objets et décisions distincts ; la coopération modifie le scénario et les situations de jeu.
- Personnalisation initiale et événements personnels issus d’un hasard persistant. Actions différentes et complémentaires selon les rôles. La reconnexion ne relance pas les résultats aléatoires.
- Sauvegarde fiable, reprise de partie, désaccords résolubles, combats communs et échanges sans duplication.
- Lancement sous Windows 64 bits depuis Git : un seul `JOUER.bat` qui prépare, vérifie et lance le jeu, conserve les sauvegardes et écrit des logs exploitables. Aucun ZIP manuel, aucune ROM ni installation de Python au moment de jouer.
- Suivi sur `NeptuneOff/Pokemon-Universe`. Les sources, le lanceur et les fichiers de la base Windows sont inclus dans Git ; les mises à jour se récupèrent avec `git pull --ff-only`. Une Release ou une archive séparée ne doit pas être nécessaire.

## État natif

L’étape actuelle installe le port existant avec les ressources françaises, un prologue et une enquête à Bonaugure prolongée à Littorella. Deux rôles solo conduisent à des interactions différentes, à un rapport persistant et à des récompenses uniques. Le parcours analyste de Bonaugure, sa sauvegarde et sa reprise ont été exécutés dans le moteur natif sous Linux ; les autres parcours ont des limites de validation détaillées dans NATIVE-VALIDATION.md. Le reste de la campagne suit Platine. La coopération, le catalogue étendu et les Méga-Évolutions du prototype JavaScript ne sont pas intégrés au moteur natif.

Le prologue à Sinnoh valide une première scène sur la base d’origine ; il ne verrouille pas l’ordre final des sept régions.

Les règles C du nouveau départ couvrent les 27 starters des neuf générations publiées et trois propositions de compagnon tirées dans 48 lignées éligibles, avec 53 parcours vers une Méga. Les choix, leur conservation, l'ordre des deux sélections et le contrat de remise du Pokémon avec sa gemme sont testés. **Ces règles ne sont pas encore raccordées à l'écran de choix ni aux équipes et au Sac natifs.** Le registre des espèces n'autorise pas à écrire leurs numéros nationaux dans les anciennes tables de Platine. Voir [le nouvel arc](SCENARIO-RESONANCE.md).

## Prochain jalon de gameplay

Une petite zone native doit prouver le duo avant l’extension du monde : deux identités persistantes, deux positions visibles, deux équipes, un objectif nécessitant deux actions différentes, une conséquence partagée et une reconnexion vérifiée. Le scénario envisagé associe l’observation des migrations à l’analyse de balises ; il doit être implémenté dans les scripts et systèmes du moteur, au-delà des dialogues.

Les espèces et Méga-Évolutions supplémentaires doivent fonctionner dans les combats et sauvegardes. Les ressources postérieures à Platine nécessitent une création ou adaptation artistique ; elles n’existent pas toutes dans un style Platine officiel.

## Tests fréquents et contenu supplémentaire

Livrer des étapes testables dans Git, avec un parcours court et les limites de chaque étape. Le lanceur unique donne accès à un profil admin séparé et à une copie explicite de la campagne pour tester sans l'écraser. Voir [TESTER.md](TESTER.md).

Les espèces de toutes les générations doivent être réparties selon l'écologie et la progression dans plusieurs régions. Les Fakemon, fusions et ressources communautaires sont autorisés et souhaités ; conserver la cohérence visuelle de Platine et les crédits. Les créatures ajoutées ont une place narrative et écologique précise. Cela ne réintroduit pas les mécaniques de combat exclues.
