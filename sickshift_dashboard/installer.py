#!/usr/bin/env python3
"""
Installer and auto-repair integration script for SickShift Dashboard.
Ensures that the FastAPI Dashboard is mounted in Tornado, present in the navigation bar,
that display enhancements (smooth zoom on /view-shows/, network logo containment) are active,
and that the multi-language translation engine (system language detection) is configured,
even after upstream SickShift git updates (`git pull`, etc.).
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import unicodedata
from pathlib import Path


NAV_ITEM_SNIPPET = '''\t\t\t\t\t<li id="NAVdashboard">
\t\t\t\t\t\t<a href="$sbRoot/dashboard" tabindex="$tab#set $tab += 1#" title="Dashboard - Upcoming & Missing Episodes">
\t\t\t\t\t\t\t<i class="sgicon-cal"></i>
\t\t\t\t\t\t\t<span>Dashboard</span>
\t\t\t\t\t\t</a>
\t\t\t\t\t</li>
'''

DROPDOWN_SNIPPET = '''\t\t\t\t\t\t\t<li><a href="$sbRoot/dashboard" tabindex="$tab#set $tab += 1#"><i class="sgicon-cal"></i>Dashboard (Upcoming / Missing)</a></li>
\t\t\t\t\t\t\t<li><a href="$sbRoot/dashboard/mini" tabindex="$tab#set $tab += 1#"><i class="sgicon-episodestatus"></i>Dashboard Mini</a></li>
\t\t\t\t\t\t\t<li class="divider"></li>
'''

I18N_SCRIPT_SNIPPET = '''#import locale, os
#set $sys_lang = os.environ.get('LANG', os.environ.get('LC_ALL', locale.getdefaultlocale()[0] or 'en')).split('.')[0].split('_')[0].lower()
\t<script>window.SG_SYS_LANG = "$sys_lang";</script>
\t<script src="$sbRoot/js/i18n.js?v=$sbPID"></script>
\t<style>
\t\t#NAVdashboard {
\t\t\tfloat: left !important;
\t\t\theight: 50px !important;
\t\t\tdisplay: flex !important;
\t\t\talign-items: center !important;
\t\t\tpadding: 0 10px 0 0 !important;
\t\t\tmargin: 0 !important;
\t\t}
\t\t#NAVdashboard > a {
\t\t\twidth: auto !important;
\t\t\theight: 32px !important;
\t\t\tmargin: 0 !important;
\t\t\tpadding: 0 12px !important;
\t\t\tdisplay: inline-flex !important;
\t\t\talign-items: center !important;
\t\t\tgap: 6px !important;
\t\t\tline-height: 30px !important;
\t\t\tfont-size: 13px !important;
\t\t\tfont-weight: 600 !important;
\t\t\tcolor: #3dd9eb !important;
\t\t\tbackground: rgba(61, 217, 235, 0.12) !important;
\t\t\tborder: 1px solid rgba(61, 217, 235, 0.3) !important;
\t\t\tborder-radius: 6px !important;
\t\t\ttext-decoration: none !important;
\t\t\tbox-shadow: none !important;
\t\t\tbox-sizing: border-box !important;
\t\t\ttransition: background-color 150ms ease, border-color 150ms ease, color 150ms ease;
\t\t}
\t\t#NAVdashboard > a:hover {
\t\t\tbackground: rgba(61, 217, 235, 0.22) !important;
\t\t\tborder-color: #3dd9eb !important;
\t\t\tcolor: #ffffff !important;
\t\t}
\t\t#NAVdashboard > a i {
\t\t\tfont-size: 14px;
\t\t\tcolor: inherit;
\t\t}
\t</style>
'''

TORNADO_BRIDGE_SNIPPET = '''        # Native mounting of FastAPI Dashboard under /dashboard
        try:
            from sickshift_dashboard.bridge import register_tornado_bridge
            register_tornado_bridge(
                self.app,
                self.re_host_pattern,
                self.options['web_root'],
                prefix='/dashboard',
            )
            logger.log('SickShift Dashboard FastAPI mounted on /dashboard')
        except Exception as exc:
            logger.error(f'Failed to mount SickShift Dashboard: {exc}')

'''

SICKSHIFT_PY_SNIPPET = '''
# Auto-check and repair FastAPI Dashboard integration
try:
    from sickshift_dashboard.installer import ensure_dashboard_installed
    ensure_dashboard_installed(os.path.dirname(os.path.abspath(__file__)))
except Exception:
    pass
'''

HOME_TMPL_ZOOM_SNIPPET = '''
\t\t/* Image zoom and neon glow effect */
\t\t.posterview .show-card {
\t\t\theight: 354px !important;
\t\t\toverflow: hidden !important;
\t\t\tborder-radius: 6px !important;
\t\t\ttransition: box-shadow 250ms cubic-bezier(.4, 0, .2, 1), border-color 250ms cubic-bezier(.4, 0, .2, 1);
\t\t}
\t\t.posterview .show-card:hover {
\t\t\tborder-color: #3dd9eb !important;
\t\t\tbox-shadow: 0 0 16px rgba(61, 217, 235, 0.55), 0 8px 24px rgba(0, 0, 0, 0.45) !important;
\t\t}
\t\t.posterview .show-card .ui-progressbar {
\t\t\tborder-top: 1px solid #111 !important;
\t\t\tborder-bottom: none !important;
\t\t\tborder-left: none !important;
\t\t\tborder-right: none !important;
\t\t\theight: 8px !important;
\t\t\ttransition: background-color 250ms, box-shadow 250ms, border-color 250ms !important;
\t\t}
\t\t.posterview .show-card:hover .ui-progressbar {
\t\t\tborder-top: 1px solid rgba(61, 217, 235, 0.4) !important;
\t\t\tbackground-color: rgba(61, 217, 235, 0.15) !important;
\t\t\tbox-shadow: inset 0 0 6px rgba(61, 217, 235, 0.4) !important;
\t\t}
\t\t.posterview .show-card:hover .ui-progressbar-value {
\t\t\tbox-shadow: 0 0 8px rgba(61, 217, 235, 0.6) !important;
\t\t}
\t\t.posterview div.show-image {
\t\t\toverflow: hidden !important;
\t\t\tposition: relative;
\t\t\tborder-top-left-radius: 5px;
\t\t\tborder-top-right-radius: 5px;
\t\t}
\t\t.posterview div.show-image img {
\t\t\ttransition: transform 300ms cubic-bezier(.4, 0, .2, 1);
\t\t\twill-change: transform;
\t\t\tbackface-visibility: hidden;
\t\t\tdisplay: block;
\t\t}
\t\t.posterview .show-card:hover div.show-image img,
\t\t.posterview div.show-image:hover img {
\t\t\ttransform: scale(1.08);
\t\t}

\t\t/* Small Poster mode (thumbnails) */
\t\t.imgsmallposter {
\t\t\tposition: relative;
\t\t}
\t\t.imgsmallposter img.small {
\t\t\ttransition: transform 250ms cubic-bezier(.4, 0, .2, 1), box-shadow 250ms cubic-bezier(.4, 0, .2, 1), border-color 250ms cubic-bezier(.4, 0, .2, 1);
\t\t\tposition: relative;
\t\t\tdisplay: inline-block;
\t\t\ttransform-origin: center center;
\t\t}
\t\t.imgsmallposter:hover img.small,
\t\t.imgsmallposter img.small:hover {
\t\t\ttransform: scale(1.65);
\t\t\tz-index: 1000;
\t\t\tborder-color: #3dd9eb !important;
\t\t\tbox-shadow: 0 8px 24px rgba(0, 0, 0, 0.65);
\t\t}

\t\t/* Banner mode */
\t\t.imgbanner {
\t\t\toverflow: hidden;
\t\t\tborder-radius: 8px;
\t\t}
\t\t.imgbanner .banner {
\t\t\ttransition: transform 300ms cubic-bezier(.4, 0, .2, 1), box-shadow 300ms cubic-bezier(.4, 0, .2, 1);
\t\t\twill-change: transform;
\t\t}
\t\t.imgbanner:hover .banner,
\t\t.imgbanner .banner:hover {
\t\t\ttransform: scale(1.05);
\t\t\tbox-shadow: 0 6px 18px rgba(0, 0, 0, 0.4);
\t\t}

\t\t/* Network logo container and uniform layout */
\t\t.posterview .show-card table {
\t\t\ttable-layout: fixed !important;
\t\t\twidth: 100% !important;
\t\t}
\t\t.posterview .show-card table td.show-table:first-child {
\t\t\twidth: 24px !important;
\t\t\ttext-align: left !important;
\t\t\toverflow: hidden !important;
\t\t\twhite-space: nowrap !important;
\t\t}
\t\t.posterview .show-card table td.show-network {
\t\t\twidth: 88px !important;
\t\t\ttext-align: center !important;
\t\t\tvertical-align: middle !important;
\t\t\tpadding: 0 !important;
\t\t\toverflow: hidden !important;
\t\t\twhite-space: nowrap !important;
\t\t}
\t\t.posterview .show-card table td.show-quality {
\t\t\twidth: 74px !important;
\t\t\ttext-align: right !important;
\t\t\toverflow: hidden !important;
\t\t\twhite-space: nowrap !important;
\t\t\ttext-overflow: ellipsis !important;
\t\t}
\t\t.posterview .show-card table td.show-quality .show-quality {
\t\t\tfont-size: 10px !important;
\t\t\tletter-spacing: -0.2px !important;
\t\t}
\t\t.show-table.show-network {
\t\t\theight: 22px;
\t\t\tline-height: 22px;
\t\t\tvertical-align: middle;
\t\t\toverflow: hidden !important;
\t\t\ttext-align: center;
\t\t\twhite-space: nowrap;
\t\t\ttext-overflow: ellipsis;
\t\t}
\t\t.show-network-image {
\t\t\twidth: 74px !important;
\t\t\theight: 22px !important;
\t\t\tmax-width: 74px !important;
\t\t\tmax-height: 22px !important;
\t\t\tobject-fit: contain !important;
\t\t\tvertical-align: middle !important;
\t\t\tdisplay: inline-block !important;
\t\t}
\t\ttable.tablesorter tbody tr:hover td {
\t\t\tbackground-color: rgba(61, 217, 235, 0.035) !important;
\t\t\tborder-top: 1px solid rgba(61, 217, 235, 0.28) !important;
\t\t\tborder-bottom: 1px solid rgba(61, 217, 235, 0.28) !important;
\t\t\tbox-shadow: none !important;
\t\t}
\t\ttable.tablesorter tbody tr:hover td:first-child {
\t\t\tborder-left: 2px solid rgba(61, 217, 235, 0.65) !important;
\t\t\tborder-top-left-radius: 4px;
\t\t\tborder-bottom-left-radius: 4px;
\t\t\tbox-shadow: none !important;
\t\t}
\t\ttable.tablesorter tbody tr:hover td:last-child {
\t\t\tborder-right: 1px solid rgba(61, 217, 235, 0.28) !important;
\t\t\tborder-top-right-radius: 4px;
\t\t\tborder-bottom-right-radius: 4px;
\t\t\tbox-shadow: none !important;
\t\t}
'''

GIT_HOOK_SCRIPT = '''#!/bin/sh
# Cross-platform git hook to ensure dashboard integration survives merges
GIT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
if [ -f "$GIT_DIR/sickshift_dashboard/installer.py" ]; then
    if command -v python3 >/dev/null 2>&1; then
        python3 "$GIT_DIR/sickshift_dashboard/installer.py" "$GIT_DIR" >/dev/null 2>&1 || true
    elif command -v python >/dev/null 2>&1; then
        python "$GIT_DIR/sickshift_dashboard/installer.py" "$GIT_DIR" >/dev/null 2>&1 || true
    elif command -v py >/dev/null 2>&1; then
        py "$GIT_DIR/sickshift_dashboard/installer.py" "$GIT_DIR" >/dev/null 2>&1 || true
    fi
fi
'''


def patch_inc_top(tmpl_path: Path) -> bool:
    if not tmpl_path.exists():
        return False
    content = tmpl_path.read_text(encoding="utf-8", errors="replace")
    modified = False

    if 'id="NAVdashboard"' not in content:
        target = '<li id="NAVhome"'
        if target in content:
            content = content.replace(target, NAV_ITEM_SNIPPET + target, 1)
            modified = True

    if 'href="$sbRoot/dashboard"' not in content:
        dropdown_marker = '<ul class="dropdown-menu" style="min-width:204px">'
        if dropdown_marker in content:
            replacement = dropdown_marker + "\n" + DROPDOWN_SNIPPET
            content = content.replace(dropdown_marker, replacement, 1)
            modified = True

    if 'i18n.js' not in content:
        head_end = '</head>'
        if head_end in content:
            content = content.replace(head_end, I18N_SCRIPT_SNIPPET + head_end, 1)
            modified = True

    if modified:
        tmpl_path.write_text(content, encoding="utf-8")
        print(f"[INSTALLER] Navigation bar and i18n patched: {tmpl_path}")
    return modified


def patch_home_tmpl(tmpl_path: Path) -> bool:
    if not tmpl_path.exists():
        return False
    content = tmpl_path.read_text(encoding="utf-8", errors="replace")
    modified = False

    if "/* Image zoom and neon glow effect */" not in content and "/* Image zoom effect (Dashboard style) */" not in content and "/* Effet de zoom d'image (style Dashboard) */" not in content:
        target = ".spinner{display:inline-block;width:16px;height:16px;background:url(${sg_root}/images/loading16${theme_suffix}.gif) no-repeat 0 0}"
        if target in content:
            content = content.replace(target, target + HOME_TMPL_ZOOM_SNIPPET, 1)
            modified = True

    if modified:
        tmpl_path.write_text(content, encoding="utf-8")
        print(f"[INSTALLER] home.tmpl patched (zoom + network logo containment): {tmpl_path}")
    return modified


def ensure_network_logos(root_path: Path) -> None:
    net_dir = root_path / "gui" / "slick" / "images" / "network"
    if not net_dir.is_dir():
        return

    src_candidates = [
        net_dir / "iciradio-canadatélé.png",
        net_dir / "radio-canada.png",
    ]
    src = next((c for c in src_candidates if c.exists()), None)
    if src:
        targets = [
            "ici radio-canada télé.png",
            unicodedata.normalize("NFD", "ici radio-canada télé.png"),
            unicodedata.normalize("NFC", "ici radio-canada télé.png"),
            "ici radio-canada.png",
        ]
        for t in targets:
            dst = net_dir / t
            if not dst.exists():
                try:
                    shutil.copy2(src, dst)
                    print(f"[INSTALLER] Network logo created: {t}")
                except Exception:
                    pass


def patch_webserve_init(py_path: Path) -> bool:
    if not py_path.exists():
        return False
    content = py_path.read_text(encoding="utf-8", errors="replace")
    if "sickshift_dashboard.bridge" in content:
        return False

    targets = [
        "        # Main Handler\n        self.app.add_handlers(self.re_host_pattern, [",
        "        # Main Handler",
        "        self.app.add_handlers(self.re_host_pattern, [",
    ]
    for target in targets:
        if target in content:
            new_content = content.replace(target, TORNADO_BRIDGE_SNIPPET + target, 1)
            py_path.write_text(new_content, encoding="utf-8")
            print(f"[INSTALLER] webserveInit.py patched successfully: {py_path}")
            return True

    print(f"[INSTALLER] WARNING: Target injection point not found in {py_path}")
    return False


def patch_sickshift_py(py_path: Path) -> bool:
    if not py_path.exists():
        return False
    content = py_path.read_text(encoding="utf-8", errors="replace")
    if "from sickshift_dashboard.installer import ensure_dashboard_installed" in content:
        return False

    target = "sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), 'lib')))"
    if target in content:
        new_content = content.replace(target, target + SICKSHIFT_PY_SNIPPET, 1)
        py_path.write_text(new_content, encoding="utf-8")
        print(f"[INSTALLER] sickshift.py startup hook added: {py_path}")
        return True

    return False


def install_git_hooks(git_dir: Path) -> None:
    hooks_dir = git_dir / ".git" / "hooks"
    if not hooks_dir.is_dir():
        return

    for hook_name in ("post-merge", "post-checkout"):
        hook_path = hooks_dir / hook_name
        current = ""
        if hook_path.exists():
            current = hook_path.read_text(encoding="utf-8", errors="replace")
        if "sickshift_dashboard/installer.py" not in current:
            hook_path.write_text(GIT_HOOK_SCRIPT, encoding="utf-8")
            hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            print(f"[INSTALLER] Git hook installed: {hook_path}")


def ensure_dashboard_installed(root_dir: str | Path | None = None) -> None:
    if root_dir is None:
        root_path = Path(__file__).resolve().parent.parent
    else:
        root_path = Path(root_dir).resolve()

    inc_top = root_path / "gui" / "slick" / "interfaces" / "default" / "inc_top.tmpl"
    home_tmpl = root_path / "gui" / "slick" / "interfaces" / "default" / "home.tmpl"
    webserve = root_path / "sickshift" / "webserveInit.py"
    sickshift_entry = root_path / "sickshift.py"

    patch_inc_top(inc_top)
    patch_home_tmpl(home_tmpl)
    patch_webserve_init(webserve)
    patch_sickshift_py(sickshift_entry)
    install_git_hooks(root_path)
    ensure_network_logos(root_path)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    ensure_dashboard_installed(target)
    print("[INSTALLER] Verification and installation finished.")
