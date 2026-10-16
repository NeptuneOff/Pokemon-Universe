# Vérification de la version 0.2

## Tests automatisés

Commande : `npm test`. Résultat : **12 tests réussis**.

- Catalogue de 1 025 espèces, équipes valides, dégâts et Méga-Évolution.
- Accessibilité des interactions sur les 21 cartes et références de campagne.
- Sept chapitres coopératifs parcourus via deux clients HTTP : rapports, combat commun et votes.
- Échange de Pokémon et d’objets : conservation des caractéristiques, mise à jour du Pokédex.
- Refus des anciennes confirmations et annulation des consentements lorsqu’une offre change.
- Inventaires réservés, anciennes synchronisations ignorées après transfert.
- Annulation, expiration, quantités invalides, équipe vide et septième membre refusés.
- Confirmations concurrentes sans double transfert.
- Échec d’écriture simulé : aucun inventaire transféré ; confirmation réessayable.
- Rechargement de la sauvegarde serveur et reconnexion avec les jetons existants.

Les équipes du test des sept chapitres sont volontairement très puissantes : ce test vérifie les étapes de campagne, pas l’équilibrage d’une partie normale.

## Navigateur

Commande optionnelle : `node tests/browser-trade.cjs` après installation de Playwright et Chromium.

Vérifié dans deux contextes Chromium indépendants : création et connexion du duo, choix de deux starters, propositions via l’interface, double confirmation, rechargement pendant l’échange, transfert puis rechargement et reconnexion. Aucun événement d’erreur JavaScript. Les commandes des boutons sont déclenchées dans le DOM ; il ne s’agit pas d’une validation manuelle sur deux PC.

L’interface d’échange a également été inspectée à 1440 × 1000.

## Vérifications restantes

- Deux PC Windows sur un vrai réseau LAN ou VPN, avec pare-feu et pertes de connexion.
- Parcours manuel complet et équilibrage de la campagne.
- Toutes les tailles de fenêtre et navigateurs annoncés.
- Évolutions par échange, autres objets et échanges directs depuis le refuge.
- Interruptions électriques ou pannes matérielles de stockage.

Le jeu reste un prototype ; ces contrôles ne valent pas validation du produit final.
