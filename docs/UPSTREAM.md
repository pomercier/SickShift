# Intégrer l’amont sans écraser le fork

## Deux environnements distincts

Travaillez dans un clone de développement propre. L’installation active et son dossier de données ne doivent jamais servir de zone de fusion. Le script refuse un checkout comportant des modifications. Le dépôt conserve l’historique public amont, ce qui permet une fusion Git avec ancêtre commun.

```sh
git switch main
git pull --ff-only origin main
bash scripts/integrate_upstream.sh
```

Le script crée une branche `upstream-sync/<révision>`, prépare la fusion et lance les vérifications avant de créer un commit. Il n’envoie rien et ne déploie rien. S’il y a des conflits, ils restent sur cette branche ; résolvez-les ou utilisez `git merge --abort`. En cas d’échec des tests, la fusion reste non commitée pour diagnostic.

## Revue obligatoire

1. Adapter les nouveaux imports et fichiers SickGear aux modules SickShift.
2. Examiner chaque migration SQL, sa version et ses exigences ; tester avec une base synthétique ou une copie locale privée qui ne sera jamais commitée.
3. Exécuter les contrôles de confidentialité, de syntaxe, d’import et les tests. Tester l’application avec un nouveau dossier de données.
4. Vérifier les fonctions propres au fork : tableau de bord, copie, repli des sections, aperçu et renommage réel.
5. Pousser uniquement la branche d’intégration et ouvrir une pull request vers `main`.
6. Fusionner après revue. Avant déploiement, arrêter le service et sauvegarder le dossier de données. En cas de migration SQL, restaurer code **et** base ensemble pour revenir en arrière.

Le workflow hebdomadaire ouvre une issue pour chaque nouvelle révision amont non intégrée. Il ne fusionne rien. Il nécessite GitHub Actions et les issues activés. Les pull requests créées manuellement déclenchent les contrôles normaux.

## Protection du dépôt GitHub

Après publication, configurer une règle sur `main` : pull request obligatoire, contrôle `SickShift release checks` requis, interdiction de force-push et de suppression, résolution des discussions. Ces règles relèvent des paramètres GitHub et ne sont pas activées par la seule présence de ce document. Un propriétaire peut toujours contourner certaines protections selon sa configuration.

Le bouton historique de remplacement du code est neutralisé dans le fork. Les mises à jour de données et des dépendances ne passent pas par ce blocage. Pour les dépendances, un environnement isolé et une sauvegarde restent nécessaires : une mise à jour de paquet peut introduire une incompatibilité.

Le démarrage du produit n’installe pas de hooks Git et ne répare pas automatiquement les sources : ce mécanisme du prototype a été retiré de l’entrée principale pour que chaque modification reste visible en revue.

## Première publication préparée

`scripts/publish_github.sh` exige une session GitHub CLI authentifiée comme `pomercier`. Il crée au besoin un vrai fork GitHub de SickGear sous le nom SickShift, refuse de forcer une branche distante divergente, publie la branche puis configure la protection de `main`. La disponibilité des règles dépend des permissions et de l’offre GitHub du dépôt. Un échec de configuration doit être traité explicitement avant de considérer le dépôt protégé. L’exécution de ce script constitue une publication réelle.
