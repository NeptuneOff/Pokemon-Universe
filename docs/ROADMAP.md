# De la campagne pilote au jeu complet

> Ce document décrit le prototype web archivé. La base actuelle et son ordre de migration sont dans [PLATINUM-BASE.md](PLATINUM-BASE.md).

## Contrat de produit

Le jeu final doit être une aventure PC complète, jouable en duo sur deux machines, traversant les sept premières régions dans un récit progressif. Tous les Pokémon du catalogue actuel et toutes les Méga-Évolutions doivent être obtenables et cohérents visuellement. Les autres mécaniques de transformation de combat demandées à l’exclusion restent absentes.

La version 0.2 vérifie des bases techniques. Elle ne satisfait pas encore le contrat de produit final.

## 1. Solidifier le moteur

- [x] Catalogue de 1 025 espèces et données des Méga-Évolutions.
- [x] Exploration, collisions, interactions et transitions de cartes.
- [x] Capture, équipe de six, refuge, objets et sauvegarde.
- [x] Types, stats, ordre des actions, PP et changements de partenaire.
- [ ] Remplacer les capacités génériques simplifiées par un moteur d’effets fidèle.
- [ ] Talents, statuts, terrains, météo, objets tenus et attaques à plusieurs cibles.
- [ ] Évolutions par objet, échange, affection, lieu et autres conditions exactes.
- [ ] Formes spéciales et apprentissage des capacités réellement dépendant du niveau.
- [ ] Équilibrage complet sans progression accélérée de fin de chapitre.

## 2. Coopération de production

- [x] Identités, inventaires et équipes séparés ; monde commun.
- [x] Rôles, indices complémentaires, rapports croisés et combats communs.
- [x] Décisions conjointes avec trois issues de récompense.
- [x] Persistance serveur et reconnexion du navigateur.
- [x] Échanges de Pokémon de l’équipe, Balls et potions avec double confirmation et transfert transactionnel.
- [ ] Étendre les échanges au refuge, aux autres objets et aux évolutions associées.
- [ ] Capture partagée optionnelle et rencontres scénarisées communes.
- [ ] Sauvegarde résistante aux interruptions brutales et migration de schéma.
- [ ] Arbitrage exhaustif des événements, inventaires et déplacements côté serveur.
- [ ] Invitations Internet, comptes optionnels, récupération des jetons et hébergement durable.
- [ ] Quêtes personnelles longues qui convergent vers des objectifs communs.
- [ ] Plusieurs énigmes réellement distinctes par région, pas seulement des séquences.

## 3. Direction artistique

- [x] Une seule famille de sprites pixel art pour les Pokémon importés.
- [x] Palette commune et rendu sans lissage.
- [ ] Remplacer les décors de test par des tilesets DS originaux et aboutis.
- [ ] Produire les sprites manquants, surtout les nouvelles formes Méga de Z-A.
- [ ] Harmoniser personnages, portraits, interfaces et animations de combat.
- [ ] Intérieurs, météo visible, cycle jour/nuit, effets et cinématiques.
- [ ] Musique et paysages sonores régionaux cohérents.
- [ ] Vérifier les conditions de réutilisation des ressources tierces avant une distribution finale.

## 4. Contenu régional complet

Les 21 cartes pilotes n’ont pas vocation à être agrandies artificiellement pour prétendre constituer sept régions. Elles seront remplacées progressivement par des ensembles cohérents comprenant villes, routes, donjons, intérieurs, raccourcis et retours utiles.

| Région | Arc directeur | Rôle dans le récit commun |
|---|---|---|
| Kanto | Disparition des relevés migratoires | Former le duo et identifier Atlas |
| Johto | Antennes et mémoire des ruines | Comprendre que la résonance ne se commande pas |
| Hoenn | Déviation des courants | Mesurer les conséquences écologiques |
| Sinnoh | Extraction de cristaux | Distinguer amplification et création du lien |
| Unys | Transferts imposés | Mettre le consentement des partenaires au centre du conflit |
| Kalos | Industrialisation de la Méga-Évolution | Maîtriser la puissance sans synchronisation forcée |
| Alola | Balise de convergence | Résoudre le conflit et ouvrir un monde post-histoire |

Les histoires officielles sont des références de thèmes et de géographie, pas sept scénarios collés à la suite. Il reste à écrire les quêtes détaillées, les antagonistes secondaires, les champions, les Ligues et les activités de fin de jeu.

## Définition de « terminé »

Un catalogue de données ou une démo de sept villes ne suffit pas. La livraison finale exige une campagne complète testée depuis deux nouvelles parties, aucune ressource provisoire visible, toutes les espèces obtenables sans menu de test, un équilibrage progressif, une sauvegarde fiable et une direction artistique homogène.
