# Pokémon Universe — Méridien

**Prototype PC jouable, version 0.2. Ce dépôt ne contient pas encore le jeu complet demandé.**

Objectif : une aventure continue dans les sept premières régions, tous les Pokémon, toutes les Méga-Évolutions recensées (y compris Z-A), une direction artistique pixel art commune et une véritable campagne en coopération à deux joueurs. Pas de capacités Z, Dynamax, Gigamax ni Téracristallisation.

La campagne pilote **Méridien** sert à éprouver les systèmes : 21 petites cartes originales et sept chapitres courts. Ce ne sont pas des reproductions intégrales de Kanto, Johto, Hoenn, Sinnoh, Unys, Kalos et Alola.

## Lancer le jeu

### Solo

Extraire ou cloner le dépôt, puis ouvrir `index.html` dans Chrome, Edge ou Firefox. Les ressources sont locales. Utiliser **Menu → Exporter la sauvegarde** pour conserver une copie transportable.

### Duo, chacun sur son PC

1. Sur le PC hôte, installer Node.js 22 ou plus récent.
2. Lancer `DEMARRER-PROTOTYPE-WEB-ARCHIVE.bat`, ou exécuter `node server.cjs` dans ce dossier.
3. Ouvrir `http://localhost:8787` sur le PC hôte.
4. Sur le deuxième PC, ouvrir `http://ADRESSE_IP_DU_PC_HOTE:8787`. L’adresse s’affiche dans le terminal du serveur. Les deux PC doivent être sur le même réseau local ou sur un VPN privé commun.
5. Le premier joueur choisit **Jouer en duo → Créer la partie**, personnalise son personnage et choisit son partenaire.
6. Le second choisit **Jouer en duo → Rejoindre** avec le code de six caractères indiqué dans l’interface du premier joueur.
7. Garder le serveur ouvert pendant la partie. Si Windows demande l’accès réseau, l’autoriser sur le réseau privé utilisé.

Le second joueur n’a pas besoin d’installer Node.js. Il reçoit le client et les ressources depuis le PC hôte. Pas de service central, de matchmaking ni de traversée NAT automatique dans cette version. Pas d’exécutable Windows natif : le client tourne dans le navigateur du PC.

**Reconnexion :** ouvrir la même adresse dans le même navigateur, puis **Jouer en duo → Reprendre ma connexion**. Les jetons de connexion sont propres à chaque navigateur. Le serveur conserve les parties dans `.sessions/`, exclu de Git. Copier ce dossier sauvegarde le monde commun ; l’export solo ne remplace pas cette sauvegarde coop.

## Échanger avec son partenaire

Les deux joueurs doivent être connectés au même relais, hors combat. Ouvrir **Menu → Échanger avec mon partenaire**.

1. Choisir un Pokémon de son équipe, des Balls et/ou des potions, puis **Mettre à jour mon offre**. Un don sans contrepartie est possible.
2. Vérifier les deux offres affichées. Chacun choisit **Confirmer cet échange**. Toute modification annule les confirmations.
3. À la seconde confirmation, le serveur transfère les deux offres ensemble et sauvegarde les deux équipes. Le Pokédex du destinataire enregistre le Pokémon reçu.

Les équipes restent entre un et six Pokémon. Pour proposer un Pokémon du refuge, l’ajouter d’abord à l’équipe. Pendant l’échange, les équipes et les sacs sont réservés : pas de combat, déplacement ou gestion d’équipe. Chacun peut annuler ; après dix minutes, l’offre expire sans transfert. Une reconnexion reprend l’offre en cours ou récupère le résultat sauvegardé.

Cette version échange uniquement les Pokémon de l’équipe, les Balls et les potions. **Les évolutions déclenchées par échange ne sont pas encore implémentées.** Les niveaux, capacités, PP, PV et gemmes équipées sont conservés.

## Commandes

| Action | Commande |
|---|---|
| Marcher | Flèches, ZQSD ou WASD |
| Courir | Majuscule |
| Parler / examiner / franchir une sortie | E ou Entrée |
| Menu | Échap |
| Combat / équipe / objets | Boutons à la souris |

Au départ, parler à Lise devant le laboratoire au nord. Le centre Pokémon soigne gratuitement. La sortie de la route est à l’est ; le quai est au sud-est. Interagir avec les sorties avec **E**.

## Coopération actuellement implémentée

- Deux identités, équipes, inventaires et positions distincts dans une partie partagée.
- **Analyste :** première et dernière bornes des énigmes ; soutien tactique commun en combat.
- **Éclaireur :** borne intermédiaire ; protection commune et bonus de capture en exploration.
- Indices complémentaires : l’inscription révèle une partie différente de la séquence à chaque rôle.
- La console exige les deux rapports avant de débloquer le défi régional.
- Combats majeurs à deux contre deux adversaires actifs, avec relève. Chaque joueur choisit son action ; le serveur résout le tour quand les deux décisions sont arrivées.
- Nom, couleur de veste et tempérament contribuent à une graine personnelle enregistrée. Les textes de découvertes secondaires varient selon cette graine et la région.
- Deux votes de fin de chapitre : publication des preuves, restauration des habitats, ou compromis si les choix divergent. Ils changent le bilan et les ressources accordées pour la suite.
- Échanges et dons de Pokémon, Balls et potions avec double confirmation et transfert atomique.
- Sauvegarde commune sur le PC hôte et reprise avec les mêmes jetons.

Les combats sauvages et les gardes de route restent personnels dans cette version. Les quêtes personnelles sont encore des variantes courtes, pas des embranchements complets de plusieurs heures.

## Données et limites

| Domaine | État de la version 0.2 |
|---|---|
| Pokédex | 1 025 espèces de base importées ; formes régionales et variantes Méga supplémentaires |
| Disponibilité | Espèces accessibles via les bureaux des habitats des sept régions ; légendaires après la campagne |
| Campagne | Sept chapitres condensés, trois petites cartes par chapitre |
| Combat | Types, STAB, stats, vitesse, précision, PP, dégâts, capture, niveaux et changements de partenaire |
| Capacités | Sous-ensemble offensif ; effets secondaires, talents, conditions spéciales et compétitivité non fidèles aux jeux officiels |
| Évolution | Niveaux simples ; conditions complexes remplacées provisoirement par une évolution manuelle à partir du niveau 30 |
| Méga-Évolution | Variantes et statistiques importées ; une par joueur par combat, gemme compatible et bracelet requis ; pas encore tous les comportements particuliers |
| Art | Sprites pixel art communautaires DS/BW ; décors programmatiques provisoires ; liste explicite des sprites manquants |
| Audio | Petits effets de synthèse ; pas encore de bande originale |
| Réseau | LAN / VPN privé, synchronisation par requêtes HTTP ; pas encore une infrastructure publique durcie |

**Les données ne sont pas équivalentes à une intégration exhaustive des mécaniques.** La présence de toutes les espèces ne signifie pas que leurs talents, capacités et formes particulières fonctionnent tous comme dans les jeux officiels.

Les Méga-formes sans illustration compatible utilisent temporairement le sprite de base avec une aura et la mention « VISUEL PROVISOIRE ». Certaines espèces récentes n’ont pas encore de sprite et affichent un marqueur. Les 56 entrées concernées sont listées dans `docs/missing-sprites.json`. Cela doit être corrigé avant une livraison respectant entièrement la direction artistique demandée.

## Développement

```bash
npm test
npm start
```

Aucune dépendance npm n’est nécessaire pour jouer, héberger ou exécuter les tests unitaires et d’intégration HTTP. Le test navigateur optionnel vérifie deux clients indépendants, un échange et les reconnexions avant et après transfert :

```bash
npm install --no-save playwright
npx playwright install chromium
node tests/browser-trade.cjs
```

Il utilise un dossier temporaire et ne modifie pas les sauvegardes de jeu.

- `src/core.js` : règles de combat et validation des sauvegardes.
- `src/world.js` : cartes, collisions et interactions.
- `src/game.js` : client, rendu, exploration et combats solo.
- `src/coop-client.inc.js` : adaptateur coop, inséré dans `game.js` par `tools/assemble_coop.py`.
- `server.cjs` : parties communes, API, persistance et combats coop.
- `src/trade.cjs` : validation des offres et transaction d’échange.
- `data/campaign.js` : scénario et progression.
- `data/game-data.js` : catalogue généré, autonome hors ligne.
- `tools/` : import et préparation des ressources. Les images sont regroupées dans `assets/pokemon-*.js` ; `python tools/unpack_sprites.py` restitue les PNG éditables et `python tools/pack_sprites.py` les regroupe à nouveau.
- `tests/` : tests de données, collisions, règles et campagne coop.

Voir [la feuille de route](docs/ROADMAP.md), [la conception du duo](docs/COOP-DESIGN.md) et [les crédits](CREDITS.md).
