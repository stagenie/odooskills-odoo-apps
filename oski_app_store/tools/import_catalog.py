"""Importeur catalogue oski.module pour le store apps.odooskills.com.

Idempotent (clé = technical_name). Lit chaque module oski_* de content/apps/{free,pro},
construit la fiche oski.module + une version 19.0 (.zip en ir.attachment) + icône +
captures, en gardant is_published=False. À lancer via odoo-bin shell.

Usage (shell):  exec(open(".../import_catalog.py").read())
Variables d'env optionnelles : OSKI_ROOT (racine repo), OSKI_ONLY (csv technical_names),
OSKI_VERSION (défaut 19.0 : version Odoo importée, nomme le zip <tech>-<NN>.zip et la
ligne oski.module.version ; hors 19.0 la fiche n'est pas touchée et doit déjà exister),
OSKI_REPORT (chemin d'un JSON écrit en fin de script, consommé par publish_check.py).
"""
import ast
import base64
import os
import zipfile

ROOT = os.environ.get("OSKI_ROOT", "/home/stadev/vscode-projects/odoo19-dev")
ONLY = set(filter(None, os.environ.get("OSKI_ONLY", "").split(",")))
APPS = [("free", "LGPL-3"), ("pro", "OPL-1")]
VERSION = os.environ.get("OSKI_VERSION", "19.0")
REPORT = os.environ.get("OSKI_REPORT")

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


# --- pure helpers (testables) ---
def zip_name(tech, nn):
    return "%s-%s.zip" % (tech, nn)


def version_vals(manifest, nn, rec_id, ov_id, att_id):
    return {"module_id": rec_id, "odoo_version_id": ov_id, "odoo_version": nn,
            "module_version": manifest.get("version", "%s.1.0.0" % nn), "attachment_id": att_id}


def fr_translations(payload):
    return {k: payload[k] for k in ("name", "summary", "description_html") if payload.get(k)}


def rewrite_shots(html, shot_by_file):
    if not html or not shot_by_file:
        return html
    new_html = html
    for fname, att_id in shot_by_file.items():
        new_html = new_html.replace(
            'src="%s"' % fname, 'src="/web/image/%s"' % att_id
        ).replace(
            'src="./%s"' % fname, 'src="/web/image/%s"' % att_id
        )
    return new_html
# --- end pure helpers ---


# Le shell odoo-bin hérite de la langue de l'admin connecté (fr_FR en prod) ;
# or un write() sur un champ translate=True ne remplit QUE le slot de la langue
# du contexte courant. On force en_US ici pour que les valeurs "manifeste" du
# catalogue (name/summary/description_html) soient bien posées en en_US.
env = env(context=dict(env.context, lang="en_US"))

Module = env["oski.module"].sudo()
Version = env["oski.module.version"].sudo()
Attach = env["ir.attachment"].sudo()
if VERSION == "19.0":
    ov = env["oski.odoo.version"].sudo().search([("name", "=", "19.0")], limit=1)
    if not ov:
        ov = env["oski.odoo.version"].sudo().create({"name": "19.0", "sequence": 190})
else:
    ov = env["oski.odoo.version"].sudo().search([("name", "=", VERSION)], limit=1)
    if not ov:
        raise SystemExit("oski.odoo.version %s absente : la créer en backend d'abord" % VERSION)

Currency = env["res.currency"].sudo()
_cur_cache = {}


def currency_id(code):
    code = (code or "EUR").upper()
    if code not in _cur_cache:
        c = Currency.with_context(active_test=False).search([("name", "=", code)], limit=1)
        _cur_cache[code] = c.id if c else False
    return _cur_cache[code]


created, updated, skipped, errors = [], [], [], []
report = []

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
            rec = Module.search([("technical_name", "=", tech)], limit=1)

            if VERSION != "19.0" and not rec:
                print("fiche absente pour %s : importer la 19.0 d'abord" % tech)
                continue

            if VERSION == "19.0":
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
                    "price": 0.0 if is_free else price,
                    "currency_id": currency_id(man.get("currency", "EUR")),
                    "author": man.get("author") or "OdooSkills",
                }

                # icône
                icon = os.path.join(descdir, "icon.png")
                if os.path.isfile(icon):
                    vals["image_1920"] = b64file(icon)

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
                new_html = rewrite_shots(description_html, shot_by_file)
                if new_html != description_html:
                    rec.write({"description_html": new_html})

                fr_file = os.path.join(mdir, "i18n", "store_fr.json")
                if os.path.isfile(fr_file):
                    import json
                    with open(fr_file, encoding="utf-8") as fh:
                        fr_payload = json.load(fh)
                    for field, value in fr_translations(fr_payload).items():
                        if field == "description_html":
                            value = rewrite_shots(value, shot_by_file)
                        rec.update_field_translations(
                            field,
                            {"en_US": rec.with_context(lang="en_US")[field] or "", "fr_FR": value},
                        )
                    print("  fiche FR posée (store_fr.json)")

            zip_path = "/tmp/oski_%s_%s.zip" % (tech, VERSION)
            build_module_zip(mdir, zip_path)
            zname = zip_name(tech, VERSION)
            zvals = {
                "name": zname, "datas": b64file(zip_path), "mimetype": "application/zip",
                "res_model": "oski.module", "res_id": rec.id,
            }
            za = Attach.search([("name", "=", zname),
                                 ("res_model", "in", ["oski.module", "oski.module.version"])], limit=1)
            if za:
                za.write(zvals)
            else:
                za = Attach.create(zvals)
            os.remove(zip_path)

            ver = Version.search([("module_id", "=", rec.id), ("odoo_version", "=", VERSION)], limit=1)
            vvals = version_vals(man, VERSION, rec.id, ov.id, za.id)
            if ver:
                ver.write(vvals)
            else:
                ver = Version.create(vvals)

            report.append({
                "technical_name": tech, "id": rec.id, "website_url": rec.website_url,
                "is_free": rec.is_free, "is_published": rec.is_published,
                "versions": {VERSION: {"version_id": ver.id, "attachment_id": za.id}},
            })

        except Exception as e:
            errors.append("%s: %s" % (tech, e))

# --- Passe 2 : dépendances entre modules du catalogue ----------------------
# Scanne TOUS les manifests présents sous OSKI_ROOT (indépendamment
# d'OSKI_ONLY : lecture pure, aucune création de fiche) et pointe
# dependency_ids de chaque fiche existante vers les fiches du catalogue
# citées dans son `depends`. Les dépendances hors catalogue (account,
# mail, …) sont ignorées. Seule la 19.0 porte la fiche : hors 19.0, rien.
if VERSION == "19.0":
    all_depends = {}
    for sub, _lic in APPS:
        base = os.path.join(ROOT, "content", "apps", sub)
        if not os.path.isdir(base):
            continue
        for tech in sorted(os.listdir(base)):
            if not tech.startswith("oski_") or tech == "oski_app_store":
                continue
            manifest_path = os.path.join(base, tech, "__manifest__.py")
            if not os.path.isfile(manifest_path):
                continue
            try:
                all_depends[tech] = read_manifest(manifest_path).get("depends") or []
            except Exception as e:
                errors.append("%s (deps): %s" % (tech, e))

    _by_tech = {
        r.technical_name: r
        for r in Module.search([("technical_name", "in", list(all_depends))])
    }
    deps_linked = 0
    for tech, deps in all_depends.items():
        rec = _by_tech.get(tech)
        if not rec:
            continue
        dep_ids = [_by_tech[d].id for d in deps if d in _by_tech]
        if set(dep_ids) != set(rec.dependency_ids.ids):
            rec.write({"dependency_ids": [(6, 0, dep_ids)]})
            deps_linked += 1
else:
    deps_linked = 0

env.cr.commit()

if REPORT:
    import json
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print("rapport écrit", REPORT)

print("=== IMPORT CATALOG ===")
print("created:", len(created))
print("updated:", len(updated))
print("deps maj:", deps_linked)
print("errors :", len(errors))
for e in errors:
    print("  !", e)
print("total oski.module:", Module.search_count([]))
print("published=True count (doit etre 0):", Module.search_count([("is_published", "=", True)]))
