"""./venv/bin/python -m pytest content/apps/free/oski_app_store/tools/test_import_catalog_helpers.py -q"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _helpers():
    # le script est un script shell Odoo : on n'importe que le bloc pur, délimité par les marqueurs
    src = open(os.path.join(HERE, "import_catalog.py"), encoding="utf-8").read()
    pure = src.split("# --- pure helpers (testables) ---")[1].split("# --- end pure helpers ---")[0]
    ns = {}
    exec(pure, ns)
    return ns


def test_zip_name():
    h = _helpers()
    assert h["zip_name"]("oski_x", "18.0") == "oski_x-18.0.zip"


def test_version_vals_uses_manifest_version():
    h = _helpers()
    vals = h["version_vals"]({"version": "18.0.1.2.0"}, "18.0", 5, 7, 9)
    assert vals == {"module_id": 5, "odoo_version_id": 7, "odoo_version": "18.0", "module_version": "18.0.1.2.0", "attachment_id": 9}


def test_fr_translations_skips_empty():
    h = _helpers()
    assert h["fr_translations"]({"name": "Solde", "summary": "", "description_html": "<p>x</p>", "description": "txt"}) == {"name": "Solde", "description_html": "<p>x</p>"}


def test_rewrite_shots():
    h = _helpers()
    shot_by_file = {"a.png": 7}
    assert h["rewrite_shots"]('<img src="a.png">', shot_by_file) == '<img src="/web/image/7">'
    assert h["rewrite_shots"]('<img src="./a.png">', shot_by_file) == '<img src="/web/image/7">'
    assert h["rewrite_shots"]('<img src="unknown.png">', shot_by_file) == '<img src="unknown.png">'
    assert h["rewrite_shots"]("", shot_by_file) == ""
    assert h["rewrite_shots"]('<img src="a.png">', {}) == '<img src="a.png">'
