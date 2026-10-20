# Coopération asymétrique — archive du prototype web

> Les mécanismes ci-dessous ne sont pas intégrés au moteur natif. Voir [le cahier des charges actuel](CAHIER-DES-CHARGES.md).

## Idée centrale

Deux personnages interprètent le même monde différemment. L’analyste comprend les dispositifs ; l’éclaireur comprend leurs effets sur les Pokémon. Aucun des deux ne détient seul toutes les informations nécessaires à l’enquête.

Le partenaire n’est pas un suiveur : chacun a une équipe, un inventaire, un personnage et une action de combat. La partie partage les accréditations, les preuves et les conséquences des décisions.

## Personnalisation et hasard

Une graine de partie est générée par le serveur. Chaque identité reçoit une graine dérivée de cette graine, de son pseudo, de sa couleur, de son tempérament et de son siège dans la partie. Elle est conservée sur le serveur. Revenir sur une carte ou recharger la partie ne relance pas les événements.

La version pilote choisit parmi quatre découvertes textuelles par région. Les récompenses dépendent du rôle. Ce n’est pas encore un générateur de véritables quêtes divergentes. Le projet final doit ajouter des familles d’événements avec prérequis, résolutions et effets persistants ; les statistiques de combat ne doivent pas être déterminées arbitrairement par la couleur du personnage.

## Boucle commune actuelle

1. Un membre du duo reçoit le mandat régional.
2. Le passage est ouvert après une victoire personnelle contre le garde.
3. Chaque joueur consulte une version différente de l’inscription.
4. L’analyste règle la première borne, l’éclaireur stabilise la deuxième, l’analyste règle la troisième.
5. Les deux joueurs déposent leurs rapports à la console.
6. Ils se déclarent prêts et affrontent ensemble le défi régional.
7. Chaque joueur vote sur la publication ou la restauration.
8. Les deux votes débloquent le chapitre suivant. Accord restauration : Balls et potions ; accord publication : financement ; divergence : compromis et récompense mixte.

## Combats communs

Le serveur conserve les équipes du combat. Une action par joueur et par tour ; doubles envois et numéros de tour périmés sont refusés. L’ordre utilise la priorité puis la vitesse. Deux ennemis au maximum sont actifs, les suivants prennent la relève. Si une équipe est entièrement K.O., le joueur restant peut terminer le combat.

Soutiens une fois par combat : l’éclaireur réduit les dégâts reçus par les deux partenaires pendant le tour ; l’analyste augmente leur prochaine attaque. Chaque joueur peut faire méga-évoluer un partenaire compatible une fois dans le combat.

## Transport et persistance

Serveur HTTP Node.js sans dépendances ; clients navigateur interrogés toutes les 500 ms. Les sauvegardes sont écrites via un fichier temporaire puis renommées. Les réponses ne divulguent pas le jeton du partenaire. Le serveur ne sert pas le dossier `.sessions`.

Le serveur fait autorité sur les étapes de campagne, les votes et les tours des combats communs. Les équipes, inventaires, positions et victoires solo sont encore déclarés par les clients avec une validation de structure. Ce n’est pas un système anti-triche ni un serveur public durci. L’usage actuel vise deux partenaires de confiance en LAN ou via VPN privé.

## À étendre

Des combats ne doivent pas remplacer toutes les interactions coopératives. Prévoir : exploration simultanée de deux lieux, témoignages contradictoires, escorte pendant une réparation, observation discrète et capture consentie, ressources transférables, choix différés dont le partenaire constate les conséquences, et résolution de désaccords sans bloquer définitivement l’histoire.


## Échanges au relais (0.2)

Les deux personnages doivent être connectés, hors combat et dans le même relais. Une offre contient au maximum un Pokémon de l’équipe, 99 Balls et 99 potions, dans la limite du stock. Les dons sont permis ; ni équipe vide ni équipe de plus de six Pokémon ne sont autorisées.

Chaque offre porte un identifiant et une version. Modifier une offre efface les deux confirmations. Une confirmation portant sur une ancienne version est refusée ; le joueur doit relire le récapitulatif. Après les deux confirmations, le serveur prépare les deux inventaires dans une copie de la session, écrit le résultat, puis remplace la session en mémoire. Si l’écriture échoue, aucun inventaire en mémoire n’est transféré et la confirmation peut être réessayée.

Pendant une offre en cours, le serveur ignore les changements d’équipe et d’inventaire des synchronisations ordinaires et refuse les événements de campagne et les préparations de combat. Après le transfert, chaque joueur reçoit un nouveau compteur `gameEpoch`. Une synchronisation portant l’ancien compteur ne peut pas rétablir le Pokémon donné ou les anciens stocks. Le client adopte les données serveur avant d’envoyer le nouveau compteur.

Les offres et confirmations sont sauvegardées avec la session. Une déconnexion ne confirme rien à la place du joueur. Il peut reprendre avec son jeton ; son partenaire peut annuler sans attendre. Une offre expire dix minutes après son ouverture, à la prochaine requête authentifiée. Une transaction déjà terminée ne peut pas être rejouée.

Cela protège contre les conflits entre clients ordinaires et les requêtes périmées. Cela ne rend pas l’ensemble du jeu anti-triche : les équipes solo restent déclarées par les clients. Les évolutions par échange ne sont pas encore résolues.
