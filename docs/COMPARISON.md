# SickShift face à SickGear

Comparaison préparée le 29 octobre 2026 avec `SickGear/SickGear`, branche `main`, commit `60b9dec46e9ffae97a87cad0905a654acc726167`. Les affirmations portent sur les sources comparées, pas sur toutes les versions futures.

| Domaine | Socle SickGear | Différences SickShift |
|---|---|---|
| Gestion des séries | Suivi, recherche, métadonnées, fournisseurs, intégrations | Moteur conservé, modules renommés `sickshift` |
| Présentation | Interface Slick et ses modes | Habillage cinéma, identité SickShift et nouveau logo transparent |
| Vue d’ensemble | Pages natives de gestion | Paquet FastAPI `sickshift_dashboard` et tableau de bord intégré |
| Aperçus locaux | Aucun composant équivalent dans la base comparée | Popup sur épisodes locaux, cache FFmpeg, sortie 8 bits et conversions HDR |
| Épisodes manquants | Gestion native des statuts | Groupes repliables, copie avec confirmation et typographie harmonisée |
| Sections du tableau de bord | Pas de composant équivalent | Chevrons accessibles, déplié par défaut, préférence navigateur |
| Renommage | Mécanismes natifs de déplacement et mise à jour en base | Bilan avant/après vérifié ; échec du déplacement vidéo bloquant avant les fichiers associés |
| Mise à jour du code | Mise à jour intégrée de l’amont | Intégration sur branche et revue ; remplacement direct bloqué |
| Données privées | Créées par chaque installation | Export propre, exclusions et contrôle des fichiers indexés |

## Méthode et historique

Le dépôt de publication part directement de l’historique **public** de SickGear. Les sources SickShift sont importées dans un nouveau commit ; l’historique de développement privé, les sauvegardes et les bases de l’installation d’origine ne sont pas repris. Les 31 commits du développement local sont ainsi consolidés au lieu d’être publiés sans audit.

La comparaison locale avant renommage recensait 66 fichiers modifiés et environ 7 452 lignes ajoutées sur les commits locaux. Ce chiffre n’inclut pas l’ensemble des modifications non commitées ni le renommage global ; ce n’est pas le nombre final de fichiers du fork. Pour la comparaison exacte de l’export :

```sh
git diff --stat 60b9dec46e9ffae97a87cad0905a654acc726167 HEAD
git diff --find-renames 60b9dec46e9ffae97a87cad0905a654acc726167 HEAD
```

## Limites à connaître

Le renommage global augmente le travail de fusion amont. Un merge Git réussi ne suffit pas : il faut aussi vérifier les nouveaux imports, les noms de modules, les migrations SQL et les parcours utilisateur. Les anciens scripts et intégrations tiers peuvent encore exiger une adaptation. Les URL publiques réelles et les noms de protocoles externes ne doivent pas être renommés arbitrairement.

La page de découverte personnalisée « quoi regarder » reste une évolution future ; le tableau de bord actuel n’est pas présenté comme un moteur de recommandation nouveau.
