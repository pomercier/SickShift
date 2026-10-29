<p align="center"><img src="docs/assets/sickshift-logo.png" width="420" alt="SickShift"></p>
<h1 align="center">Votre prochaine soirée commence ici.</h1>
<p align="center"><strong>Le moteur SickGear. Une expérience SickShift.</strong><br>Un fork indépendant pour suivre ses séries dans une interface cinéma, retrouver ses épisodes et lancer un aperçu en un geste.</p>
<p align="center"><a href="#démarrer">Démarrer</a> · <a href="docs/COMPARISON.md">Comparaison avec SickGear</a> · <a href="docs/UPSTREAM.md">Mises à jour protégées</a> · <a href="docs/PRIVACY.md">Confidentialité</a></p>

## Vos séries, au premier plan

**Un tableau de bord cinéma.** Les épisodes à regarder, les épisodes manquants, les séries terminées et les prochaines diffusions dans une vue cohérente. Des sections repliables qui mémorisent vos préférences dans votre navigateur.

**Un aperçu avant de choisir.** Survolez un épisode pour lire un court extrait généré localement avec FFmpeg. Les aperçus sont encodés en H.264 8 bits. Le HDR10 et le HLG sont convertis en SDR ; le Dolby Vision profil 5 utilise libplacebo et nécessite un appareil Vulkan compatible.

**Moins de friction.** Copie des références des épisodes manquants, regroupement par série, présentation harmonisée et bilan de renommage fondé sur le résultat réel plutôt que sur un nom prévu.

**Un socle reconnu.** SickShift conserve le moteur de gestion, de recherche, de métadonnées et les intégrations du projet [SickGear](https://github.com/SickGear/SickGear). Les fonctions héritées conservent leurs propres prérequis et paramètres.

## Démarrer

Python 3.11 à 3.13 est ciblé par la configuration CI. FFmpeg et ffprobe sont requis pour les aperçus ; sans eux, le reste de l’application reste utilisable. Les commandes ci-dessous utilisent un environnement Python isolé.

```sh
git clone https://github.com/pomercier/SickShift.git
cd SickShift
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dashboard.txt
python sickshift.py --nolaunch --datadir ./data
```

Ouvrez l’adresse annoncée dans les journaux et configurez votre propre bibliothèque. **Aucune base de données, bibliothèque, liste de séries, configuration personnelle ou clé de service n’est fournie.**

Pour Windows : activez l’environnement avec `.venv\Scripts\activate` et installez FFmpeg dans le PATH. Pour un service Linux, consultez [le modèle systemd](packaging/sickshift.service.example).

La recherche facultative de logos TMDB utilise votre propre variable d’environnement `SICKSHIFT_TMDB_API_KEY`. Aucun chargement automatique de fichier `.env` n’est supposé.

## Des mises à jour qui se relisent

Les données de séries et les dépendances continuent d’utiliser les mécanismes habituels. Le remplacement direct du code depuis l’application est bloqué : les changements amont passent par une branche d’intégration, des tests et une pull request. Le suivi hebdomadaire signale les nouveaux commits sans modifier le code.

Cela protège contre un écrasement automatique, **sans promettre une fusion sans conflit**. Le renommage des modules et les modifications d’interface exigent parfois une adaptation manuelle. [Procédure complète](docs/UPSTREAM.md).

## Développement et état du projet

```sh
python scripts/check_release.py
python -m compileall -q sickshift sickshift_dashboard
python -m unittest tests.preview_clip_tests -v
```

Le dépôt contient des contrôles de confidentialité et des tests réels de conversion SDR, 10 bits, HDR10 et HLG. La configuration CI multiplateforme de l’amont a été remplacée par des contrôles ciblés Linux/Python ; leur présence ne signifie pas qu’ils ont déjà réussi sur GitHub. La conversion Dolby Vision dépend du matériel et n’est pas couverte par un test graphique universel.

Les captures d’une bibliothèque réelle sont volontairement absentes. Les préférences d’affichage locales ne sont pas synchronisées entre utilisateurs ou appareils.

## Origine et licence

SickShift est un fork indépendant de SickGear, lui-même issu de Sick-Beard. Il ne s’agit pas d’une version officielle de SickGear. Les droits et mentions d’origine sont conservés ; le code est distribué sous [GPL-3.0](COPYING.txt). Voir [la comparaison technique](docs/COMPARISON.md) et [les contributions](CONTRIBUTING.md).
