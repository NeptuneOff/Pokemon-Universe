# Ressources communautaires et direction artistique

Le périmètre inclut désormais les Fakemon et les fusions. L'objectif reste un jeu français avec les décors, l'échelle et la lisibilité de Platine. Une ressource trouvée n'est pas automatiquement une espèce jouable.

## Sources examinées

| Source primaire | Utilité | Conditions et état |
|---|---|---|
| [Infinite Fusion Hoenn](https://github.com/infinitefusion/infinitefusion-hoenn-public) et [scripts Infinite Fusion](https://github.com/infinitefusion/scripts) | Organisation des sprites personnalisés, crédits par sprite, inspiration pour les créatures fusionnées | README et chargeurs examinés. Aucun de ses sprites n'est importé ; suivre les crédits et conditions propres aux ressources sélectionnées. Son runtime RPG Maker n'est pas le moteur Universe. |
| [PokemonAssets, IcyEthics](https://github.com/icyethics/PokemonAssets/tree/7dbfbfd2cfa89cb65061823fb30f1bf628fcd283) | Fakemon avec vues avant/arrière, shiny, icône et empreinte | Autorise les projets non commerciaux et l'adaptation, à condition que les projets dérivés restent réutilisables et adaptables. Crédit IcyEthics conservé. CANIGHT est retenu comme premier lot source à évaluer. |
| [Smogon sprites](https://github.com/smogon/sprites) / [projet de sprites X/Y](https://www.smogon.com/forums/threads/x-y-sprite-project.3486712/) | Sprites des espèces et Méga postérieures à Platine | Le dépôt ne donne pas un accord uniforme pour tous les fichiers. Vérifier le projet et l'artiste de chaque image ; ne pas étendre une autorisation de projet à tout le dépôt. |

Les fichiers sélectionnés ont leur révision, chemin, empreinte, auteur et texte des conditions dans `content/native/community/`. Les originaux restent réutilisables et adaptables selon les conditions de leur auteur. Ne pas attribuer ces dessins à Universe.

## Passage au jeu natif

Conserver un identifiant de contenu tel que `fan:artiste:espece`, distinct des numéros du Pokédex officiel. Avant activation : définir son nom français, sa place écologique et narrative, les statistiques, capacités et évolutions ; vérifier les vues, l'animation, la transparence et les palettes ; intégrer et tester les archives natives en combat, dans l'équipe et le PC. Les scènes et crédits doivent expliquer la présence de la créature sans casser la progression.

Une image de 96 pixels ne doit pas être réduite automatiquement pour entrer dans une case de Platine : cadrage, lisibilité et animation se contrôlent individuellement. Les variantes shiny utilisent leurs palettes propres. Un sprite sans vue arrière ou sans données reste un candidat, pas un remplacement silencieux d'une espèce officielle.

Le premier lot CANIGHT ne modifie pas encore la distribution jouable. Son manifeste rapporte les dimensions et couleurs des originaux. La vue arrière exige un contrôle d’échelle ; l’icône source comporte un fond sombre et 51 couleurs ; l’empreinte est vide. Ces défauts sont signalés avant toute activation, et les originaux sont conservés pour l’adaptation.
