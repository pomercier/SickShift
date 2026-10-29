/**
 * Automatic internationalization engine for SickShift and its Dashboard.
 * Detects the host default system language (e.g. French) and translates the UI in real time.
 */
(function() {
    'use strict';

    // System language detection
    const rawLang = (window.SG_SYS_LANG || navigator.language || navigator.userLanguage || 'en');
    const systemLang = rawLang.split(/[-_.]/)[0].toLowerCase();

    // If language is not French, retain original English strings
    if (systemLang !== 'fr') {
        return;
    }

    const DICT = {
        // Main navigation
        "Shows": "Séries",
        "Show List": "Liste des séries",
        "Daily Schedule": "Programme quotidien",
        "Add Shows": "Ajouter une série",
        "Add Existing Shows": "Ajouter des séries existantes",
        "Add New Show": "Ajouter une nouvelle série",
        "Trending Shows": "Séries tendances",
        "Popular Shows": "Séries populaires",
        "Schedule": "Programme",
        "History": "Historique",
        "Manage": "Gestion",
        "Episode Overview": "Aperçu des épisodes",
        "Mass Update": "Mise à jour en masse",
        "Backlog Overview": "Aperçu des retards",
        "Bulk Change": "Modification en masse",
        "Search Tasks": "Tâches de recherche",
        "Show Tasks": "Tâches des séries",
        "Manage Searches": "Gestion des recherches",
        "Failed Downloads": "Téléchargements échoués",
        "Manage Subtitle Missed": "Sous-titres manquants",
        "Subtitles Missed": "Sous-titres manquants",
        "Manage Torrents": "Gestion des torrents",
        "Update Emby": "Mettre à jour Emby",
        "Update Kodi": "Mettre à jour Kodi",
        "Update PLEX": "Mettre à jour PLEX",
        "Config": "Configuration",
        "System": "Système",
        "Settings...": "Paramètres...",
        "General": "Général",
        "Media Providers": "Fournisseurs de médias",
        "Light or Dark": "Clair ou Sombre",
        "Backup/Restore": "Sauvegarde/Restauration",
        "Search Settings": "Paramètres de recherche",
        "Search Providers": "Fournisseurs de recherche",
        "Subtitles": "Sous-titres",
        "Post Processing": "Post-traitement",
        "Notifications": "Notifications",
        "Anime": "Animé",
        "Help & Info": "Aide & Infos",
        "Wiki": "Wiki",
        "IRC Chat": "Chat IRC",
        "Donate": "Faire un don",
        "About": "À propos",
        "Check for Updates": "Vérifier les mises à jour",
        "View Changes": "Voir les modifications",
        "View Errors": "Voir les erreurs",
        "View Log File": "Voir le journal (logs)",
        "Import": "Importer",
        "existing shows": "séries existantes",
        "Logout": "Déconnexion",
        "Restart": "Redémarrer",
        "Shutdown": "Éteindre",
        "Process Media": "Traiter les médias",
        "Media Process": "Traitement des médias",
        "Manual Post-Processing": "Post-traitement manuel",
        "Dashboard": "Dashboard",
        "Dashboard (À venir / Manquants)": "Dashboard (À venir / Manquants)",
        "Dashboard Mini": "Dashboard Mini",
        "Add show...": "Ajouter une série...",
        "Added last...": "Dernières ajoutées...",
        "History new...": "Nouvelles de l'historique...",
        "find show at TV info source": "Trouver la série à la source d'infos TV",
        "TVDb Cards": "Cartes TVDb",
        "TVmaze Cards": "Cartes TVmaze",
        "TMDB Cards": "Cartes TMDB",
        "Trakt Cards": "Cartes Trakt",
        "IMDb Cards": "Cartes IMDb",
        "Metacritic Cards": "Cartes Metacritic",
        "TV Calendar Cards": "Cartes Calendrier TV",
        "Next Episode Cards": "Cartes Prochains épisodes",
        "Anime Cards": "Cartes Animés",
        "browse anime to add": "Parcourir les animés à ajouter",
        "to use, first enable AniDB here": "Pour utiliser, activez d'abord AniDB ici",
        "This will list added shows": "Ceci listera les séries ajoutées",
        "This will list latest history": "Ceci listera l'historique récent",
        "upcoming...": "à venir...",
        "new shows...": "nouvelles séries...",
        "new popular...": "nouvelles populaires...",
        "trends, tailored suggestions...": "tendances, suggestions...",
        "popular decades, watchlists...": "décennies populaires, listes...",
        "popular decades, watchlists......": "décennies populaires, listes...",
        "new shows, coming soon, or by rating...": "nouvelles séries, à venir ou par note...",

        // Sorting and layout controls
        "Sort By:": "Trier par :",
        "Sort Order:": "Ordre de tri :",
        "Layout:": "Affichage :",
        "Name": "Nom",
        "Next Episode": "Prochain épisode",
        "Last Episode": "Dernier épisode",
        "Network": "Réseau",
        "Progress": "Progression",
        "Quality": "Qualité",
        "Asc": "Croissant",
        "Desc": "Décroissant",
        "Poster": "Affiches",
        "Small Poster": "Petites affiches",
        "Banner": "Bannières",
        "Simple": "Simple",
        "Reset Filter": "Réinitialiser le filtre",
        "Reset": "Réinitialiser",

        // Show and episode statuses
        "Continuing": "En cours",
        "Ended": "Terminée",
        "Paused": "En pause",
        "Loading...": "Chargement...",
        "No Network": "Aucun réseau",
        "Custom": "Personnalisé",
        "no data": "aucune donnée",
        "Downloaded": "Téléchargé",
        "Downloaded:": "Téléchargés :",
        "Snatched": "Récupéré",
        "Snatched:": "Récupérés :",
        "Archived": "Archivé",
        "Archived:": "Archivés :",
        "Ignored": "Ignoré",
        "Ignored:": "Ignorés :",
        "Skipped": "Passé",
        "Skipped:": "Ignorés :",
        "Wanted": "Recherché",
        "Wanted:": "Recherchés :",
        "Upgradable": "Améliorable",
        "Upgradable:": "Améliorables :",
        "Unaired": "Non diffusé",
        "Failed": "Échoué",
        "Failed:": "Échoués :",
        "Subtitled": "Sous-titré",
        "Unknown": "Inconnu",
        "unknown": "inconnu",
        "never": "jamais",
        "TBA": "À venir",
        "Total": "Total",

        // View show details page
        "Season": "Saison",
        "Seasons": "Saisons",
        "All Seasons": "Toutes les saisons",
        "Jump to season": "Aller à la saison",
        "Episode": "Épisode",
        "Episodes": "Épisodes",
        "Airdate": "Date de diffusion",
        "Air Date": "Date de diffusion",
        "Air date": "Date de diffusion",
        "Air Date:": "Date de diffusion :",
        "Air date:": "Date de diffusion :",
        "Airdate:": "Date de diffusion :",
        "Filename": "Nom de fichier",
        "Size": "Taille",
        "Search": "Rechercher",
        "Status": "Statut",
        "Action": "Action",
        "Actions": "Actions",
        "Edit": "Modifier",
        "Delete": "Supprimer",
        "Remove": "Supprimer",
        "Scan & Rename": "Scanner & Renommer",
        "Scanner & Renommer": "Scanner & Renommer",
        "Scanner et renommer": "Scanner et renommer",
        "Old Location / New Location": "Ancien nom / Nouveau nom (Avant / Après)",
        "Supprimer": "Supprimer",
        "Re-scan files": "Re-scanner les fichiers",
        "Quick file scan": "Scan rapide des fichiers",
        "Force Update": "Forcer la mise à jour",
        "Full update": "Mise à jour complète",
        "Cast update": "Mise à jour de la distribution",
        "Emby show update": "Mise à jour Emby",
        "Kodi show update": "Mise à jour Kodi",
        "XBMC show update": "Mise à jour XBMC",
        "Download subtitles": "Télécharger les sous-titres",
        "Rename media": "Renommer les médias",
        "Pause show": "Mettre en pause",
        "Unpause show": "Reprendre",
        "Change Selected Episodes to": "Changer les épisodes sélectionnés en",
        "Change selected episodes to": "Changer les épisodes sélectionnés en",
        "Go": "Valider",
        "Select All": "Tout sélectionner",
        "Select all": "Tout sélectionner",
        "Clear All": "Tout désélectionner",
        "Clear all": "Tout désélectionner",
        "Select filtered episodes": "Sélectionner les épisodes filtrés",
        "Expand All": "Tout développer",
        "Collapse All": "Tout réduire",
        "Prev Episode": "Épisode précédent",
        "Specials": "Hors-série",
        "Special": "Hors-série",
        "Show specials": "Afficher les hors-série",
        "Hide specials": "Masquer les hors-série",
        "Unhide specials": "Afficher les hors-série",
        "Show all": "Tout afficher",
        "Hide most": "Réduire",
        "Hide all": "Tout masquer",
        "Show most": "Tout afficher",
        "Overview": "Synopsis",
        "Location": "Emplacement",
        "Airs": "Diffusion",
        "Aired": "Diffusé",
        "Air": "Diffusion",
        "Premiered": "Première diffusion",
        "Runtime": "Durée",
        "mins.": "min.",
        "mins": "min.",
        "min.": "min.",
        "IMDb rating": "Note IMDb",
        "No votes available": "Aucun vote disponible",
        "Qualities": "Qualités",
        "Upgrade to": "Améliorer vers",
        "Upgrade once": "Améliorer une seule fois",
        "Scene Exceptions": "Exceptions Scene",
        "Scene Exception": "Exception Scene",
        "Scene names": "Noms Scene",
        "Pause": "Mettre en pause",
        "Unpause": "Reprendre",
        "Resume": "Reprendre",
        "Change Show Quality": "Changer la qualité",
        "Remove Show": "Supprimer la série",
        "Edit Show": "Modifier la série",
        "Re-check Show": "Revérifier la série",
        "Manual Search": "Recherche manuelle",
        "Automatic Search": "Recherche automatique",
        "Subtitle Search": "Recherche sous-titres",
        "Meta": "Méta",
        "Scene": "Scène",
        "Scene absolute": "Scène absolue",
        "with archived quality": "avec la qualité archivée",
        "Archived with": "Archivé avec",
        "downloaded quality": "qualité téléchargée",
        "default": "par défaut",
        "Filter Episodes": "Filtrer les épisodes",
        "Filter episodes": "Filtrer les épisodes",
        "Ignored words": "Mots ignorés",
        "Required words": "Mots requis",
        "Excluded global ignored words": "Mots ignorés globaux exclus",
        "Excluded global required words": "Mots requis globaux exclus",
        "Flat folders": "Dossiers plats",
        "Air by date": "Diffusion par date",
        "DVD order": "Ordre DVD",
        "Scene numbering": "Numérotation Scene",
        "Sports": "Sports",
        "Wanted group": "Groupe recherché",
        "Wanted groups": "Groupes recherchés",
        "Unwanted group": "Groupe non désiré",
        "Unwanted groups": "Groupes non désirés",
        "No plot overview available": "Aucun synopsis disponible",
        "Videos": "Vidéos",
        "Links": "Liens",
        "No genres": "Aucun genre",
        "View:": "Affichage :",
        "View": "Affichage",
        "of": "sur",
        "with": "avec",
        "and": "et",
        "file": "fichier",
        "files": "fichiers",
        "archived": "archivé",
        "archived files": "fichiers archivés",
        "No episode details at TV info source": "Aucun détail d'épisode à la source TV",
        "Restart SickShift to reveal new options here": "Redémarrez SickShift pour voir de nouvelles options ici",
        "Restart SickShift for new features on this page": "Redémarrez SickShift pour les nouvelles fonctionnalités sur cette page",

        // Schedule / Calendar
        "Today": "Aujourd'hui",
        "Soon": "Bientôt",
        "Later": "Plus tard",
        "Missed": "Manqués",
        "All": "Tout",
        "Calendar": "Calendrier",
        "List": "Liste",
        "Day": "Jour",
        "Week": "Semaine",
        "Month": "Mois",

        // History
        "Time": "Heure",
        "Provider": "Fournisseur",
        "Clear History": "Vider l'historique",
        "Trim History": "Purger l'historique",

        // Footer stats
        "shows": "séries",
        "active": "actives",
        "episodes downloaded": "épisodes téléchargés",
        "snatched": "récupérés",
        "next connect": "prochaine connexion",
        "for...": "pour...",
        "free space": "espace libre",
        "Free space stats for volume/path": "Espace libre par volume/chemin",
        "Metadata from": "Métadonnées de",

        // Generic buttons
        "Save Changes": "Enregistrer les modifications",
        "Save": "Enregistrer",
        "Cancel": "Annuler",
        "Close": "Fermer",
        "Yes": "Oui",
        "No": "Non",
        "OK": "OK",
        "Submit": "Envoyer",
        "Refresh": "Actualiser",
        "Update": "Mettre à jour",
        "Back": "Retour",
        "Next": "Suivant",
        "Previous": "Précédent",
        "Apply": "Appliquer"
    };

    const ATTR_DICT = {
        "Process Media": "Traiter les médias",
        "Filter Show Name": "Filtrer par nom de série",
        "Filter": "Filtrer",
        "Filter Episodes": "Filtrer les épisodes",
        "Filter episodes": "Filtrer les épisodes",
        "Search": "Rechercher",
        "Reset Filter": "Réinitialiser le filtre",
        "View overview of snatched episodes": "Voir l'aperçu des épisodes récupérés",
        "Change time layout": "Changer le format d'affichage de l'heure",
        "Tableau de bord - Épisodes à venir et manquants": "Tableau de bord - Épisodes à venir et manquants",
        "Click to scroll to specials": "Cliquer pour aller aux hors-série",
        "Retry download": "Réessayer le téléchargement",
        "Manual search": "Recherche manuelle",
        "Search subtitles": "Rechercher des sous-titres",
        "Enter a new SSxEE if different at the provider (e.g. 20x5). Remove content for default": "Entrez un nouveau SSxEE si différent chez le fournisseur (ex. 20x5). Videz pour la valeur par défaut",
        "Enter a new absolute number if different at the provider (e.g. 22). Remove content for default": "Entrez un nouveau numéro absolu si différent chez le fournisseur (ex. 22). Videz pour la valeur par défaut"
    };

    const PATTERNS = [
        // Show seasons and season headers
        { regex: /^(?:Season|Saison)\s+(\d+)$/i, replace: "Saison $1" },
        { regex: /^(?:Season|Saison):\s*(\d+)$/i, replace: "Saison : $1" },
        { regex: /^(?:Episode|Épisode)\s+(\d+)$/i, replace: "Épisode $1" },
        { regex: /^(?:Episode|Épisode):\s*(\d+)$/i, replace: "Épisode : $1" },
        { regex: /^(?:Show|Afficher la)\s+(?:season|saison)\s+(\d+)$/i, replace: "Afficher la saison $1" },
        { regex: /^(?:Hide|Masquer la)\s+(?:season|saison)\s+(\d+)$/i, replace: "Masquer la saison $1" },
        { regex: /^(?:Show|Afficher les)\s+specials$/i, replace: "Afficher les hors-série" },
        { regex: /^(?:Hide|Masquer les)\s+specials$/i, replace: "Masquer les hors-série" },
        { regex: /^Show\s+all$/i, replace: "Tout afficher" },
        { regex: /^Hide\s+most$/i, replace: "Réduire" },
        { regex: /^Hide\s+all$/i, replace: "Tout masquer" },
        { regex: /^Show\s+most$/i, replace: "Tout afficher" },

        // Quantities, files and counts
        { regex: /^(\d+)\s+of\s+(\d+)$/i, replace: "$1 sur $2" },
        { regex: /^of\s+(\d+)$/i, replace: "sur $1" },
        { regex: /^with\s+(\d+)\s+files?$/i, replace: "avec $1 fichiers" },
        { regex: /^with\s+(\d+)\s+archived$/i, replace: "avec $1 archivés" },
        { regex: /^(\d+)\s+files?$/i, replace: "$1 fichiers" },
        { regex: /^(\d+)\s+file$/i, replace: "$1 fichier" },
        { regex: /^(\d+)\s+archived$/i, replace: "$1 archivés" },
        { regex: /^(\d+)\s+episodes?/i, replace: "$1 épisodes" },
        { regex: /^(\d+)\s+specials?/i, replace: "$1 hors-série" },
        { regex: /^(\d+)\s+to\s+prune$/i, replace: "$1 à purger" },
        { regex: /^keep\s+(\d+)$/i, replace: "garder $1" },
        { regex: /^No\s+files?$/i, replace: "Aucun fichier" },

        // Checkbox labels & status tallies
        { regex: /^Downloaded:\s*$/i, replace: "Téléchargés :" },
        { regex: /^Snatched:\s*$/i, replace: "Récupérés :" },
        { regex: /^Wanted:\s*$/i, replace: "Recherchés :" },
        { regex: /^Upgradable:\s*$/i, replace: "Améliorables :" },
        { regex: /^Skipped:\s*$/i, replace: "Ignorés :" },
        { regex: /^Failed:\s*$/i, replace: "Échoués :" },
        { regex: /^Ignored:\s*$/i, replace: "Ignorés :" },
        { regex: /^Downloaded:\s*(\d+)/i, replace: "Téléchargés : $1" },
        { regex: /^Snatched:\s*(\d+)/i, replace: "Récupérés : $1" },
        { regex: /^Wanted:\s*(\d+)/i, replace: "Recherchés : $1" },
        { regex: /^Upgradable:\s*(\d+)/i, replace: "Améliorables : $1" },
        { regex: /^Skipped:\s*(\d+)/i, replace: "Ignorés : $1" },
        { regex: /^Failed:\s*(\d+)/i, replace: "Échoués : $1" },
        { regex: /^Total:\s*(\d+)/i, replace: "Total : $1" },

        // Options
        { regex: /^default\s*\((.*?)\)$/i, replace: "par défaut ($1)" },

        // Time unknown
        { regex: /^\((.*?)\s+time unknown\)$/i, replace: "($1 heure inconnue)" },
        { regex: /^\(time unknown\)$/i, replace: "(heure inconnue)" },

        // Stats patterns
        { regex: /^(\d+)\s+shows\s+\((\d+)\s+active\)$/i, replace: "$1 séries ($2 actives)" },
        { regex: /^(\d+)\s+episodes downloaded/i, replace: "$1 épisodes téléchargés" },
        { regex: /^\(\+(\d+)\s+snatched\)$/i, replace: "(+$1 récupérés)" },
        { regex: /^Loading\.\.\.\s*\((.*?)\)$/i, replace: "Chargement... ($1)" }
    ];

    const ATTR_PATTERNS = [
        { regex: /^View\s+poster\s+for\s+(.*)$/i, replace: "Voir l'affiche de $1" },
        { regex: /^Previous\s+show:\s*(.*)$/i, replace: "Série précédente : $1" },
        { regex: /^Next\s+show:\s*(.*)$/i, replace: "Série suivante : $1" },
        { regex: /^View\s+(.*?)\s+info\s+in\s+new\s+tab$/i, replace: "Voir les infos $1 dans un nouvel onglet" },
        { regex: /^View\s+other\s+popular\s+(.*?)\s+shows\s+on\s+(.*)$/i, replace: "Voir d'autres séries populaires du genre $1 sur $2" },
        { regex: /^Season\s+(\d+)$/i, replace: "Saison $1" }
    ];

    // Build lowercase lookup dictionaries for case-insensitive matching fallbacks
    const LOWER_DICT = Object.create(null);
    for (const [k, v] of Object.entries(DICT)) {
        LOWER_DICT[k.toLowerCase()] = v;
    }
    const LOWER_ATTR_DICT = Object.create(null);
    for (const [k, v] of Object.entries(ATTR_DICT)) {
        LOWER_ATTR_DICT[k.toLowerCase()] = v;
    }

    const IGNORED_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA', 'CODE', 'PRE', 'SVG', 'PATH']);

    function translateText(str) {
        if (!str) return str;
        const trimmed = str.trim();
        if (!trimmed) return str;

        // Exact match
        if (DICT[trimmed]) {
            return str.replace(trimmed, DICT[trimmed]);
        }

        // Lowercase match fallback
        const lower = trimmed.toLowerCase();
        if (LOWER_DICT[lower]) {
            return str.replace(trimmed, LOWER_DICT[lower]);
        }

        // Handle strings with attached opening parenthesis e.g. "Show List (" or "History ("
        const withoutParen = trimmed.replace(/\s*\($/, '');
        if (withoutParen !== trimmed) {
            if (DICT[withoutParen]) {
                return str.replace(withoutParen, DICT[withoutParen]);
            }
            const lowerWP = withoutParen.toLowerCase();
            if (LOWER_DICT[lowerWP]) {
                return str.replace(withoutParen, LOWER_DICT[lowerWP]);
            }
        }

        // Regex patterns
        for (let i = 0; i < PATTERNS.length; i++) {
            if (PATTERNS[i].regex.test(trimmed)) {
                return str.replace(trimmed, trimmed.replace(PATTERNS[i].regex, PATTERNS[i].replace));
            }
        }
        return str;
    }

    function resolveAttrTranslation(val) {
        if (!val) return null;
        const trimmed = val.trim();
        if (ATTR_DICT[trimmed]) return ATTR_DICT[trimmed];
        if (DICT[trimmed]) return DICT[trimmed];
        const lower = trimmed.toLowerCase();
        if (LOWER_ATTR_DICT[lower]) return LOWER_ATTR_DICT[lower];
        if (LOWER_DICT[lower]) return LOWER_DICT[lower];
        for (let i = 0; i < ATTR_PATTERNS.length; i++) {
            if (ATTR_PATTERNS[i].regex.test(trimmed)) {
                return trimmed.replace(ATTR_PATTERNS[i].regex, ATTR_PATTERNS[i].replace);
            }
        }
        return null;
    }

    function translateElementAttributes(el) {
        if (!el || el.nodeType !== Node.ELEMENT_NODE) return;

        // Placeholders
        const ph = el.getAttribute('placeholder');
        if (ph) {
            const trans = resolveAttrTranslation(ph);
            if (trans && trans !== ph) el.setAttribute('placeholder', trans);
        }

        // Titles
        const title = el.getAttribute('title');
        if (title) {
            const trans = resolveAttrTranslation(title);
            if (trans && trans !== title) el.setAttribute('title', trans);
        }

        // Labels (optgroup, etc.)
        const label = el.getAttribute('label');
        if (label) {
            const trans = resolveAttrTranslation(label);
            if (trans && trans !== label) el.setAttribute('label', trans);
        }

        // aria-label
        const ariaLabel = el.getAttribute('aria-label');
        if (ariaLabel) {
            const trans = resolveAttrTranslation(ariaLabel);
            if (trans && trans !== ariaLabel) el.setAttribute('aria-label', trans);
        }

        // Submit and button values
        if (el.tagName === 'INPUT' && (el.type === 'button' || el.type === 'submit' || el.type === 'reset')) {
            const val = el.value;
            if (val) {
                const trans = resolveAttrTranslation(val);
                if (trans && trans !== val) el.value = trans;
            }
        }
    }

    function translateNode(node) {
        if (!node) return;

        if (node.nodeType === Node.TEXT_NODE) {
            const parent = node.parentElement;
            if (parent && !IGNORED_TAGS.has(parent.tagName)) {
                const original = node.nodeValue;
                const translated = translateText(original);
                if (translated !== original) {
                    node.nodeValue = translated;
                }
            }
            return;
        }

        if (node.nodeType === Node.ELEMENT_NODE) {
            if (IGNORED_TAGS.has(node.tagName)) return;
            translateElementAttributes(node);

            // Select options
            if (node.tagName === 'OPTION') {
                const t = node.textContent;
                const trimmed = t.trim();
                const trans = translateText(trimmed);
                if (trans !== trimmed) {
                    node.textContent = t.replace(trimmed, trans);
                }
            }

            let child = node.firstChild;
            while (child) {
                translateNode(child);
                child = child.nextSibling;
            }
        }
    }

    function checkQuebecFlags() {
        const detailsEl = document.getElementById('showCol');
        if (detailsEl) {
            const text = detailsEl.innerText.toLowerCase();
            const qcKeywords = ['tqs', 'tva', 'télé-québec', 'tele-quebec', 'radio-canada', 'src', 'noovo', 'vrak', 'canal d', 'canal vie', 'ztele', 'ztélé', 'musiqueplus', 'sériesplus', 'seriesplus', 'super écran', 'super ecran', 'tou.tv', 'club illico', 'unis tv', 'addik', 'prise 2', 'casa', 'évasion', 'evasion', 'zeste'];
            const isQc = qcKeywords.some(kw => text.includes(kw));
            if (isQc) {
                const caFlags = detailsEl.querySelectorAll('img.flag[src*="ca.png"]');
                caFlags.forEach(img => {
                    img.src = img.src.replace('ca.png', 'qc.png');
                    img.title = 'Québec';
                });
            }
        }
    }

    let isTranslating = false;

    function runTranslation(root) {
        if (isTranslating) return;
        isTranslating = true;
        try {
            translateNode(root || document.body);
            checkQuebecFlags();
        } finally {
            isTranslating = false;
        }
    }

    // Initial translation execution upon DOM load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            runTranslation(document.body);
        });
    } else {
        runTranslation(document.body);
    }

    // Observer for dynamically added content (Isotope, AJAX, filtering)
    const observer = new MutationObserver(function(mutations) {
        if (isTranslating) return;
        for (let i = 0; i < mutations.length; i++) {
            const mut = mutations[i];
            if (mut.type === 'childList') {
                for (let j = 0; j < mut.addedNodes.length; j++) {
                    const added = mut.addedNodes[j];
                    if (added.nodeType === Node.ELEMENT_NODE || added.nodeType === Node.TEXT_NODE) {
                        runTranslation(added);
                    }
                }
            } else if (mut.type === 'characterData') {
                translateNode(mut.target);
            }
        }
    });

    // Start mutation observer as soon as document.body is ready
    function startObserver() {
        if (document.body) {
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                characterData: true
            });
        } else {
            setTimeout(startObserver, 20);
        }
    }
    startObserver();

})();
