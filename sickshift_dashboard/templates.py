from __future__ import annotations

import urllib.parse
from datetime import datetime
from typing import Any, Optional

from jinja2 import BaseLoader, Environment, Template, select_autoescape

from sickshift_dashboard.config import Settings
from sickshift_dashboard.i18n import get_i18n_context

TEMPLATE_STRING = r'''<!DOCTYPE html>
<html lang="{{ lang|default('fr') }}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<link rel="manifest" href="{{ mount_prefix }}/manifest.webmanifest">
<meta name="theme-color" content="#0a0a0f">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>{{ t.title_main }}</title>
<link rel="icon" type="image/x-icon" href="{{ web_root or '' }}/images/ico/favicon.ico">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
:root{
  --bg-primary:#07090e;
  --bg-secondary:rgba(18, 24, 38, 0.70);
  --bg-tertiary:rgba(25, 34, 52, 0.85);
  --bg-card:rgba(18, 24, 38, 0.65);
  --bg-hover:rgba(56, 189, 248, 0.12);
  --border-subtle:rgba(255, 255, 255, 0.08);
  --border-light:rgba(56, 189, 248, 0.35);
  --text-primary:#f8fafc;
  --text-secondary:#94a3b8;
  --text-muted:#64748b;
  --accent-blue:#38bdf8;
  --accent-cyan:#3dd9eb;
  --shadow-sm:0 2px 8px rgba(0,0,0,.4);
  --shadow-md:0 8px 24px -4px rgba(0,0,0,.6);
  --shadow-lg:0 20px 40px -10px rgba(0,0,0,.7);
  --transition-fast:150ms cubic-bezier(.16,1,.3,1);
  --transition-base:280ms cubic-bezier(.16,1,.3,1);
  --card-border-radius:16px;
}
html{scroll-behavior:smooth}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  margin:0;padding:0;
  background-color:#07090e;
  background-image:radial-gradient(circle at 50% -15%, rgba(56, 189, 248, 0.14) 0%, rgba(129, 140, 248, 0.06) 50%, transparent 80%);
  background-attachment:fixed;
  min-height:100vh;
  color:var(--text-primary);
  line-height:1.6;
  -webkit-font-smoothing:antialiased;
}
body::before{
  content:'';position:fixed;top:0;left:0;right:0;bottom:0;
  background-image:url("{{ bg_file|default('') }}");
  background-repeat:no-repeat;background-position:center;background-size:cover;
  opacity:.04;z-index:-1;
  pointer-events:none;
}
body::after{
  display:none;
}

/* ============================================================
   AURA CINEMA - TOP NAVIGATION BAR
   ============================================================ */
.aura-topbar{
  width:100%;max-width:1440px;margin:0 auto 24px auto;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;
  background:rgba(15, 20, 32, 0.75);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
  border:1px solid rgba(255,255,255,0.08);border-radius:18px;padding:12px 20px;
  box-shadow:0 10px 30px rgba(0,0,0,0.5);
}
.aura-brand{display:flex;align-items:center;gap:12px}
.aura-logo-icon{
  width:36px;height:36px;border-radius:0;background:transparent;
  display:flex;align-items:center;justify-content:center;box-shadow:none;
}
.aura-logo-icon svg{width:20px;height:20px;fill:none;stroke:#ffffff;stroke-width:2.3}
.aura-brand-text{display:flex;flex-direction:column}
.aura-brand-title{font-size:1.05rem;font-weight:900;color:#ffffff;letter-spacing:-0.02em;line-height:1.1}
.aura-brand-tag{color:var(--accent-cyan);font-weight:600;font-size:0.75rem;margin-left:5px}
.aura-brand-sub{font-size:0.70rem;color:#94a3b8;font-weight:500}
.aura-nav-links{display:flex;align-items:center;gap:6px;background:rgba(255,255,255,0.04);padding:4px;border-radius:12px;border:1px solid rgba(255,255,255,0.05)}
.aura-nav-item{
  padding:6px 14px;border-radius:9px;font-size:0.80rem;font-weight:600;color:#cbd5e1;text-decoration:none;
  transition:all 150ms ease;
}
.aura-nav-item:hover{color:#ffffff;background:rgba(255,255,255,0.08)}
.aura-nav-item.active{background:rgba(61,217,235,0.18);color:#3dd9eb;border:1px solid rgba(61,217,235,0.3)}
.aura-top-actions{display:flex;align-items:center;gap:10px}
.aura-scan-btn{
  display:inline-flex;align-items:center;gap:7px;padding:8px 16px;border-radius:10px;
  font-size:0.78rem;font-weight:800;color:#07090e;background:linear-gradient(135deg, #38bdf8 0%, #3b82f6 100%);
  border:none;cursor:pointer;box-shadow:0 4px 14px rgba(56,189,248,0.35);transition:all 180ms ease;
}
.aura-scan-btn svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:2.4}
.aura-scan-btn:hover{background:linear-gradient(135deg, #7dd3fc 0%, #60a5fa 100%);transform:translateY(-1px);box-shadow:0 6px 18px rgba(56,189,248,0.5)}
.aura-scan-btn:active{transform:scale(0.96)}
.aura-back-btn{
  padding:8px 14px;border-radius:10px;font-size:0.80rem;font-weight:600;color:#cbd5e1;
  background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);text-decoration:none;
  transition:all 150ms ease;
}
.aura-back-btn:hover{color:#ffffff;background:rgba(255,255,255,0.12)}

/* ============================================================
   AURA CINEMA - HERO SPOTLIGHT BANNER
   ============================================================ */
.hero-banner{
  position:relative;border-radius:24px;overflow:hidden;
  border:1px solid rgba(255,255,255,0.1);
  box-shadow:0 24px 48px -12px rgba(0,0,0,0.7);
  height:360px;display:flex;align-items:flex-end;margin-bottom:30px;
  background:#090d15;
}
.hero-bg{
  position:absolute;inset:0;background-size:cover;background-position:center top;
  filter:brightness(0.92);transform:scale(1.02);transition:transform 8s ease;
}
.hero-banner:hover .hero-bg{transform:scale(1.05)}
.hero-gradient{
  position:absolute;inset:0;
  background:linear-gradient(to top, #07090e 0%, rgba(7,9,14,0.65) 50%, rgba(7,9,14,0.1) 100%),
             linear-gradient(to right, #07090e 0%, rgba(7,9,14,0.7) 40%, transparent 100%);
}
.hero-content{position:relative;z-index:2;padding:32px 40px;max-width:760px;display:flex;flex-direction:column;gap:12px}
.hero-tags{display:flex;align-items:center;gap:12px}
.hero-badge-tag{
  padding:3px 10px;border-radius:999px;font-size:0.72rem;font-weight:800;text-transform:uppercase;
  letter-spacing:0.06em;background:rgba(239,68,68,0.2);color:#f87171;border:1px solid rgba(239,68,68,0.35);
}
.hero-ready-dot{font-size:0.75rem;color:#cbd5e1;font-weight:600;display:inline-flex;align-items:center;gap:6px}
.pulse-dot{width:7px;height:7px;border-radius:999px;background:#10b981;box-shadow:0 0 8px #10b981}
.hero-title{font-size:2.8rem;font-weight:900;color:#ffffff;line-height:1.05;letter-spacing:-0.03em;margin:0;text-shadow:0 2px 10px rgba(0,0,0,0.8)}
.hero-meta{display:flex;flex-wrap:wrap;align-items:center;gap:10px;font-size:0.85rem;color:#cbd5e1}
.hero-ep-badge{font-weight:800;color:var(--accent-cyan)}
.hero-ep-title{font-weight:600;color:#ffffff}
.hero-pill{font-size:0.72rem;font-weight:700;font-family:monospace;padding:2px 8px;border-radius:6px;background:rgba(255,255,255,0.1);color:#ffffff}
.hero-actions{display:flex;align-items:center;gap:12px;margin-top:6px}
.hero-btn-play{
  display:inline-flex;align-items:center;gap:8px;padding:10px 22px;border-radius:12px;
  font-size:0.82rem;font-weight:800;color:#07090e;background:var(--accent-cyan);
  border:none;cursor:pointer;box-shadow:0 8px 20px rgba(61,217,235,0.3);
  transition:all 180ms ease;
}
.hero-btn-play svg{width:16px;height:16px;fill:currentColor}
.hero-btn-play:hover{background:#7dd3fc;transform:translateY(-1px);box-shadow:0 12px 26px rgba(61,217,235,0.45)}
.hero-btn-play:active{transform:scale(0.97)}
.hero-btn-info{
  display:inline-flex;align-items:center;gap:8px;padding:10px 18px;border-radius:12px;
  font-size:0.82rem;font-weight:600;color:#e2e8f0;background:rgba(255,255,255,0.08);
  border:1px solid rgba(255,255,255,0.15);text-decoration:none;transition:all 180ms ease;
}
.hero-btn-info:hover{background:rgba(255,255,255,0.16);color:#ffffff}

/* ============================================================
   AMBIENT BACKGROUND ANIMATION (Desktop Only >= 1025px)
   Lively yet elegant atmospheric drift
   ============================================================ */
@media (min-width: 1025px) {
  body::before {
    top: -30px; left: -30px; right: -30px; bottom: -30px;
    opacity: .075 !important;
    animation: fanart-drift 28s ease-in-out infinite alternate;
    will-change: transform, opacity;
  }
  body::after {
    content: '';
    display: block;
    position: fixed;
    top: -30%; left: -30%; width: 160%; height: 160%;
    pointer-events: none;
    z-index: -1;
    background:
      radial-gradient(ellipse 55% 45% at 20% 25%, rgba(61, 217, 235, 0.085) 0%, transparent 65%),
      radial-gradient(ellipse 50% 45% at 80% 75%, rgba(74, 158, 255, 0.075) 0%, transparent 65%),
      radial-gradient(circle 45% at 50% 50%, rgba(140, 90, 255, 0.055) 0%, transparent 60%);
    animation: ambient-aurora 22s ease-in-out infinite alternate;
    will-change: transform, opacity;
  }
}
@keyframes fanart-drift {
  0% {
    transform: scale(1) translate(0, 0);
    opacity: .065;
  }
  50% {
    transform: scale(1.05) translate(-12px, -8px);
    opacity: .085;
  }
  100% {
    transform: scale(1.08) translate(10px, 8px);
    opacity: .070;
  }
}
@keyframes ambient-aurora {
  0% {
    transform: translate3d(0, 0, 0) scale(1) rotate(0deg);
    opacity: 0.85;
  }
  33% {
    transform: translate3d(-4%, 3%, 0) scale(1.06) rotate(2deg);
    opacity: 1;
  }
  66% {
    transform: translate3d(3.5%, -3%, 0) scale(1.03) rotate(-1.5deg);
    opacity: 0.92;
  }
  100% {
    transform: translate3d(-1%, 3.5%, 0) scale(1.08) rotate(1deg);
    opacity: 0.88;
  }
}
@media (prefers-reduced-motion: reduce) {
  body::before, body::after {
    animation: none !important;
    transform: none !important;
  }
}
.content-wrapper{
  position:relative;min-height:100vh;display:flex;flex-direction:column;align-items:center;
  padding:2rem 0 calc(2rem + env(safe-area-inset-bottom));
}
.main-content{width:100%;max-width:1280px;padding:0 1.5rem}
.top-bar{
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.75rem;
  margin-bottom:1.5rem;
}
.page-precedente{margin:0}
.page-precedente a{
  color:var(--text-secondary);text-decoration:none;font-size:.9rem;font-weight:500;
  transition:var(--transition-base);display:inline-flex;align-items:center;gap:.5rem;
  padding:.5rem 1rem;border-radius:8px;border:1px solid var(--border-subtle);
  background:var(--bg-secondary);cursor:pointer;font-family:inherit;
}
.page-precedente a::before{content:none !important;display:none !important}
.page-precedente a:hover{
  color:var(--accent-cyan);border-color:var(--accent-cyan);background:var(--bg-tertiary);
}
.page-precedente a:hover{transform:translateX(-2px)}

.count-badge{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:22px;height:22px;padding:0 7px;margin-left:8px;
  font-size:.78rem;font-weight:600;border-radius:999px;
  background:rgba(61,217,235,.14);color:var(--accent-cyan);
  border:1px solid rgba(61,217,235,.28);vertical-align:middle;
}

.card{
  background:var(--bg-card);
  backdrop-filter:blur(16px);
  -webkit-backdrop-filter:blur(16px);
  border-radius:var(--card-border-radius);
  border:1px solid var(--border-subtle);
  margin-bottom:28px;overflow:hidden;
  box-shadow:var(--shadow-md);
  transition:var(--transition-base);
  scroll-margin-top:4.5rem;
}
.card:hover{
  border-color:rgba(56, 189, 248, 0.35);
  box-shadow:0 14px 32px -6px rgba(0,0,0,.6), 0 0 20px rgba(56, 189, 248, 0.12);
}
.card-header{
  padding:16px 24px;border-bottom:1px solid var(--border-subtle);
  background:linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0) 100%);
  display:flex;align-items:center;justify-content:space-between;
}
.card-header h2{
  margin:0;color:#ffffff;font-weight:700;font-size:1.35rem;letter-spacing:-0.01em;
  display:inline-flex;align-items:center;gap:10px;
}
.card-header h2::before{content:none}
.section-toggle{display:inline-flex;align-items:center;justify-content:center;width:26px;height:28px;padding:3px;border:0;background:transparent;color:var(--accent-cyan);cursor:pointer;flex-shrink:0;vertical-align:middle}
.section-toggle svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round;transition:transform .15s}
.section-toggle[aria-expanded="false"] svg{transform:rotate(180deg)}
.section-toggle:focus-visible{outline:2px solid var(--accent-cyan);border-radius:4px}
.card-content[hidden]{display:none!important}

.card-content{padding:18px}

/* Desktop layout */
.grid-container{
  display:grid;gap:0;width:100%;margin:10px auto;
  border-radius:var(--card-border-radius);overflow:hidden;
  box-shadow:var(--shadow-md);background-color:var(--bg-card);
}
.show-grid{grid-template-columns:auto 1fr auto auto auto auto}
.grid-header-row{display:contents}
.grid-header{
  font-weight:600;padding:1rem .8rem;color:var(--text-secondary);
  letter-spacing:.5px;font-size:.92rem;text-transform:uppercase;
  display:flex;justify-content:center;align-items:center;text-align:center;
  background:var(--bg-secondary);
}
.grid-item{
  padding:.7rem .8rem;border-bottom:1px solid var(--border-subtle);
  display:flex;align-items:center;min-height:65px;justify-content:center;
  text-align:center;transition:var(--transition-fast);color:var(--text-secondary);
}
.grid-item.col-title{
  justify-content:flex-start;text-align:left;color:var(--text-primary);font-weight:500;
  white-space:normal !important;word-break:break-word !important;overflow-wrap:break-word !important;
}
.show-row{display:contents}
.show-row:hover .grid-item,
.show-row.selected .grid-item,
.show-row:focus-within .grid-item{
  background-color:rgba(61,217,235,0.035) !important;
  border-top:1px solid rgba(61,217,235,0.28) !important;
  border-bottom:1px solid rgba(61,217,235,0.28) !important;
  box-shadow:none !important;
  cursor:pointer;
}
.show-row:hover .grid-item.col-thumb,
.show-row.selected .grid-item.col-thumb,
.show-row:focus-within .grid-item.col-thumb{
  border-left:2px solid rgba(61,217,235,0.65) !important;
  border-top-left-radius:6px;
  border-bottom-left-radius:6px;
  box-shadow:none !important;
  border-right:none !important;
}
.show-row:hover .grid-item.col-network,
.show-row.selected .grid-item.col-network,
.show-row:focus-within .grid-item.col-network{
  border-right:1px solid rgba(61,217,235,0.28) !important;
  border-top-right-radius:6px;
  border-bottom-right-radius:6px;
  box-shadow:none !important;
}
.show-row:hover .col-title,
.show-row:hover .col-title a,
.show-row.selected .col-title,
.show-row.selected .col-title a,
.show-row:focus-within .col-title,
.show-row:focus-within .col-title a{
  color:#ffffff !important;
}
.show-row:hover .show-thumbnail,
.show-row.selected .show-thumbnail,
.show-row:focus-within .show-thumbnail{
  border-color:var(--border-subtle) !important;
  box-shadow:none !important;
}

/* Thumbnail poster: clean neutral styling without blue/cyan glow */
.show-thumbnail{
  width:45px;height:68px;border-radius:5px;object-fit:cover;display:block;
  border:1px solid var(--border-subtle);box-shadow:var(--shadow-sm);
  transition:transform 250ms cubic-bezier(.4,0,.2,1), border-color 250ms cubic-bezier(.4,0,.2,1), box-shadow 250ms cubic-bezier(.4,0,.2,1);
}
.show-thumbnail:hover{
  transform:scale(1.65);z-index:100;position:relative;
  border-color:var(--border-light) !important;
  box-shadow:0 6px 18px rgba(0,0,0,.75) !important;
}

.ep-pill-mobile{display:none}
.network-img{
  width:78px;height:24px;object-fit:contain;
  display:block;margin:0 auto;
  filter:drop-shadow(0 1px 2px rgba(0,0,0,0.5));
}

/* ============================================================
   MISSING EPISODES SECTION (COLLAPSIBLE BY SHOW IF > 1 EPISODE)
   ============================================================ */
.missing-container{
  display:flex;flex-direction:column;gap:8px;max-width:720px;margin:0 auto;
}
.missing-card{
  background:var(--bg-secondary);border:1px solid var(--border-subtle);
  border-radius:8px;overflow:hidden;transition:border-color .2s ease,background-color .2s ease,box-shadow .2s ease;
}
.missing-card:hover{
  border-color:#3dd9eb !important;
  box-shadow:0 0 14px rgba(61,217,235,0.25) !important;
}
.missing-card:hover .show-thumbnail{
  border-color:var(--border-light) !important;
  box-shadow:none !important;
}
.missing-header{
  display:flex;align-items:center;padding:8px 12px;gap:12px;cursor:pointer;
  user-select:none;transition:background-color .15s;
}
.missing-header:hover{background-color:var(--bg-hover)}
.missing-thumb-link{display:flex;align-items:center;flex-shrink:0;text-decoration:none}
.missing-info{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px}
.missing-title-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.missing-show-title, .missing-info > .missing-title-row > .missing-ep-text{
  color:var(--text-primary);font-size:.95rem;font-weight:600;
  word-break:break-word;cursor:pointer;
}
.missing-ep-badge{
  font-size:.76rem;font-weight:700;padding:2px 8px;border-radius:999px;
  background:rgba(61,217,235,.15);color:var(--accent-cyan);
  border:1px solid rgba(61,217,235,.3);white-space:nowrap;
}
.missing-chevron{
  color:var(--accent-cyan);font-size:.75rem;transition:transform .2s ease;
  margin-left:auto;flex-shrink:0;padding:4px;
}
.missing-card.expanded .missing-chevron{transform:rotate(180deg)}
.missing-episodes-list{
  border-top:1px solid var(--border-subtle);background:rgba(10,10,15,.4);
  padding:6px 12px 10px 65px;display:flex;flex-direction:column;gap:4px;
}
.missing-ep-item{
  display:flex;align-items:center;justify-content:space-between;gap:12px;
  font-size:.90rem;color:var(--text-primary);
  padding:6px 10px;border-radius:5px;
  border-bottom:1px solid rgba(255,255,255,0.03);
  cursor:pointer;transition:background-color .15s ease, color .15s ease;
}
.missing-ep-item:last-child{border-bottom:none}
.missing-ep-item:hover{background:rgba(255,255,255,0.05)}
.missing-ep-item:hover .missing-ep-text{color:var(--accent-cyan)}
.missing-ep-text{
  font-weight:500;color:var(--text-primary);
  word-break:break-word;user-select:text;
  font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}
.missing-ep-main{font-weight:500;color:var(--text-primary)}
.missing-info > .missing-title-row > .missing-ep-text > span{font-family:inherit;font-size:inherit;font-weight:inherit}

.missing-ep-sep{color:var(--text-secondary);opacity:.6;margin:0 2px}
.missing-ep-title{color:var(--text-secondary);font-size:.88rem;font-weight:400}
.missing-ep-item.copied, .missing-info.copied{
  background:rgba(16,185,129,0.14) !important;
  color:#10b981 !important;
}
.missing-ep-item.copied .missing-ep-text,
.missing-ep-item.copied .missing-ep-main,
.missing-ep-item.copied .missing-ep-title,
.missing-info.copied .missing-ep-text,
.missing-info.copied .missing-ep-main,
.missing-info.copied .missing-ep-title{
  color:#10b981 !important;
}
.copied-pill{
  display:none;
  font-size:.74rem;
  font-weight:600;
  color:#10b981;
  background:rgba(16,185,129,0.15);
  border:1px solid rgba(16,185,129,0.35);
  padding:2px 8px;
  border-radius:4px;
  margin-left:auto;
  flex-shrink:0;
  user-select:none;
}
.missing-ep-item.copied .copied-pill,
.missing-info.copied .copied-pill{
  display:inline-block;
}

/* Ended & Upcoming shows posters with blue hover effect */
.flex-center{display:flex;flex-wrap:wrap;justify-content:center;gap:20px;margin-top:10px}
.show-cards{display:flex;flex-wrap:wrap;justify-content:center;gap:20px;padding:10px}

.show-card{
  width:200px;
  background:rgba(22, 30, 46, 0.65);
  backdrop-filter:blur(14px);
  -webkit-backdrop-filter:blur(14px);
  border:1px solid rgba(255, 255, 255, 0.08);
  border-radius:16px;overflow:hidden;
  box-shadow:0 10px 25px -5px rgba(0,0,0,0.5);
  transition:transform 280ms cubic-bezier(.16,1,.3,1), border-color 280ms cubic-bezier(.16,1,.3,1), box-shadow 280ms cubic-bezier(.16,1,.3,1);
}
.show-card:hover{
  transform:translateY(-6px) scale(1.02);
  border-color:rgba(61, 217, 235, 0.55) !important;
  box-shadow:0 20px 40px -15px rgba(61, 217, 235, 0.3), 0 0 25px rgba(61, 217, 235, 0.15) !important;
}
.show-card:hover .show-poster img{transform:scale(1.05)}
.show-card:hover .show-info h3{color:#3dd9eb !important}

.show-poster{
  position:relative;overflow:hidden;
  border-radius:12px 12px 0 0;
}
.show-poster img{
  width:100%;height:auto;aspect-ratio:2 / 3;display:block;
  transition:transform 350ms cubic-bezier(.16,1,.3,1);object-fit:cover;
}
.show-date{
  position:absolute;left:0;right:0;bottom:0;color:#ffffff;
  text-align:center !important;padding:4px 6px;font-size:.78rem;font-weight:700;
  line-height:1.2;white-space:pre-line;z-index:2;
  background:linear-gradient(180deg, transparent 0%, rgba(7,9,14,0.85) 100%);
  text-shadow:0 1px 4px rgba(0,0,0,0.95);
}
.show-info{
  padding:8px 8px 10px 8px;text-align:center !important;background:transparent;
}
.show-info h3{
  margin:0;font-size:.78rem;font-weight:600;color:#ffffff;
  letter-spacing:-.01em;line-height:1.25 !important;
  min-height:2.5em;max-height:2.5em;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;line-clamp:2;
  overflow:hidden;text-overflow:ellipsis;
  word-break:normal;overflow-wrap:break-word;
  text-align:center !important;padding:0 2px;transition:color 150ms ease;
}

.image-container{
  position:relative;overflow:hidden;border-radius:var(--card-border-radius);
  box-shadow:var(--shadow-md);border:1px solid var(--border-subtle);background:var(--bg-secondary);
  transition:transform 250ms cubic-bezier(.4,0,.2,1), border-color 250ms cubic-bezier(.4,0,.2,1), box-shadow 250ms cubic-bezier(.4,0,.2,1);
}
.image-container:hover{
  transform:translateY(-4px);
  border-color:#3dd9eb !important;
  box-shadow:0 0 18px rgba(61,217,235,.40), 0 8px 24px rgba(0,0,0,.55) !important;
}
.image-container img{width:200px;height:293px;transition:transform 300ms cubic-bezier(.4,0,.2,1);object-fit:cover;display:block}
.image-container:hover img{transform:scale(1.05);opacity:.95}

/* ============================================================
   TABLET ADAPTATION (681px - 1024px, iPad & Android Tablets)
   ============================================================ */
@media (min-width:681px) and (max-width:1024px), html[data-device="tablet"] body {
  body::before{animation:none !important;transform:none !important}
  body::after{display:none !important;animation:none !important}
  .content-wrapper{padding:1.25rem 0 calc(1.5rem + env(safe-area-inset-bottom))}
  .main-content{padding:0 1.25rem}
  .card{margin-bottom:20px;border-radius:12px}
  .card-header{padding:14px 18px}
  .card-header h2{font-size:1.3rem}

  /* Tablet grid */
  .show-grid{grid-template-columns:52px 1.5fr auto 1.5fr auto}
  .grid-header:nth-child(3),.grid-header:nth-child(4){display:none}
  .grid-item{padding:.6rem .6rem;min-height:58px}
  .grid-item.col-season,.grid-item.col-episode{display:none}
  .grid-item.col-epname{display:flex;font-size:.86rem}
  .grid-item.col-network{display:flex}
  .ep-pill-mobile{display:inline-flex;padding:3px 8px;font-size:.78rem;border-radius:5px;align-self:center}

  /* Fluid 3-4 column grid for cards on tablet */
  .show-cards,.flex-center{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(160px,1fr));
    gap:14px;padding:8px;margin-top:0;
  }
  .show-card{width:100%}
  .show-poster{aspect-ratio:2 / 3}
  .show-date{font-size:.85rem;padding:.5rem .35rem}
  .image-container{width:100%}
  .image-container img{width:100%;height:auto;aspect-ratio:2 / 3}
}

/* ============================================================
   MOBILE PHONE ADAPTATION (<=680px, Smartphones)
   ============================================================ */
@media (max-width:680px), html[data-device="mobile"] body {
  body{background-attachment:scroll}
  body::before{animation:none !important;transform:none !important;opacity:.025}
  body::after{display:none !important;animation:none !important}
  .content-wrapper{padding:.75rem 0 calc(1.5rem + env(safe-area-inset-bottom))}
  .main-content{padding:0 .75rem}
  .top-bar{margin-bottom:.75rem;gap:.5rem}
  .page-precedente a{padding:.45rem .8rem;font-size:.82rem;border-radius:8px}

  .card{margin-bottom:16px;border-radius:12px}
  .card-header{padding:12px 14px}
  .card-header h2{font-size:1.15rem;font-weight:500}
  .card-content{padding:10px}

  /* Transform table grid into compact vertical cards */
  .grid-container.show-grid{
    display:flex;flex-direction:column;gap:8px;
    margin:0;background:transparent;box-shadow:none;border-radius:0;
  }
  .grid-header-row{display:none}

  .show-row{
    display:grid;
    grid-template-columns:54px 1fr auto;
    grid-template-rows:auto auto;
    grid-template-areas:
      "thumb title badge"
      "thumb epname net";
    align-items:center;
    column-gap:12px;row-gap:3px;
    padding:9px 11px;
    background:var(--bg-secondary);
    border:1px solid var(--border-subtle);
    border-radius:10px;
    transition:transform .12s ease,background-color .15s ease, border-color .15s ease, box-shadow .15s ease;
  }
  .show-row:hover,
  .show-row.selected,
  .show-row:focus-within{
    border-color:rgba(61,217,235,0.40) !important;
    background:rgba(61,217,235,0.035) !important;
    box-shadow:0 2px 10px rgba(0,0,0,.5) !important;
  }
  .show-row:hover .show-thumbnail,
  .show-row.selected .show-thumbnail,
  .show-row:focus-within .show-thumbnail{
    border-color:var(--border-subtle) !important;
    box-shadow:none !important;
  }
  .show-row:hover .grid-item.col-title,
  .show-row.selected .grid-item.col-title,
  .show-row:focus-within .grid-item.col-title{
    color:#ffffff !important;
  }
  .show-row:active{transform:scale(.985);background-color:var(--bg-hover)}
  .show-row .grid-item{
    padding:0;min-height:0;border:none;background:transparent!important;
    justify-content:flex-start;text-align:left;
  }
  .show-row .grid-item.col-thumb{grid-area:thumb}
  .show-row .grid-item.col-thumb .show-thumbnail{
    width:52px;height:76px;border-radius:6px;transform:none!important;
  }
  .show-row .grid-item.col-title{
    grid-area:title;font-size:.96rem;font-weight:600;
    color:var(--text-primary);line-height:1.25;
    white-space:normal !important;word-break:break-word !important;overflow:visible !important;
  }
  .show-row .grid-item.col-season,
  .show-row .grid-item.col-episode{display:none}

  /* Compact S01E02 pill badge */
  .ep-pill-mobile{
    grid-area:badge;display:inline-flex;align-items:center;justify-content:center;
    padding:3px 8px;border-radius:6px;
    font-size:.76rem;font-weight:700;letter-spacing:.3px;
    background:rgba(74,158,255,.15);color:var(--accent-cyan);
    border:1px solid rgba(74,158,255,.3);white-space:nowrap;
    align-self:start;
  }
  .show-row .grid-item.col-epname{
    display:block;grid-area:epname;
    font-size:.82rem;color:var(--text-secondary);
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    max-width:100%;
  }
  .show-row .grid-item.col-network{
    display:flex;grid-area:net;justify-content:flex-end;align-items:center;
  }
  .network-img{max-height:18px;max-width:64px;opacity:.9}

  .missing-episodes-list{padding-left:55px}

  /* 2-column fluid grid for mobile upcoming and ended posters */
  .show-cards,.flex-center{
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:10px;padding:4px;margin-top:0;
  }
  .show-card{width:100%}
  .show-poster{height:auto;aspect-ratio:2 / 3}
  .show-date{font-size:.78rem;padding:3px 4px}
  .show-info{padding:5px 4px;background:transparent;text-align:center !important}
  .show-info h3{font-size:.74rem;line-height:1.25;min-height:2.5em;max-height:2.5em;text-align:center !important}
  .image-container{width:100%}
  .image-container img{width:100%;height:auto;aspect-ratio:2 / 3}
}

@media (max-width:360px){
  .show-row{grid-template-columns:46px 1fr auto;column-gap:9px;padding:8px}
  .show-row .grid-item.col-thumb .show-thumbnail{width:46px;height:68px}
  .show-row .grid-item.col-title{font-size:.9rem}
}
</style>
</head>
<body>
<div class="content-wrapper">
<div class="main-content">
<div class="top-bar" style="display:none">
  <div class="page-precedente"><a href="{{ web_root or '' }}/home/">{{ t.btn_back }}</a></div>
</div>

<div class="aura-topbar">
  <div class="aura-brand">
    <div class="aura-logo-icon">
      <img src="{{ web_root or '' }}/images/sickshift-logo.png" alt="SickShift" style="width:100%;height:100%;object-fit:contain">
    </div>
    <div class="aura-brand-text">
      <span class="aura-brand-title">SICKSHIFT <span class="aura-brand-tag">CINEMA</span></span>
      <span class="aura-brand-sub">Tableau de bord intelligent</span>
    </div>
  </div>
  <div class="aura-nav-links">
    <a href="{{ web_root or '' }}/view-shows/" class="aura-nav-item">Séries</a>
    <a href="{{ web_root or '' }}/dashboard/" class="aura-nav-item active">Dashboard</a>
    <a href="{{ web_root or '' }}/manage/" class="aura-nav-item">Gestion</a>
  </div>
  <div class="aura-top-actions">
    <button type="button" class="aura-scan-btn" id="btn-scan-rename" onclick="triggerGlobalScanRename()" title="Scanner les dossiers et renommer automatiquement">
      <svg viewBox="0 0 24 24"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
      <span>Scan & Renommer</span>
    </button>
  </div>
</div>

<div class="card" id="sec-to-watch">
<div class="card-header"><h2><button type="button" class="section-toggle" aria-expanded="true" aria-label="Replier la section" title="Replier la section" onclick="toggleDashboardSection(this)"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 15 6-6 6 6"/></svg></button> {{ t.sec_to_watch }} <span class="count-badge">{{ shows|length }}</span></h2></div>
<div class="card-content">
<div class="grid-container show-grid">
<div class="grid-header-row">
<div class="grid-header"></div><div class="grid-header">{{ t.col_show }}</div><div class="grid-header">{{ t.col_season }}</div><div class="grid-header">{{ t.col_episode }}</div><div class="grid-header">{{ t.col_epname }}</div><div class="grid-header">{{ t.col_network }}</div>
</div>
{% for show_item in shows %}
{% set link_url = show_item.indexer_id|show_link(show_item.show_id) %}
<div class="show-row" data-href="{{ link_url }}" data-has-file="1" data-indexer="{{ show_item.indexer_id or 1 }}" data-show-id="{{ show_item.show_id }}" data-season="{{ show_item.season }}" data-episode="{{ show_item.episode }}" data-show-name="{{ show_item.show_name or '' }}" data-ep-name="{{ show_item.ep_name or '' }}">
<div class="grid-item col-thumb"><a href="{{ link_url }}"><img src="{{ show_item.thumbnail or '' }}" class="show-thumbnail" alt="{{ show_item.show_name or '' }}" loading="lazy" decoding="async"></a></div>
<div class="grid-item col-title"><a href="{{ link_url }}" style="color:inherit;text-decoration:none">{{ show_item.show_name or '' }}</a></div>
<div class="grid-item col-season">{{ show_item.season if show_item.season is not none else '' }}</div>
<div class="grid-item col-episode">{{ show_item.episode if show_item.episode is not none else '' }}</div>
{% if show_item.season is not none and show_item.episode is not none %}
<span class="ep-pill-mobile">S{{ "%02d"|format(show_item.season) }}E{{ "%02d"|format(show_item.episode) }}</span>
{% endif %}
<div class="grid-item col-epname">{{ show_item.ep_name or '' }}</div>
<div class="grid-item col-network">
{% if show_item.network %}
<img src="{{ mount_prefix }}/media/network/{{ show_item.network|urlencode }}" alt="{{ show_item.network }}" title="{{ show_item.network }}" class="network-img" loading="lazy" decoding="async">
{% endif %}
</div>
</div>
{% endfor %}
</div>
</div>
</div>

{% if missing_groups %}
<div class="card" id="sec-missing">
<div class="card-header"><h2><button type="button" class="section-toggle" aria-expanded="true" aria-label="Replier la section" title="Replier la section" onclick="toggleDashboardSection(this)"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 15 6-6 6 6"/></svg></button> {{ t.sec_missing }} <span class="count-badge">{{ missing|length }}</span></h2></div>
<div class="card-content">
<div class="missing-container">
{% for group in missing_groups %}
{% set m_link = group.indexer_id|show_link(group.show_id) %}
{% if group.episodes|length > 1 %}
<div class="missing-card">
  <div class="missing-header" onclick="toggleMissingAccordion(this)">
    <a href="{{ m_link }}" class="missing-thumb-link" onclick="event.stopPropagation()" title="{{ group.show_name }}"><img src="{{ group.thumbnail or '' }}" class="show-thumbnail" alt="{{ group.show_name }}" loading="lazy" decoding="async"></a>
    <div class="missing-info">
      <div class="missing-title-row">
        <span class="missing-show-title">{{ group.show_name }}</span>
        <span class="missing-ep-badge">{{ group.episodes|length }} {{ t.episodes_missing|default('missing episodes') }}</span>
      </div>
    </div>
    <span class="missing-chevron">▼</span>
  </div>
  <div class="missing-episodes-list" style="display:none;">
    {% for ep in group.episodes %}
    <div class="missing-ep-item" onclick="copyMissingEp(event, this, '{{ ep.missing|escape }}')" title="{{ t.btn_copy|default('Copier') }} : {{ ep.missing }}">
      <span class="missing-ep-text"><span class="missing-ep-main">{{ ep.missing }}</span>{% if ep.ep_name %}<span class="missing-ep-sep"> - </span><span class="missing-ep-title">{{ ep.ep_name }}</span>{% endif %}</span>
      <span class="copied-pill">✓ {{ t.copied|default('Copié !') }}</span>
    </div>
    {% endfor %}
  </div>
</div>
{% else %}
<div class="missing-card">
  <div class="missing-header" style="cursor:default">
    <a href="{{ m_link }}" class="missing-thumb-link" title="{{ group.show_name }}"><img src="{{ group.thumbnail or '' }}" class="show-thumbnail" alt="{{ group.show_name }}" loading="lazy" decoding="async"></a>
    <div class="missing-info" onclick="copyMissingEp(event, this, '{{ group.episodes[0].missing|escape }}')" style="cursor:pointer" title="{{ t.btn_copy|default('Copier') }} : {{ group.episodes[0].missing }}">
      <div class="missing-title-row" style="justify-content:space-between;width:100%">
        <span class="missing-ep-text"><span class="missing-ep-main">{{ group.episodes[0].missing }}</span>{% if group.episodes[0].ep_name %}<span class="missing-ep-sep"> - </span><span class="missing-ep-title">{{ group.episodes[0].ep_name }}</span>{% endif %}</span>
        <span class="copied-pill">✓ {{ t.copied|default('Copié !') }}</span>
      </div>
    </div>
  </div>
</div>
{% endif %}
{% endfor %}
</div>
</div>
</div>
{% endif %}

{% if image_urls %}
<div class="card" id="sec-ended"><div class="card-header"><h2><button type="button" class="section-toggle" aria-expanded="true" aria-label="Replier la section" title="Replier la section" onclick="toggleDashboardSection(this)"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 15 6-6 6 6"/></svg></button> {{ t.sec_ended }} <span class="count-badge">{{ image_urls|length }}</span></h2></div><div class="card-content"><div class="flex-center">{% for i in range(image_urls|length) %}<div class="image-container"><a href="{{ image_links[i] }}"><img src="{{ image_urls[i] }}" alt="{{ t.alt_ended }}" loading="lazy" decoding="async"></a></div>{% endfor %}</div></div></div>
{% endif %}

{% if upcoming %}
<div class="card" id="sec-upcoming"><div class="card-header"><h2><button type="button" class="section-toggle" aria-expanded="true" aria-label="Replier la section" title="Replier la section" onclick="toggleDashboardSection(this)"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 15 6-6 6 6"/></svg></button> {{ t.sec_upcoming }} <span class="count-badge">{{ upcoming|length }}</span></h2></div><div class="card-content"><div class="show-cards">{% for item in upcoming %}<div class="show-card"><div class="show-poster"><a href="{{ item.indexer_id|show_link(item.show_id) }}"><img src="{{ item.image }}" alt="{{ item.show_name }}" loading="lazy" decoding="async"><div class="show-date">{{ item.airdate|format_date }}</div></a></div><div class="show-info"><h3 title="{{ item.show_name }}">{{ item.show_name }}</h3></div></div>{% endfor %}</div></div></div>
{% endif %}
</div></div>
<script>
function setDashboardSection(button, expanded){
  var card = button.closest('.card');
  var content = card && card.querySelector('.card-content');
  if(!content) return;
  content.hidden = !expanded;
  button.setAttribute('aria-expanded', String(expanded));
  var label = expanded ? 'Replier la section' : 'Déplier la section';
  button.setAttribute('aria-label', label);
  button.title = label;
}

function dashboardSectionKey(button){
  return 'sickshift:section:' + window.location.pathname + ':' + button.closest('.card').id;
}

function toggleDashboardSection(button){
  var expanded = button.getAttribute('aria-expanded') !== 'true';
  setDashboardSection(button, expanded);
  try { localStorage.setItem(dashboardSectionKey(button), String(expanded)); } catch(e) {}
}

document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.section-toggle').forEach(function(button){
    var expanded = true;
    try { expanded = localStorage.getItem(dashboardSectionKey(button)) !== 'false'; } catch(e) {}
    setDashboardSection(button, expanded);
  });
});

function toggleMissingAccordion(headerEl){
  var card = headerEl.closest('.missing-card');
  if(!card) return;
  var list = card.querySelector('.missing-episodes-list');
  if(!list) return;
  var isHidden = list.style.display === 'none' || list.style.display === '';
  list.style.display = isHidden ? 'flex' : 'none';
  card.classList.toggle('expanded', isHidden);
}

function copyMissingEp(e, el, text){
  if(e) e.stopPropagation();
  if(!text) return;
  var row = el.closest ? (el.closest('.missing-ep-item') || el.closest('.missing-info') || el) : el;
  function markSuccess(){
    if(row){
      row.classList.add('copied');
      setTimeout(function(){ row.classList.remove('copied'); }, 1200);
    }
  }
  if(navigator.clipboard && window.isSecureContext){
    navigator.clipboard.writeText(text).then(markSuccess).catch(function(){ fallbackCopy(text); });
  } else {
    fallbackCopy(text);
  }
  function fallbackCopy(str){
    try {
      var ta = document.createElement('textarea');
      ta.value = str;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      ta.style.pointerEvents = 'none';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      var ok = document.execCommand('copy');
      document.body.removeChild(ta);
      if(ok) markSuccess();
    } catch(err){}
  }
}

document.addEventListener('DOMContentLoaded',function(){
 document.querySelectorAll('.show-row').forEach(function(row){
  var url = row.getAttribute('data-href') || (row.querySelector('a') && row.querySelector('a').getAttribute('href'));
  row.style.cursor = 'pointer';
  var holdTimer = null;
  var isHold = false;
  row.addEventListener('mousedown', function(e){
   isHold = false;
   clearTimeout(holdTimer);
   holdTimer = setTimeout(function(){
    isHold = true;
   }, 200);
  });
  row.addEventListener('mouseup', function(e){
   clearTimeout(holdTimer);
  });
  row.addEventListener('mouseenter', function(){
   document.querySelectorAll('.show-row.selected').forEach(function(r){ r.classList.remove('selected'); });
   row.classList.add('selected');
  });
  row.addEventListener('click', function(e){
   document.querySelectorAll('.show-row.selected').forEach(function(r){ r.classList.remove('selected'); });
   row.classList.add('selected');
   if(e.target.closest('a')) return;
   if(isHold || (window.isEpPreviewShowing && window.isEpPreviewShowing())) {
    e.preventDefault();
    e.stopPropagation();
    return;
   }
   if(url) window.location.href = url;
  });
 });
});
</script>
<script>
(()=>{
  function updateDeviceLayout(){
    var w = window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth;
    var dev = 'desktop';
    if(w <= 680){ dev = 'mobile'; }
    else if(w <= 1024){ dev = 'tablet'; }
    else{ dev = 'desktop'; }
    document.documentElement.setAttribute('data-device', dev);
    document.body.classList.remove('device-desktop', 'device-tablet', 'device-mobile');
    document.body.classList.add('device-' + dev);
  }
  window.addEventListener('resize', updateDeviceLayout, {passive: true});
  window.addEventListener('orientationchange', updateDeviceLayout, {passive: true});
  updateDeviceLayout();
  if('serviceWorker' in navigator) navigator.serviceWorker.register('{{ mount_prefix }}/service-worker.js').catch(()=>{});
})();
</script>
<script src="{{ web_root or '' }}/js/lib/jquery-2.2.4.min.js"></script>
<script>window.sbRoot = '{{ web_root or "" }}';</script>
<script src="{{ web_root or '' }}/js/episodePreview.js?v=dash"></script>
<script>
function triggerGlobalScanRename() {
  window.location.href = (window.sbRoot || '') + '/home/scan-and-rename';
}
$(function() {
  var $heroBtn = $('#hero-preview-btn');
  if ($heroBtn.length) {
    var $firstRow = $('#sec-to-watch .show-row').first();
    if ($firstRow.length) {
      $heroBtn.on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        if (window.triggerEpisodePreview) {
          var rect = this.getBoundingClientRect();
          window.triggerEpisodePreview($firstRow[0], rect.left + 20, rect.bottom + 12);
        }
      });
    }
  }
});
</script>
</body>
</html>'''


TEMPLATE_STRING_MINI = r'''<!DOCTYPE html>
<html lang="{{ lang|default('fr') }}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<link rel="manifest" href="{{ mount_prefix }}/manifest.webmanifest">
<meta name="theme-color" content="#0a0a0f">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>{{ t.title_mini }}</title>
<link rel="icon" type="image/x-icon" href="{{ web_root or '' }}/images/ico/favicon.ico">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
:root{--bg-primary:#000;--bg-secondary:#13131a;--bg-tertiary:#1a1a24;--bg-card:#16161f;--bg-hover:#1d1d28;--border-subtle:#252530;--border-light:#2a2a38;--text-primary:#e8e8f0;--text-secondary:#a8a8b8;--accent-blue:#4a9eff;--accent-cyan:#3dd9eb;--shadow-sm:0 1px 3px rgba(0,0,0,.3);--shadow-md:0 4px 12px rgba(0,0,0,.4);--shadow-lg:0 8px 24px rgba(0,0,0,.5);--transition-fast:150ms cubic-bezier(.4,0,.2,1);--transition-base:250ms cubic-bezier(.4,0,.2,1);--card-border-radius:10px}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:0;padding:0;background:linear-gradient(135deg,#0a0a0f 0%,#13131a 50%,#0f0f16 100%);background-attachment:fixed;min-height:100vh;color:var(--text-primary);line-height:1.4;-webkit-font-smoothing:antialiased}
body::before{content:'';position:fixed;top:0;left:0;right:0;bottom:0;background-image:url("{{ bg_file|default('') }}");background-repeat:no-repeat;background-position:center;background-size:cover;opacity:.03;z-index:-1}
.content-wrapper{width:100%;max-width:720px;margin:0 auto;min-height:100vh;padding:.6rem .6rem calc(1rem + env(safe-area-inset-bottom));display:flex;flex-direction:column}
.page-precedente{margin-bottom:.6rem}
.page-precedente a{color:var(--text-secondary);text-decoration:none;font-size:.82rem;font-weight:500;transition:var(--transition-base);display:inline-flex;align-items:center;gap:.35rem;padding:.4rem .75rem;border-radius:7px;border:1px solid var(--border-subtle);background:var(--bg-secondary)}
.page-precedente a::before{content:none !important;display:none !important}
.page-precedente a:hover{color:var(--accent-cyan);border-color:var(--accent-cyan);background:var(--bg-tertiary);transform:translateX(-2px)}
.card{background:var(--bg-card);border-radius:var(--card-border-radius);border:1px solid var(--border-subtle);margin:0;overflow:hidden;box-shadow:var(--shadow-md);transition:var(--transition-base)}
.card-header{padding:10px 14px;border-bottom:1px solid var(--border-subtle);background:linear-gradient(180deg,var(--bg-secondary) 0%,var(--bg-card) 100%);text-align:center}
.card-header h2{margin:0;color:var(--accent-cyan);font-weight:500;font-size:1.1rem}.card-header h2::before{content:none}
.section-toggle{display:inline-flex;align-items:center;justify-content:center;width:26px;height:28px;padding:3px;border:0;background:transparent;color:var(--accent-cyan);cursor:pointer;flex-shrink:0;vertical-align:middle}
.section-toggle svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round;transition:transform .15s}
.section-toggle[aria-expanded="false"] svg{transform:rotate(180deg)}
.section-toggle:focus-visible{outline:2px solid var(--accent-cyan);border-radius:4px}
.card-content[hidden]{display:none!important}

.card-content{padding:8px}

.missing-container{display:flex;flex-direction:column;gap:8px;max-width:650px;margin:0 auto}
.missing-card{background:var(--bg-secondary);border:1px solid var(--border-subtle);border-radius:8px;overflow:hidden;transition:border-color .2s ease, box-shadow .2s ease}
.missing-card:hover{border-color:#3dd9eb;box-shadow:0 0 14px rgba(61,217,235,0.25)}
.missing-header{display:flex;align-items:center;padding:7px 10px;gap:10px;cursor:pointer;user-select:none}
.missing-header:hover{background-color:var(--bg-hover)}
.missing-thumb-link{display:flex;align-items:center;flex-shrink:0;text-decoration:none}
.missing-info{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.missing-title-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.missing-show-title, .missing-info > .missing-title-row > .missing-ep-text{color:var(--text-primary);font-size:.9rem;font-weight:600;word-break:break-word}
.missing-info > .missing-title-row > .missing-ep-text > span{font-family:inherit;font-size:inherit;font-weight:inherit}

.missing-ep-badge{font-size:.74rem;font-weight:700;padding:2px 7px;border-radius:999px;background:rgba(61,217,235,.15);color:var(--accent-cyan);border:1px solid rgba(61,217,235,.3)}
.missing-chevron{color:var(--accent-cyan);font-size:.72rem;transition:transform .2s ease;margin-left:auto;flex-shrink:0}
.missing-card.expanded .missing-chevron{transform:rotate(180deg)}
.missing-episodes-list{border-top:1px solid var(--border-subtle);background:rgba(10,10,15,.4);padding:6px 10px 8px 55px;display:flex;flex-direction:column;gap:4px}
.missing-ep-item{display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:.88rem;color:var(--text-primary);padding:5px 8px;border-radius:5px;border-bottom:1px solid rgba(255,255,255,0.03);cursor:pointer;transition:background-color .15s ease, color .15s ease}
.missing-ep-item:last-child{border-bottom:none}
.missing-ep-item:hover{background:rgba(255,255,255,0.05)}
.missing-ep-item:hover .missing-ep-text{color:var(--accent-cyan)}
.missing-ep-text{font-weight:500;color:var(--text-primary);word-break:break-word;user-select:text}
.missing-ep-item.copied, .missing-info.copied{background:rgba(16,185,129,0.14) !important;color:#10b981 !important}
.missing-ep-item.copied .missing-ep-text, .missing-ep-item.copied .missing-ep-main, .missing-ep-item.copied .missing-ep-title,
.missing-info.copied .missing-ep-text, .missing-info.copied .missing-ep-main, .missing-info.copied .missing-ep-title{color:#10b981 !important}
.copied-pill{display:none;font-size:.74rem;font-weight:600;color:#10b981;background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.35);padding:2px 8px;border-radius:4px;margin-left:auto;flex-shrink:0;user-select:none}
.missing-ep-item.copied .copied-pill, .missing-info.copied .copied-pill{display:inline-block}

.show-thumbnail{
  width:38px;height:56px;border-radius:5px;object-fit:cover;display:block;
  border:1px solid var(--border-subtle);box-shadow:var(--shadow-sm);
  transition:transform 250ms cubic-bezier(.4,0,.2,1), border-color 250ms cubic-bezier(.4,0,.2,1), box-shadow 250ms cubic-bezier(.4,0,.2,1);
}
.show-thumbnail:hover{
  transform:scale(1.7);z-index:100;position:relative;
  border-color:var(--border-light) !important;
  box-shadow:0 4px 14px rgba(0,0,0,.75) !important;
}

::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border-subtle);border-radius:3px}::-webkit-scrollbar-thumb:hover{background:var(--border-light)}
</style>
</head>
<body>
<div class="content-wrapper">
<div class="page-precedente"><a href="{{ mount_prefix or '/' }}">{{ t.btn_home }}</a></div>
<div class="card" id="sec-missing">
<div class="card-header"><h2><button type="button" class="section-toggle" aria-expanded="true" aria-label="Replier la section" title="Replier la section" onclick="toggleDashboardSection(this)"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 15 6-6 6 6"/></svg></button> {{ t.sec_missing }} ({{ missing|length }})</h2></div>
<div class="card-content">
{% if missing_groups %}
<div class="missing-container">
{% for group in missing_groups %}
{% set m_link = group.indexer_id|show_link(group.show_id) %}
{% if group.episodes|length > 1 %}
<div class="missing-card">
  <div class="missing-header" onclick="toggleMissingAccordion(this)">
    <a href="{{ m_link }}" class="missing-thumb-link" onclick="event.stopPropagation()" title="{{ group.show_name }}"><img src="{{ group.thumbnail or '' }}" class="show-thumbnail" alt="{{ group.show_name }}" loading="lazy" decoding="async"></a>
    <div class="missing-info">
      <div class="missing-title-row">
        <span class="missing-show-title">{{ group.show_name }}</span>
        <span class="missing-ep-badge">{{ group.episodes|length }} {{ t.episodes_missing|default('missing episodes') }}</span>
      </div>
    </div>
    <span class="missing-chevron">▼</span>
  </div>
  <div class="missing-episodes-list" style="display:none;">
    {% for ep in group.episodes %}
    <div class="missing-ep-item" onclick="copyMissingEp(event, this, '{{ ep.missing|escape }}')" title="{{ t.btn_copy|default('Copier') }} : {{ ep.missing }}">
      <span class="missing-ep-text"><span class="missing-ep-main">{{ ep.missing }}</span>{% if ep.ep_name %}<span class="missing-ep-sep"> - </span><span class="missing-ep-title">{{ ep.ep_name }}</span>{% endif %}</span>
      <span class="copied-pill">✓ {{ t.copied|default('Copié !') }}</span>
    </div>
    {% endfor %}
  </div>
</div>
{% else %}
<div class="missing-card">
  <div class="missing-header" style="cursor:default">
    <a href="{{ m_link }}" class="missing-thumb-link" title="{{ group.show_name }}"><img src="{{ group.thumbnail or '' }}" class="show-thumbnail" alt="{{ group.show_name }}" loading="lazy" decoding="async"></a>
    <div class="missing-info" onclick="copyMissingEp(event, this, '{{ group.episodes[0].missing|escape }}')" style="cursor:pointer" title="{{ t.btn_copy|default('Copier') }} : {{ group.episodes[0].missing }}">
      <div class="missing-title-row" style="justify-content:space-between;width:100%">
        <span class="missing-ep-text"><span class="missing-ep-main">{{ group.episodes[0].missing }}</span>{% if group.episodes[0].ep_name %}<span class="missing-ep-sep"> - </span><span class="missing-ep-title">{{ group.episodes[0].ep_name }}</span>{% endif %}</span>
        <span class="copied-pill">✓ {{ t.copied|default('Copié !') }}</span>
      </div>
    </div>
  </div>
</div>
{% endif %}
{% endfor %}
</div>
{% else %}
<div style="text-align:center;padding:1rem;color:var(--text-primary);font-size:1rem;">{{ t.all_shows_up_to_date|default('All shows are up to date') }}</div>
{% endif %}
</div>
</div>
</div>
<script>
function setDashboardSection(button, expanded){
  var card = button.closest('.card');
  var content = card && card.querySelector('.card-content');
  if(!content) return;
  content.hidden = !expanded;
  button.setAttribute('aria-expanded', String(expanded));
  var label = expanded ? 'Replier la section' : 'Déplier la section';
  button.setAttribute('aria-label', label);
  button.title = label;
}

function dashboardSectionKey(button){
  return 'sickshift:section:' + window.location.pathname + ':' + button.closest('.card').id;
}

function toggleDashboardSection(button){
  var expanded = button.getAttribute('aria-expanded') !== 'true';
  setDashboardSection(button, expanded);
  try { localStorage.setItem(dashboardSectionKey(button), String(expanded)); } catch(e) {}
}

document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.section-toggle').forEach(function(button){
    var expanded = true;
    try { expanded = localStorage.getItem(dashboardSectionKey(button)) !== 'false'; } catch(e) {}
    setDashboardSection(button, expanded);
  });
});

function toggleMissingAccordion(headerEl){
  var card = headerEl.closest('.missing-card');
  if(!card) return;
  var list = card.querySelector('.missing-episodes-list');
  if(!list) return;
  var isHidden = list.style.display === 'none' || list.style.display === '';
  list.style.display = isHidden ? 'flex' : 'none';
  card.classList.toggle('expanded', isHidden);
}

function copyMissingEp(e, el, text){
  if(e) e.stopPropagation();
  if(!text) return;
  var row = el.closest ? (el.closest('.missing-ep-item') || el.closest('.missing-info') || el) : el;
  function markSuccess(){
    if(row){
      row.classList.add('copied');
      setTimeout(function(){ row.classList.remove('copied'); }, 1200);
    }
  }
  if(navigator.clipboard && window.isSecureContext){
    navigator.clipboard.writeText(text).then(markSuccess).catch(function(){ fallbackCopy(text); });
  } else {
    fallbackCopy(text);
  }
  function fallbackCopy(str){
    try {
      var ta = document.createElement('textarea');
      ta.value = str;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      ta.style.pointerEvents = 'none';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      var ok = document.execCommand('copy');
      document.body.removeChild(ta);
      if(ok) markSuccess();
    } catch(err){}
  }
}
(()=>{
  function updateDeviceLayout(){
    var w = window.innerWidth || document.documentElement.clientWidth || document.body.clientWidth;
    var dev = 'desktop';
    if(w <= 680){ dev = 'mobile'; }
    else if(w <= 1024){ dev = 'tablet'; }
    else{ dev = 'desktop'; }
    document.documentElement.setAttribute('data-device', dev);
    document.body.classList.remove('device-desktop', 'device-tablet', 'device-mobile');
    document.body.classList.add('device-' + dev);
  }
  window.addEventListener('resize', updateDeviceLayout, {passive: true});
  window.addEventListener('orientationchange', updateDeviceLayout, {passive: true});
  updateDeviceLayout();
  if('serviceWorker' in navigator) navigator.serviceWorker.register('{{ mount_prefix }}/service-worker.js').catch(()=>{});
})();
</script>
<script src="{{ web_root or '' }}/js/lib/jquery-2.2.4.min.js"></script>
<script>window.sbRoot = '{{ web_root or "" }}';</script>
<script src="{{ web_root or '' }}/js/episodePreview.js?v=dash"></script>
<script>
function triggerGlobalScanRename() {
  window.location.href = (window.sbRoot || '') + '/home/scan-and-rename';
}
$(function() {
  var $heroBtn = $('#hero-preview-btn');
  if ($heroBtn.length) {
    var $firstRow = $('#sec-to-watch .show-row').first();
    if ($firstRow.length) {
      $heroBtn.on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        if (window.triggerEpisodePreview) {
          var rect = this.getBoundingClientRect();
          window.triggerEpisodePreview($firstRow[0], rect.left + 20, rect.bottom + 12);
        }
      });
    }
  }
});
</script>
</body>
</html>'''


def safe_parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    value = str(value).strip()
    if not value:
        return None

    for fmt in ("%Y-%m-%d %H:%M", "%Y%m%d%H%M", "%Y%m%d", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


class TemplateEngine:
    def __init__(self, config: Settings):
        self.config = config
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(enabled_extensions=("html", "xml")),
            optimized=True,
        )
        self.env.filters["format_date"] = self.format_date
        self.env.filters["show_link"] = self.show_link
        self.env.filters["urlencode"] = self.urlencode
        self.env.filters["network_fallback"] = self.network_fallback

        self.main_template: Template = self.env.from_string(TEMPLATE_STRING)
        self.mini_template: Template = self.env.from_string(TEMPLATE_STRING_MINI)

    def format_date(self, value: Any) -> str:
        dt = safe_parse_datetime(value)
        if not dt:
            return str(value or "")

        i18n = get_i18n_context()
        formatter = i18n.get("format_date")
        if formatter and callable(formatter):
            return formatter(dt)
        return f"{dt.day}/{dt.month}/{dt.year}"

    def show_link(self, indexer: Any, show_id: Any) -> str:
        root = (self.config.web_root or self.config.base_url or "").rstrip("/")
        if indexer is None or show_id is None:
            return f"{root}/home/" if root else "/home/"
        return f"{root}/home/view-show?tvid_prodid={indexer}:{show_id}"

    @staticmethod
    def urlencode(value: Any) -> str:
        return urllib.parse.quote(str(value), safe="")

    @staticmethod
    def network_fallback(value: Any) -> str:
        if not value:
            return ""
        return urllib.parse.quote(str(value).lower().replace(" ", ""), safe="")

    def render(self, *, mini: bool = False, **context: Any) -> str:
        root = (self.config.web_root or self.config.base_url or "").rstrip("/")
        i18n = get_i18n_context()
        context.setdefault("web_root", root)
        context.setdefault("base_url", root)
        context.setdefault("mount_prefix", self.config.mount_prefix)
        context.setdefault("lang", i18n["lang"])
        context.setdefault("t", i18n["t"])
        template = self.mini_template if mini else self.main_template
        return template.render(**context)
