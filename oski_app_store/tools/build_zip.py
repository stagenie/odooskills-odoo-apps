"""Empaquette un module Odoo (content/apps/{free,pro}) en archive .zip.

Le zip contient le dossier du module à la racine (préfixe = nom du module),
ce qui permet une décompression directe dans un addons_path.
"""
import os
import zipfile

_EXCLUDED_DIRS = {".git", "__pycache__", ".idea", ".pytest_cache"}
_EXCLUDED_EXT = (".pyc", ".pyo")


def build_module_zip(module_path, output_path):
    """Crée `output_path` (.zip) à partir du dossier `module_path`.

    Raises:
        ValueError: si `module_path` ne contient pas de __manifest__.py.
    """
    module_path = os.path.abspath(module_path.rstrip(os.sep))
    parent = os.path.dirname(module_path)
    if not os.path.isfile(os.path.join(module_path, "__manifest__.py")):
        raise ValueError("Pas de __manifest__.py dans %s" % module_path)

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
