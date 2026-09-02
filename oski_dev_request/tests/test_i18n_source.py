"""La source du module est en anglais ; le français vit dans i18n/fr.po."""
import os
import re

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Mots-outils français qui n'apparaissent pas dans une source anglaise.
FRENCH = re.compile(r"\b(le|la|les|des|une|est|pour|avec|vous|votre|aucun|aucune)\b", re.I)


def _texts(path):
    """Chaînes visibles d'un fichier XML/Python : attributs string/help et nœuds texte."""
    src = open(path, encoding="utf-8").read()
    if path.endswith(".py"):
        return re.findall(r'(?:string|help)\s*=\s*"([^"]*)"', src) + re.findall(r'_\("([^"]*)"\)', src)
    body = re.sub(r"<!--.*?-->", "", src, flags=re.S)
    return re.findall(r'(?:string|help|placeholder|title|alt)="([^"]*)"', body) + \
        re.findall(r">([^<>{}]+)<", body)


@tagged("post_install", "-at_install")
class TestI18nSource(TransactionCase):

    def test_no_french_in_source(self):
        offenders = []
        for sub in ("models", "views", "controllers", "templates", "data", "security"):
            folder = os.path.join(ROOT, sub)
            for name in sorted(os.listdir(folder)):
                if not name.endswith((".py", ".xml")):
                    continue
                for text in _texts(os.path.join(folder, name)):
                    if len(FRENCH.findall(text)) >= 2:
                        offenders.append("%s/%s: %s" % (sub, name, text.strip()[:60]))
        self.assertFalse(offenders, "Français dans la source :\n" + "\n".join(offenders))
