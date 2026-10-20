# Validation de la base native française

## Contrôles réalisés les 19 et 20 octobre 2026

- ROM USA CPUE Rev 1 et France CPUF contrôlées par SHA-1 ; paquets Linux et Windows v0.1.12 contrôlés par SHA-256.
- Installation réelle sous Linux : 340 fichiers nommés, trois archives de textes françaises et 29 correspondances d’archives graphiques vérifiées.
- Les fichiers installés sont recensés avec leur SHA-256 dans `universe-install.json` (local uniquement).
- Sur les 724 banques de `pl_msg.narc`, seule la banque 389 est modifiée ; seul son message 0 change. Les autres messages chiffrés restent identiques. L’original français est conservé.
- Dix tests sans ROM : lecture NitroFS, limites/cycles, structure NARC, conservation des messages et commandes inconnues, chiffrement connu, caractères français, correspondances graphiques, extraction ZIP, refus d’écraser une sauvegarde et nettoyage après téléchargement invalide.
- Exécution native sous Linux avec rendu logiciel : démarrage, écran titre « Version Platine », introduction Universe, dialogues Sorbier en français, clavier, interaction avec l’écran tactile et sélection du personnage observés le 19 octobre. AppImage testée sans FUSE.

Les captures temporaires du 19 octobre ont disparu lors du nettoyage de l’environnement avant publication. Elles ne sont pas remplacées par des illustrations simulées. La source des outils a été restaurée depuis le travail conservé dans la conversation ; les tests sont relancés avant publication.

## Limites de cette validation

L’arrivée dans le monde, un combat et la sauvegarde/reprise n’étaient pas encore validés à ce point de reprise. La campagne entière et tous les écrans localisés ne sont pas testés. Aucun essai graphique Windows n’a été effectué. Le son n’a pas été validé (pilote audio factice dans l’environnement de test).

Aucune campagne coopérative, nouvelle région, espèce supplémentaire ni Méga-Évolution n’est livrée par cette étape.

## Reproduire les tests sans ROM

```bash
python -m unittest discover -s tests/native -v
```

## Vérification manuelle à poursuivre

Installer les ressources personnelles, créer une partie, atteindre Bonaugure, choisir un Pokémon, terminer un combat, sauvegarder, fermer puis reprendre. Ensuite valider les écrans du sac, de l’équipe, du Pokédex et les boutons français sur Windows et Linux. Conserver les captures réelles et résultats dans Git à chaque étape.
