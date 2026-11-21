"""Anti-regression checks for SickShift frontend JS, templates, and CSS overrides."""
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parent.parent
JS_DIR = REPO_ROOT / "gui" / "slick" / "js"
INC_TOP = REPO_ROOT / "gui" / "slick" / "interfaces" / "default" / "inc_top.tmpl"
DISPLAY_SHOW_JS = JS_DIR / "displayShow.js"
EPISODE_PREVIEW_JS = JS_DIR / "episodePreview.js"
OVERRIDE_CSS = REPO_ROOT / "gui" / "slick" / "css" / "sickshift-override.css"


class FrontendSanityTests(unittest.TestCase):
    def test_inc_top_defines_sickgear_alias_and_override_css(self):
        content = INC_TOP.read_text(encoding="utf-8", errors="ignore")
        self.assertIn(r"\$.SickShift =", content)
        self.assertIn(r"\$.SickGear = \$.SickShift;", content)
        self.assertIn("sickshift-override.css", content)

    def test_no_first_party_js_uses_unaliased_sickgear_namespace(self):
        offenders = []
        for js_file in sorted(JS_DIR.glob("*.js")):
            text = js_file.read_text(encoding="utf-8", errors="ignore")
            if "$.SickGear" in text:
                offenders.append(js_file.name)
        self.assertEqual(
            [],
            offenders,
            f"Found $.SickGear in first-party JS (use $.SickShift instead): {offenders}",
        )

    def test_display_show_keeps_season_toggle_and_delete_handlers(self):
        text = DISPLAY_SHOW_JS.read_text(encoding="utf-8", errors="ignore")
        for token in (
            "$.SickShift.qTips = qTips;",
            'button[id*="showseason-"]',
            "/home/season-render",
            ".ep-delete-btn",
            "/home/delete_episode",
        ):
            self.assertIn(token, text, f"Missing expected handler/token in displayShow.js: {token}")

    def test_episode_preview_exposes_keyboard_helpers(self):
        text = EPISODE_PREVIEW_JS.read_text(encoding="utf-8", errors="ignore")
        self.assertIn("window.hideEpisodePreview", text)
        self.assertIn("window.toggleEpisodePreviewMute", text)

    def test_override_css_has_balanced_braces_and_dlstats_fix(self):
        css = OVERRIDE_CSS.read_text(encoding="utf-8", errors="ignore")
        self.assertEqual(css.count("{"), css.count("}"), "Unbalanced braces in sickshift-override.css")
        self.assertIn(".show-dlstats", css)
        self.assertIn("white-space: nowrap", css)


if __name__ == "__main__":
    unittest.main()
