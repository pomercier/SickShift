# Publication sans données personnelles

L’export contient les sources, les ressources statiques du produit, les tests et leurs fixtures publiques. Il exclut les bases SQLite, configurations d’installation, caches de médias, affiches de bibliothèque, journaux, sauvegardes, environnements Python et fichiers propres à une machine.

La clé TMDB ajoutée durant le développement n’est pas incluse dans l’export. Les URL de miroir contenant des identifiants sont retirées des sources de publication au profit de PyPI. Si un identifiant précédemment utilisé est personnel, son propriétaire doit le révoquer : retirer une chaîne d’un fichier ne révoque pas une clé.

Avant tout commit ou envoi :

```sh
git add <fichiers-explicitement-voulus>
python scripts/check_release.py
git diff --cached --stat
```

Le contrôle examine les fichiers indexés : extensions de données privées, chemins de machine, certaines familles de jetons et clés intégrées. Il ne remplace pas une revue humaine, ne scanne pas le contenu binaire des images et ne prouve pas l’absence de tout secret imaginable. Ne jamais ajouter de capture d’une bibliothèque personnelle au produit.

L’historique conservé est celui du dépôt public amont ; aucun commit de l’historique privé de développement n’est importé.
