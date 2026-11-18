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
class TestI18n(TransactionCase):

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

    def test_fr_po_complete(self):
        po = open(os.path.join(ROOT, "i18n", "fr.po"), encoding="utf-8").read()
        pot = open(os.path.join(ROOT, "i18n", "oski_module_feedback.pot"), encoding="utf-8").read()
        msgids = set(re.findall(r'^msgid "(.+)"$', pot, re.M))
        empty = re.findall(r'^msgid "(.+)"\nmsgstr ""\n\n', po + "\n\n", re.M)
        self.assertTrue(msgids)
        self.assertFalse(empty, "msgstr vides : %s" % empty[:5])
        missing = [m for m in msgids if 'msgid "%s"' % m not in po]
        self.assertFalse(missing, "absents de fr.po : %s" % missing[:5])

    def test_ack_subject_in_french(self):
        from .common import feedback_vals, make_store_data
        make_store_data(self)
        self.env["res.lang"]._activate_lang("fr_FR")
        self.env["ir.module.module"]._load_module_terms(["oski_module_feedback"], ["fr_FR"], overwrite=True)
        self.portal_user.partner_id.lang = "fr_FR"
        rec = self.env["oski.module.feedback"].create(feedback_vals(self))
        tpl = self.env.ref("oski_module_feedback.mail_template_feedback_ack")
        mail = self.env["mail.mail"].browse(tpl.send_mail(rec.id, force_send=False))
        self.assertIn("Nous avons bien reçu votre demande", mail.subject)
        self.assertIn("Suivre ma demande", mail.body_html)
        fr_state = dict(rec.with_context(lang="fr_FR")._fields["state"]._description_selection(
            rec.with_context(lang="fr_FR").env))
        self.assertEqual(fr_state["done"], "Livrée")
