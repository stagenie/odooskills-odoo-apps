"""Génère des icônes de marque (tuile plum + glyphe blanc par famille) pour les
modules oski_* qui n'ont pas de static/description/icon.png. Rendu via Playwright.
"""
import os
from playwright.sync_api import sync_playwright

ROOT = "/home/stadev/vscode-projects/odoo19-dev"
SUBS = ["free", "pro"]
ONLY_MISSING = os.environ.get("OSKI_ALL") != "1"

# Glyphes feather-style (paths SVG, viewBox 24x24, stroke courant).
G = {
    "lock": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>',
    "clipboard": '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M9 14l2 2 4-4"/>',
    "bars": '<line x1="6" y1="20" x2="6" y2="13"/><line x1="12" y1="20" x2="12" y2="8"/><line x1="18" y1="20" x2="18" y2="11"/><line x1="3" y1="20" x2="21" y2="20"/>',
    "refresh": '<path d="M21 12a9 9 0 1 1-3-6.7"/><polyline points="21 3 21 9 15 9"/>',
    "merge": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="12" r="3"/><path d="M9 6h3a3 3 0 0 1 3 3v0M9 18h3a3 3 0 0 0 3-3v0"/>',
    "buoy": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.5"/><line x1="5" y1="5" x2="9.5" y2="9.5"/><line x1="14.5" y1="14.5" x2="19" y2="19"/><line x1="19" y1="5" x2="14.5" y2="9.5"/><line x1="9.5" y1="14.5" x2="5" y2="19"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="16" y1="2" x2="16" y2="6"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 12 12 17 22 12"/><polyline points="2 17 12 22 22 17"/>',
    "box": '<path d="M21 8v8a2 2 0 0 1-1 1.7l-7 4a2 2 0 0 1-2 0l-7-4A2 2 0 0 1 3 16V8a2 2 0 0 1 1-1.7l7-4a2 2 0 0 1 2 0l7 4A2 2 0 0 1 21 8z"/><polyline points="3.3 7 12 12 20.7 7"/><line x1="12" y1="22" x2="12" y2="12"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="14" y2="17"/>',
    "cart": '<circle cx="9" cy="21" r="1.5"/><circle cx="18" cy="21" r="1.5"/><path d="M2 3h3l2.7 12.4a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.6L23 7H6"/>',
    "columns": '<rect x="3" y="3" width="5" height="18" rx="1"/><rect x="10" y="3" width="5" height="12" rx="1"/><rect x="17" y="3" width="4" height="16" rx="1"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
    "qr": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><line x1="14" y1="14" x2="14" y2="21"/><line x1="18" y1="14" x2="21" y2="14"/><line x1="21" y1="18" x2="21" y2="21"/>',
    "archive": '<rect x="3" y="3" width="18" height="5" rx="1"/><path d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8"/><line x1="10" y1="12" x2="14" y2="12"/>',
    "copy": '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "palette": '<circle cx="12" cy="12" r="9"/><circle cx="8" cy="9" r="1.2" fill="white" stroke="none"/><circle cx="12" cy="7.5" r="1.2" fill="white" stroke="none"/><circle cx="16" cy="9" r="1.2" fill="white" stroke="none"/><path d="M12 21a3 3 0 0 0 0-6 2 2 0 0 1 0-4"/>',
    "wrench": '<path d="M14.7 6.3a4 4 0 0 1-5 5L4 17v3h3l5.7-5.7a4 4 0 0 0 5-5l-2.3 2.3-2.4-.6-.6-2.4z"/>',
    "spark": '<path d="M12 3l1.8 4.6L18.5 9l-4.7 1.4L12 15l-1.8-4.6L5.5 9l4.7-1.4z"/><path d="M19 14l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z"/>',
    "monitor": '<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>',
    "receipt": '<path d="M5 3h14v18l-2.5-1.5L14 21l-2-1.5L10 21l-2.5-1.5L5 21z"/><line x1="8" y1="8" x2="16" y2="8"/><line x1="8" y1="12" x2="16" y2="12"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
}

# (mots-clés, glyphe) — ordre = priorité (spécifique d'abord).
RULES = [
    (("approval", "approbation"), "shield"),
    (("quality",), "clipboard"),
    (("gantt",), "bars"),
    (("subscription", "renewal", "renouvel"), "refresh"),
    (("merge", "fusion"), "merge"),
    (("helpdesk",), "buoy"),
    (("appointment", "planning", "rendez"), "calendar"),
    (("plm",), "layers"),
    (("intercompany", "inter_company", "inter-soc"), "layers"),
    (("cost_margin", "masquage", "margin"), "lock"),
    (("security", "access", "securite", "restrict"), "lock"),
    (("qr", "vcard"), "qr"),
    (("archive",), "archive"),
    (("duplicate", "doublon"), "copy"),
    (("row_color", "list_row", "color"), "palette"),
    (("dev_request", "request"), "wrench"),
    (("login", "branding"), "spark"),
    (("pos", "shop"), "monitor"),
    (("invoice", "account", "facture", "comment_template"), "receipt"),
    (("purchase", "achat"), "cart"),
    (("sale", "devis", "order", "vente"), "file"),
    (("stock", "location", "emplacement", "low_alert"), "box"),
    (("project", "task", "checklist"), "columns"),
    (("partner", "category", "portfolio", "team", "contact", "hr", "department"), "users"),
    (("report",), "file"),
]


def glyph_for(tech):
    low = tech.lower()
    for keys, g in RULES:
        if any(k in low for k in keys):
            return G[g]
    return G["grid"]


def html_for(tech):
    glyph = glyph_for(tech)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    html,body{{margin:0;padding:0;background:transparent}}
    .tile{{width:512px;height:512px;border-radius:108px;
      background:radial-gradient(130% 130% at 28% 18%, #7d5170 0%, #5a3c52 48%, #21112E 100%);
      display:flex;align-items:center;justify-content:center;position:relative;
      box-shadow:inset 0 0 0 2px rgba(255,255,255,.06);}}
    .tile::after{{content:"";position:absolute;right:-30%;bottom:-40%;width:70%;height:70%;
      background:radial-gradient(circle, rgba(232,160,191,.30) 0%, transparent 60%);}}
    svg{{width:248px;height:248px;stroke:#fff;stroke-width:1.7;fill:none;
      stroke-linecap:round;stroke-linejoin:round;position:relative;z-index:1;
      filter:drop-shadow(0 6px 14px rgba(0,0,0,.25));}}
    </style></head><body>
    <div class="tile"><svg viewBox="0 0 24 24">{glyph}</svg></div>
    </body></html>"""


def main():
    targets = []
    for sub in SUBS:
        base = os.path.join(ROOT, "content", "apps", sub)
        if not os.path.isdir(base):
            continue
        for tech in sorted(os.listdir(base)):
            if not tech.startswith("oski_") or tech == "oski_app_store":
                continue
            descdir = os.path.join(base, tech, "static", "description")
            icon = os.path.join(descdir, "icon.png")
            if not os.path.isfile(os.path.join(base, tech, "__manifest__.py")):
                continue
            if ONLY_MISSING and os.path.isfile(icon):
                continue
            targets.append((tech, descdir, icon))

    print("icônes à générer:", len(targets))
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 512, "height": 512}, device_scale_factor=1)
        for tech, descdir, icon in targets:
            os.makedirs(descdir, exist_ok=True)
            pg.set_content(html_for(tech), wait_until="load")
            pg.wait_for_timeout(120)
            el = pg.query_selector(".tile")
            el.screenshot(path=icon, omit_background=True)
        b.close()
    print("généré:", len(targets))
    for tech, _, _ in targets[:8]:
        print("  ", tech, "->", glyph_for(tech)[:0] or "ok")


main()
