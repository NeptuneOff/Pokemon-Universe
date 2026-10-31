# Starters aléatoires dans le port natif

Le raccordement du menu natif sélectionne trois propositions persistantes : Plante, Feu et Eau. Cette première intégration jouable utilise les **12 starters des générations 1 à 4**, dont les données, sprites, cris, capacités et évolutions existent dans le moteur actuel. Le modèle complet conserve les 27 starters des générations 1 à 9 ; les 15 espèces initiales suivantes et leurs lignées restent à intégrer dans les tables natives avant de rejoindre le menu.

| Type | Vivier natif |
|---|---|
| Plante | Bulbizarre, Germignon, Arcko, Tortipouss |
| Feu | Salamèche, Héricendre, Poussifeu, Ouisticram |
| Eau | Carapuce, Kaiminus, Gobou, Tiplouf |

Chaque type est tiré indépendamment : les trois propositions peuvent appartenir à des générations différentes. Le trio Sinnoh reste un résultat possible du tirage, pas la sélection imposée. Le tirage est fixé par l'identité de la nouvelle partie et enregistré ; rouvrir le menu, sauvegarder ou reprendre ne le renouvelle pas.

Le menu original garde ses Poké Balls, sa caméra et ses animations. Les sprites, cris, noms français et Pokémon effectivement remis utilisent l'espèce tirée. Les personnages secondaires prennent les deux propositions restantes ; leurs équipes remplacent aussi les évolutions de leurs anciens starters. Quand une espèce change, elle reçoit son propre ensemble de capacités appris au niveau concerné, plutôt que les capacités explicites d'un autre Pokémon.

La variable native du starter conserve l'espèce effectivement choisie. Les scripts historiques qui comparent uniquement les trois identifiants de Sinnoh reçoivent une correspondance de type ; la remise initiale traduit ce choix vers le vrai Pokémon, seulement pendant cette remise. Les autres cadeaux ne sont pas convertis. Les cinq variables réservées sont `0x4031` et `0x406C` à `0x406F`, vérifiées inutilisées dans la révision moteur épinglée. Le format et la taille des blocs de sauvegarde restent identiques.

Les parties ayant déjà choisi leur starter gardent leur Pokémon et leurs comportements historiques. Pour essayer le tirage, commencer une nouvelle partie dans le profil Admin ou utiliser une partie encore antérieure au premier choix. Une partie principale ne doit pas être effacée pour tester.

Le second compagnon et les Méga restent un raccordement séparé. Ce menu ne prétend pas avoir rendu jouables les 27 starters ni les 48 lignées du second choix.

La préparation vérifie séparément `starter-lock.json` avant de modifier la copie de compilation. Le sous-module amont n'est pas modifié. La publication de cette source ne remplace pas à elle seule le moteur livré : attendre la promotion du candidat compilé dans `distribution/windows`, recensée dans les versions testables.
