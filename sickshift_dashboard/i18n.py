"""
Internationalization module for SickShift Dashboard.
Automatically detects host system default language (e.g. French, English, Windows/macOS/Linux).
"""

from __future__ import annotations

import locale
import os
import sys
from typing import Any


MESSAGES: dict[str, dict[str, str]] = {
    "fr": {
        "title_main": "Dashboard - Émissions TV à venir",
        "title_mini": "Dashboard - Épisodes manquants",
        "btn_back": "← Retour à SickShift",
        "btn_home": "Dashboard",
        "btn_oled": "Mode OLED",
        "nav_to_watch": "À écouter",
        "nav_missing": "Manquants",
        "nav_upcoming": "À venir",
        "nav_ended": "Annulées",
        "sec_to_watch": "Prochaines émissions à écouter",
        "sec_missing": "Épisodes manquants",
        "sec_ended": "Émissions annulées",
        "sec_upcoming": "Épisodes à venir",
        "col_show": "Émission",
        "col_season": "Saison",
        "col_episode": "Épisode",
        "col_epname": "Nom de l'épisode",
        "col_network": "Réseau",
        "alt_ended": "Émission annulée",
        "episodes_missing": "épisodes manquants",
        "episode_missing": "épisode manquant",
        "all_shows_up_to_date": "Toutes les émissions sont à jour",
        "btn_copy": "Copier",
        "copied": "Copié !",
    },
    "en": {
        "title_main": "Dashboard - Upcoming TV Shows",
        "title_mini": "Dashboard - Missing Episodes",
        "btn_back": "← Back to SickShift",
        "btn_home": "Dashboard",
        "btn_oled": "OLED Mode",
        "nav_to_watch": "To Watch",
        "nav_missing": "Missing",
        "nav_upcoming": "Upcoming",
        "nav_ended": "Ended",
        "sec_to_watch": "Next Shows to Watch",
        "sec_missing": "Missing Episodes",
        "sec_ended": "Ended Shows",
        "sec_upcoming": "Upcoming Episodes",
        "col_show": "Show",
        "col_season": "Season",
        "col_episode": "Episode",
        "col_epname": "Episode Name",
        "col_network": "Network",
        "alt_ended": "Ended show",
        "episodes_missing": "missing episodes",
        "episode_missing": "missing episode",
        "all_shows_up_to_date": "All shows are up to date",
        "btn_copy": "Copy",
        "copied": "Copied!",
    },
}

MONTHS_FR = {
    1: "janvier",
    2: "février",
    3: "mars",
    4: "avril",
    5: "mai",
    6: "juin",
    7: "juillet",
    8: "août",
    9: "septembre",
    10: "octobre",
    11: "novembre",
    12: "décembre",
}

MONTHS_EN = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def get_system_language() -> str:
    """Detects the 2-letter system language code of the host OS (Linux, macOS, Windows)."""
    # 1. Standard environment variables (Linux, macOS)
    for var in ("LANG", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(var)
        if val:
            code = val.split(".")[0].split("_")[0].lower()
            if code in MESSAGES:
                return code
            if code.startswith("fr"):
                return "fr"

    # 2. Locale module (Windows, macOS, Linux)
    try:
        loc = locale.getdefaultlocale()[0]
        if loc:
            code = loc.split(".")[0].split("_")[0].lower()
            if code in MESSAGES:
                return code
            if code.startswith("fr"):
                return "fr"
    except Exception:
        pass

    # 3. Native Windows ctypes API (if available on Windows)
    if sys.platform == "win32":
        try:
            import ctypes
            windll = getattr(ctypes, "windll", None)
            if windll:
                lang_id = windll.kernel32.GetUserDefaultUILanguage() & 0xFF
                if lang_id == 0x0C:  # French (0x040C = fr-FR, 0x0C0C = fr-CA)
                    return "fr"
        except Exception:
            pass

    return "fr"


def get_i18n_context(lang: str | None = None) -> dict[str, Any]:
    """Returns translation dictionary and helper functions for templates."""
    active_lang = (lang or get_system_language()).lower()
    if active_lang not in MESSAGES:
        active_lang = "fr" if active_lang.startswith("fr") else "en"

    strings = MESSAGES[active_lang]
    months = MONTHS_FR if active_lang == "fr" else MONTHS_EN

    def format_localized_date(dt_obj: Any) -> str:
        """Formats dates according to active language."""
        if dt_obj is None:
            return ""
        if not hasattr(dt_obj, "year"):
            return str(dt_obj)

        month_name = months.get(dt_obj.month, str(dt_obj.month))
        if active_lang == "fr":
            return f"{dt_obj.day} {month_name}\n{dt_obj.year}"
        return f"{month_name} {dt_obj.day}\n{dt_obj.year}"

    return {
        "lang": active_lang,
        "t": strings,
        "format_date": format_localized_date,
    }
