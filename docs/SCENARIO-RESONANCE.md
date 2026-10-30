# Les Résonances — direction du nouveau récit

Ce document décrit le contenu original à réaliser. Les scènes jouables actuellement modifiées sont l'introduction de Sorbier et les enquêtes de Bonaugure et Littorella. Le reste de cette campagne n'est pas encore implémenté dans les cartes du moteur.

## Le départ

Le professeur reçoit trois jeunes Pokémon issus de familles différentes à chaque nouvelle partie : un Plante, un Feu et un Eau. Le tirage est fixé pour la partie. Les deux personnages d'une campagne duo reçoivent des propositions différentes pour chaque type ; revenir dans le menu, se reconnecter ou charger ne renouvelle pas les résultats.

Après ce premier choix, le professeur propose un compagnon de résonance. Ce Pokémon commence au premier stade de sa lignée. Sa gemme est un outil de recherche confié au Dresseur, pas une transformation immédiate.

Trois propositions sont tirées parmi **48 lignées éligibles**, soit **53 parcours d'évolution vers une Méga** dans l'instantané actuel. La famille est tirée uniformément, puis sa forme Méga cible : une lignée ayant plusieurs Méga ne gagne pas artificiellement en fréquence. Les six propositions du duo proviennent de familles différentes. Riolu, Wattouat et Galekid restent des possibilités parmi les autres, sans constituer un trio fixe.

Sont retenus les premiers stades ayant au moins une évolution réelle vers un stade terminal capable de méga-évoluer. Les lignées de starters classiques, Pikachu et Évoli sont exclues de ce second choix. Les parcours à sexe imposé fournissent cette contrainte au moteur hôte : un Tarsal destiné à Gallame est mâle, un Stalgamin destiné à Momartik est femelle. Une forme sans lignée évolutive attestée n'est pas ajoutée artificiellement.

Le joueur choisit librement. Le compagnon et sa gemme sont remis ensemble. Un échec d'inventaire doit permettre de réessayer sans changer le choix et sans doubler le cadeau. Le compagnon ne peut pas méga-évoluer avant d'atteindre sa forme finale ; les conditions habituelles de Méga-Évolution restent applicables. Les autres Méga et leurs gemmes demeurent des découvertes de la campagne.

Les affinités donnent des occasions différentes d'enquêter, sans déterminer arbitrairement les statistiques à partir de l'apparence du personnage. Les événements personnels combinent l'identité initiale, la graine conservée et les décisions prises. Chaque joueur conserve son équipe, ses objets et ses propres choix.

## Le mystère central

Des Méga-Gemmes jusque-là inertes émettent des pulsations synchronisées. Des Pokémon déplacent leurs habitats avant même l'apparition de signes visibles de danger. Le réseau Atlas, présenté comme un projet de protection des déplacements Pokémon, utilise des balises pour mesurer et amplifier ces signaux. Ses résultats sont utiles, mais ses méthodes finissent par imposer un rythme aux liens entre Dresseurs et Pokémon.

L'enquête ne doit pas conclure d'emblée que toute Méga-Évolution est dangereuse. Le conflit oppose une résonance libre, construite avec le compagnon, à une synchronisation forcée dont les conséquences traversent les frontières. Les deux personnages découvrent des parties différentes du problème et doivent confronter leurs preuves.

## Les sept arcs à écrire et intégrer

L'ordre ci-dessous donne une continuité à un départ à Sinnoh. Il reste à traduire ces arcs en cartes, scripts, combats, dialogues, récompenses et conséquences testés.

| Région | Arc original | Actions distinctes du duo | Conséquence persistante |
|---|---|---|---|
| Sinnoh | La première pulsation : migrations et gemmes du lac | Mesurer les signaux ; observer les comportements | Une première hypothèse commune fondée sur deux preuves |
| Johto | La mémoire des pierres : des traces anciennes contredisent Atlas | Interpréter les inscriptions ; vérifier leur effet dans les ruines | Choisir quelles traces protéger et rendre publiques |
| Kanto | Les contours du silence : des données de calibration ont disparu | Suivre les relevés techniques ; retrouver les témoins des essais | Dévoiler une falsification ou conserver un accès utile à l'enquête |
| Hoenn | Les courants croisés : les poussières de gemmes suivent les voies maritimes | Étudier les courants ; guider une opération sur le littoral | Restaurer un habitat et modifier les liaisons accessibles |
| Unys | Les lignes de fuite : des convois déplacent des Pokémon contre leur gré | Enquêter sur les autorisations ; intervenir auprès des convois | Les sauvetages et alliances changent la suite des missions |
| Kalos | L'accord : comprendre la Méga-Évolution sans imposer la synchronie | Passer des épreuves personnelles ; partager des méthodes complémentaires | Stabiliser une méthode que chaque Dresseur maîtrise individuellement |
| Alola | Les deux voix : le réseau menace de maintenir une résonance permanente | Agir sur deux relais différents ; assumer un choix commun | Déterminer le devenir du réseau et les activités après l'histoire |

Les histoires officielles fournissent la géographie, des personnages et des enjeux locaux. Elles ne doivent pas être rejouées sept fois avec un changement de décor. Les migrations, les gemmes, les alliances et les décisions du duo lient les régions. Les retours dans une région doivent faire apparaître les conséquences des actes précédents.

La progression conserve l'équipe et évite un retour artificiel au niveau 5 à chaque région. L'équilibrage, les qualifications et les défis de chaque territoire doivent être écrits ensemble. Aucune Primo-Résurgence, capacité Z, Dynamax ou Gigamax n'est ajoutée pour résoudre le scénario.

## Un monde vivant et du contenu de fans

La génération d'origine ne décide pas des régions où une espèce vit. La répartition prévue combine habitat, climat, heure, saison et étape narrative. Les espèces communes peuvent habiter plusieurs régions avec des densités différentes ; les espèces rares gardent des indices lisibles et des conditions cohérentes. Les migrations de l'enquête changent certaines tables après les choix du duo. Une nouvelle région apporte de nouvelles situations, sans réserver mécaniquement toutes ses espèces à sa carte d'origine.

Les Fakemon et les fusions font désormais partie du périmètre demandé. Ils doivent avoir une place précise : populations locales adaptées, lignées stables, sanctuaires ou conséquences documentées des essais Atlas. Une fusion est une créature persistante de l'univers, pas une transformation de combat supplémentaire. On ne remplace pas au hasard les espèces connues ni les textures de Platine par une collection d'images hétérogènes. Chaque ajout demande données, évolution, nom français, visuels cohérents et crédits traçables. Les premiers choix de compagnons restent fondés sur les lignées officielles vérifiées ; les lignées de fans devront remplir le même contrat avant de rejoindre le tirage.

## État du nouveau départ

`content/native/start-options.fr.json` et `native/universe/journey.c` décrivent le tirage et l’ensemble du vivier des compagnons. Le format de conservation est versionné et contrôlé contre les altérations. Les règles sont testées en C ; elles ne créent pas encore les Pokémon dans la partie native et ne constituent pas une coopération réseau.

Le raccordement doit adapter le menu de sélection, les identifiants des espèces, les données de combat et d'évolution, les sprites, les noms, les choix cohérents des personnages secondaires, puis la remise effective du compagnon et de sa gemme. Il doit conserver les choix après sauvegarde/reprise. Les espèces annoncées de Vents et Vagues sont suivies séparément : leurs statistiques et lignées inconnues ne sont pas inventées pour remplir le registre.
