"""Importeur catalogue oski.module pour le store apps.odooskills.com.

Idempotent (clé = technical_name). Lit chaque module oski_* de content/apps/{free,pro},
construit la fiche oski.module + une version 19.0 (.zip en ir.attachment) + icône +
captures, en gardant is_published=False. À lancer via odoo-bin shell.

Usage (shell):  exec(open(".../import_catalog.py").read())
Variables d'env optionnelles : OSKI_ROOT (racine repo), OSKI_ONLY (csv technical_names).
"""
import ast
import base64
import os
import zipfile

ROOT = os.environ.get("OSKI_ROOT", "/home/stadev/vscode-projects/odoo19-dev")
ONLY = set(filter(None, os.environ.get("OSKI_ONLY", "").split(",")))
APPS = [("free", "LGPL-3"), ("pro", "OPL-1")]

_EXCLUDED_DIRS = {".git", "__pycache__", ".idea", ".pytest_cache"}
_EXCLUDED_EXT = (".pyc", ".pyo")

# Map mot-clé catégorie manifest -> xmlid catégorie store
_CAT_MAP = [
    (("sale", "crm", "vente"), "cat_sales"),
    (("account", "invoic", "financ", "compta"), "cat_accounting"),
    (("hr", "human", "employee", "recruit", "ressource"), "cat_hr"),
    (("website", "ecommerce", "e-commerce", "site", "portal", "appointment"), "cat_website"),
    (("project", "manufactur", "mrp", "productivity", "planning", "quality",
      "plm", "subscription", "helpdesk", "gantt", "stock", "inventory",
      "purchase", "document"), "cat_productivity"),
]


def build_module_zip(module_path, output_path):
    module_path = os.path.abspath(module_path.rstrip(os.sep))
    parent = os.path.dirname(module_path)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(module_path):
            dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
            for fname in files:
                if fname.endswith(_EXCLUDED_EXT):
                    continue
                abspath = os.path.join(root, fname)
                relpath = os.path.relpath(abspath, parent)
                zf.write(abspath, relpath)
    return output_path


def read_manifest(path):
    with open(path, "r", encoding="utf-8") as f:
        return ast.literal_eval(f.read())


def category_xmlid(env, manifest_cat):
    low = (manifest_cat or "").lower()
    for keys, xid in _CAT_MAP:
        if any(k in low for k in keys):
            return xid
    return "cat_technical"


def b64file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read())


Module = env["oski.module"].sudo()
Version = env["oski.module.version"].sudo()
Attach = env["ir.attachment"].sudo()
ov19 = env["oski.odoo.version"].sudo().search([("name", "=", "19.0")], limit=1)
if not ov19:
    ov19 = env["oski.odoo.version"].sudo().create({"name": "19.0", "sequence": 190})

created, updated, skipped, errors = [], [], [], []

for sub, default_license in APPS:
    base = os.path.join(ROOT, "content", "apps", sub)
    if not os.path.isdir(base):
        continue
    for tech in sorted(os.listdir(base)):
        if not tech.startswith("oski_") or tech == "oski_app_store":
            continue
        if ONLY and tech not in ONLY:
            continue
        mdir = os.path.join(base, tech)
        manifest_path = os.path.join(mdir, "__manifest__.py")
        if not os.path.isfile(manifest_path):
            continue
        try:
            man = read_manifest(manifest_path)
            descdir = os.path.join(mdir, "static", "description")
            index_html = os.path.join(descdir, "index.html")
            description_html = False
            if os.path.isfile(index_html):
                with open(index_html, "r", encoding="utf-8") as f:
                    description_html = f.read()

            raw_lic = (man.get("license") or default_license).upper()
            price = man.get("price", 0.0) or 0.0
            is_free = (sub == "free") or (raw_lic in ("LGPL-3", "AGPL-3", "GPL-3")) or price == 0.0
            lic = {"LGPL-3": "lgpl-3", "OPL-1": "opl-1"}.get(raw_lic, "other")

            vals = {
                "name": man.get("name", tech),
                "technical_name": tech,
                "summary": man.get("summary") or False,
                "description_html": description_html,
                "category_id": env.ref("oski_app_store.%s" % category_xmlid(env, man.get("category"))).id,
                "license": lic,
                "is_free": is_free,
                "author": man.get("author") or "OdooSkills",
            }

            # icône
            icon = os.path.join(descdir, "icon.png")
            if os.path.isfile(icon):
                vals["image_1920"] = b64file(icon)

            rec = Module.search([("technical_name", "=", tech)], limit=1)
            if rec:
                rec.write(vals)
                updated.append(tech)
            else:
                rec = Module.create({**vals, "is_published": False})
                created.append(tech)

            # captures -> attachments publics
            shots = sorted(
                f for f in os.listdir(descdir)
                if f.lower().startswith("screenshot") and f.lower().endswith((".png", ".jpg", ".jpeg"))
            ) if os.path.isdir(descdir) else []
            att_ids = []
            shot_by_file = {}
            for s in shots:
                name = "%s/%s" % (tech, s)
                a = Attach.search([("name", "=", name), ("res_model", "=", "oski.module"),
                                   ("res_id", "=", rec.id)], limit=1)
                data = b64file(os.path.join(descdir, s))
                if a:
                    a.write({"datas": data, "public": True})
                else:
                    a = Attach.create({
                        "name": name, "datas": data, "public": True,
                        "res_model": "oski.module", "res_id": rec.id,
                        "mimetype": "image/png",
                    })
                att_ids.append(a.id)
                shot_by_file[s] = a.id
            if att_ids:
                rec.write({"screenshot_ids": [(6, 0, att_ids)]})

            # Réécrit les <img src="screenshot_NN.png"> (relatifs, cassés sur le store)
            # vers l'URL publique de l'attachment /web/image/<id>.
            if description_html and shot_by_file:
                new_html = description_html
                for fname, att_id in shot_by_file.items():
                    new_html = new_html.replace(
                        'src="%s"' % fname, 'src="/web/image/%s"' % att_id
                    ).replace(
                        'src="./%s"' % fname, 'src="/web/image/%s"' % att_id
                    )
                if new_html != description_html:
                    rec.write({"description_html": new_html})

            # zip version 19.0
            zip_path = "/tmp/oski_%s.zip" % tech
            build_module_zip(mdir, zip_path)
            zname = "%s-19.0.zip" % tech
            za = Attach.search([("name", "=", zname), ("res_model", "=", "oski.module.version")], limit=1)
            zvals = {"name": zname, "datas": b64file(zip_path), "mimetype": "application/zip"}
            if za:
                za.write(zvals)
            else:
                za = Attach.create({**zvals, "res_model": "oski.module.version"})
            os.remove(zip_path)

            ver = Version.search([("module_id", "=", rec.id), ("odoo_version", "=", "19.0")], limit=1)
            vvals = {
                "module_id": rec.id,
                "odoo_version_id": ov19.id,
                "odoo_version": "19.0",
                "module_version": man.get("version", "19.0.1.0.0"),
                "attachment_id": za.id,
            }
            if ver:
                ver.write(vvals)
            else:
                Version.create(vvals)

        except Exception as e:
            errors.append("%s: %s" % (tech, e))

env.cr.commit()
print("=== IMPORT CATALOG ===")
print("created:", len(created))
print("updated:", len(updated))
print("errors :", len(errors))
for e in errors:
    print("  !", e)
print("total oski.module:", Module.search_count([]))
print("published=True count (doit etre 0):", Module.search_count([("is_published", "=", True)]))
