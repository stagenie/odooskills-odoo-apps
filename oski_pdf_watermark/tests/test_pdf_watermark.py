from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPdfWatermark(TransactionCase):
    """Le filigrane se décide dans le contexte de rendu ; les tests le lisent
    là, puis vérifient une fois qu'il ressort bien dans le HTML produit."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.ui.view"].create({
            "name": "Rapport d'essai filigrane",
            "type": "qweb",
            "key": "oski_pdf_watermark.test_report",
            "arch": """
                <t t-name="oski_pdf_watermark.test_report">
                    <t t-call="web.html_container">
                        <t t-foreach="docs" t-as="doc">
                            <div class="page"><span t-out="doc.name"/></div>
                        </t>
                    </t>
                </t>
            """,
        })
        cls.report = cls.env["ir.actions.report"].create({
            "name": "Rapport d'essai filigrane",
            "model": "res.partner",
            "report_type": "qweb-html",
            "report_name": "oski_pdf_watermark.test_report",
        })
        cls.company = cls.env["res.partner"].create({
            "name": "Société Essai", "is_company": True})
        cls.person = cls.env["res.partner"].create({
            "name": "Personne Essai", "is_company": False})

    def _rule(self, **values):
        defaults = {
            "name": "Règle", "report_id": self.report.id, "text": "BROUILLON",
        }
        defaults.update(values)
        return self.env["oski.report.watermark"].create(defaults)

    def _watermark(self, records, env=None):
        reports = (env or self.env)["ir.actions.report"]
        return reports._oski_watermark_values(self.report, records.ids)

    def test_a_rule_without_condition_marks_every_print(self):
        self._rule(text="COPIE")
        self.assertEqual(self._watermark(self.company)["text"], "COPIE")
        self.assertEqual(self._watermark(self.person)["text"], "COPIE")

    def test_no_rule_leaves_the_print_bare(self):
        self.assertFalse(self._watermark(self.company))

    def test_the_condition_selects_which_documents_are_marked(self):
        self._rule(filter_domain="[('is_company', '=', True)]")
        self.assertEqual(self._watermark(self.company)["text"], "BROUILLON")
        self.assertFalse(self._watermark(self.person))

    def test_two_documents_calling_different_words_get_none(self):
        self._rule(sequence=1, text="SOCIÉTÉ",
                   filter_domain="[('is_company', '=', True)]")
        self._rule(sequence=2, text="PERSONNE",
                   filter_domain="[('is_company', '=', False)]")
        both = self.company | self.person
        self.assertEqual(self._watermark(self.company)["text"], "SOCIÉTÉ")
        self.assertEqual(self._watermark(self.person)["text"], "PERSONNE")
        self.assertFalse(
            self._watermark(both),
            "deux filigranes différents dans une même impression : aucun, "
            "sans quoi l'un marquerait les pages de l'autre")

    def test_one_bare_document_disarms_the_whole_print(self):
        self._rule(filter_domain="[('is_company', '=', True)]")
        self.assertFalse(self._watermark(self.company | self.person))

    def test_the_first_rule_in_sequence_wins(self):
        self._rule(sequence=20, text="SECOND")
        self._rule(sequence=1, text="PREMIER")
        self.assertEqual(self._watermark(self.company)["text"], "PREMIER")

    def test_an_archived_rule_is_ignored(self):
        rule = self._rule(text="COPIE")
        rule.active = False
        self.assertFalse(self._watermark(self.company))

    def test_a_rule_of_another_company_is_ignored(self):
        """La société retenue est celle du document, pas celle de la session :
        un utilisateur multi-société imprime aussi ce qui n'est pas à lui."""
        other = self.env["res.company"].create({"name": "Autre société"})
        self._rule(text="COPIE", company_id=other.id)
        self.assertFalse(self._watermark(self.company))
        self.company.company_id = other
        self.assertEqual(self._watermark(self.company)["text"], "COPIE")

    def test_a_report_without_records_only_takes_an_unconditional_rule(self):
        conditional = self._rule(
            sequence=1, text="CONDITIONNEL",
            filter_domain="[('is_company', '=', True)]")
        self.assertFalse(self._watermark(self.env["res.partner"]))
        conditional.filter_domain = "[]"
        self.assertEqual(
            self._watermark(self.env["res.partner"])["text"], "CONDITIONNEL")

    def test_the_rendered_html_carries_the_word_and_its_style(self):
        self._rule(text="ANNULÉ", color="#123456", angle=-45, font_size=120)
        html, _kind = self.env["ir.actions.report"]._render_qweb_html(
            self.report.id, self.company.ids)
        html = html.decode() if isinstance(html, bytes) else html
        self.assertIn("ANNULÉ", html)
        self.assertIn("oski-report-watermark", html)
        self.assertIn("#123456", html)
        self.assertIn("rotate(-45deg)", html)
        self.assertIn("120px", html)

    def test_the_rendered_html_carries_nothing_without_a_rule(self):
        html, _kind = self.env["ir.actions.report"]._render_qweb_html(
            self.report.id, self.company.ids)
        html = html.decode() if isinstance(html, bytes) else html
        self.assertIn("Société Essai", html)
        self.assertNotIn("oski-report-watermark", html)

    def test_a_user_without_settings_rights_still_gets_the_watermark(self):
        """Les règles se lisent en sudo : personne n'a besoin des droits de
        paramétrage pour imprimer un document marqué."""
        self._rule(text="COPIE")
        user = self.env["res.users"].create({
            "name": "Employé", "login": "oski_watermark_employe",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        self.assertFalse(user.has_group("base.group_system"))
        values = self._watermark(self.company, env=self.env(user=user))
        self.assertEqual(values["text"], "COPIE")

    def test_an_unreadable_domain_is_refused_at_save(self):
        with self.assertRaises(ValidationError):
            self._rule(filter_domain="[('state', '=', ")

    def test_a_domain_that_does_not_fit_the_model_is_refused(self):
        with self.assertRaises(ValidationError):
            self._rule(filter_domain="[('champ_inexistant', '=', 1)]")

    def test_a_domain_that_is_not_a_list_is_refused(self):
        with self.assertRaises(ValidationError):
            self._rule(filter_domain="{'state': 'draft'}")

    def test_the_drawing_bounds_are_enforced(self):
        with self.assertRaises(ValidationError):
            self._rule(opacity=0)
        with self.assertRaises(ValidationError):
            self._rule(opacity=1.5)
        with self.assertRaises(ValidationError):
            self._rule(angle=120)
        with self.assertRaises(ValidationError):
            self._rule(font_size=4)
