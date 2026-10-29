# Composant C Universe

Registre d’espèces et règles d’éligibilité Méga. Ce module n’est pas encore lié au port PC distribué. Voir [l’état précis et le raccordement restant](../../docs/NATIVE-EXPANSION.md).

`include/universe.h` expose le registre et l’état temporaire de sélection. Les identifiants des espèces, capacités, talents et pierres sont des chaînes normalisées stables ; les pointeurs internes sont valables pendant l’exécution uniquement et ne doivent jamais être écrits dans une sauvegarde ou un paquet réseau.

Le futur adaptateur de combat doit initialiser les deux participants, obtenir l’action confirmée, appeler `univ_mega_try` puis appliquer les effets du changement de forme au moteur. `univ_mega_end` restaure la forme d’origine mais ne réinitialise pas le droit à la Méga pour ce combat. Les emplacements actuels représentent les deux participants du composant, pas une implémentation des échanges réseau ou de tous les camps du moteur.

Il ne faut pas appeler `univ_battle_init` entre deux tours, ni initialiser un Pokémon directement en forme Méga. Les champs des structures sont destinés à l’adaptateur natif ; ils ne doivent pas être alimentés directement depuis un client réseau non validé.

La table générée se reconstruit depuis les instantanés versionnés avec `python tools/native/rebuild_expansion.py --write`. Le composant peut être compilé en C11 sans dépendance externe. Les tests du dépôt fournissent le programme de validation ; aucune compilation n’est demandée au joueur.
