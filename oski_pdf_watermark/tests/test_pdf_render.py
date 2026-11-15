import io

from odoo.tests import HttpCase, tagged
from odoo.tools.pdf import PdfFileReader


@tagged("post_install", "-at_install")
class TestPdfWatermarkRender(HttpCase):
    """Le vrai PDF, rendu par wkhtmltopdf, page par page.

    Le rendu HTML ne prouve rien pour le PDF : celui-ci ne garde que les
    ``div.article`` du HTML, et wkhtmltopdf ne répète pas un élément fixe sur
    les pages suivantes. Ce test lit donc le texte de chaque page du PDF.
    HttpCase : wkhtmltopdf rappelle le serveur de test pour ses feuilles de
    style ; ``force_report_rendering`` empêche le repli HTML des tests.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.ui.view"].create({
            "name": "Rapport PDF d'essai filigrane",
            "type": "qweb",
            "key": "oski_pdf_watermark.test_pdf_report",
            "arch": """
                <t t-name="oski_pdf_watermark.test_pdf_report">
                    <t t-call="web.html_container">
                        <t t-foreach="docs" t-as="o">
                            <t t-call="web.external_layout">
                                <div class="page">
                                    <h2 t-out="o.name"/>
                                    <p t-foreach="range(120)" t-as="i">Ligne <t t-out="i"/></p>
                                </div>
                            </t>
                        </t>
                    </t>
                </t>
            """,
        })
        cls.report = cls.env["ir.actions.report"].create({
            "name": "Rapport PDF d'essai filigrane",
            "model": "res.partner",
            "report_type": "qweb-pdf",
            "report_name": "oski_pdf_watermark.test_pdf_report",
        })
        cls.marked = cls.env["res.partner"].create({"name": "Marqué", "ref": "WM-YES"})
        cls.bare = cls.env["res.partner"].create({"name": "Nu", "ref": "WM-NO"})
        cls.env["oski.report.watermark"].create({
            "name": "Essai PDF", "report_id": cls.report.id, "text": "OSKIMARK",
            "filter_domain": "[('ref', '=', 'WM-YES')]",
        })

    def _pages_text(self, records, layout=None):
        if layout:
            self.env.company.external_report_layout_id = self.env.ref(layout)
        pdf, _kind = (
            self.env["ir.actions.report"]
            .with_context(force_report_rendering=True)
            ._render_qweb_pdf(self.report.report_name, records.ids)
        )
        self.assertTrue(pdf.startswith(b"%PDF"), "le rendu n'a pas produit de PDF")
        reader = PdfFileReader(io.BytesIO(pdf), strict=False)
        pages = []
        for page in reader.pages:
            extract = getattr(page, "extract_text", None) or page.extractText
            pages.append(extract())
        return pages

    def test_every_page_of_the_pdf_carries_the_word(self):
        for layout in ("web.external_layout_standard", "web.external_layout_bubble"):
            with self.subTest(layout=layout):
                pages = self._pages_text(self.marked, layout)
                self.assertGreater(len(pages), 1, "le document d'essai doit tenir sur plusieurs pages")
                self.assertIn("Ligne 119", "".join(pages))
                for number, text in enumerate(pages, start=1):
                    self.assertIn("OSKIMARK", text, "page %s sans filigrane (%s)" % (number, layout))

    def test_a_document_outside_the_rule_prints_bare(self):
        pages = self._pages_text(self.bare)
        self.assertIn("Ligne 119", "".join(pages))
        self.assertNotIn("OSKIMARK", "".join(pages))

    def test_the_html_watermark_stays_out_of_the_pdf_body(self):
        """Le PDF est tamponné après coup : le HTML qu'il reçoit n'en porte
        pas, sans quoi la première page aurait deux filigranes."""
        html, _kind = self.env["ir.actions.report"]._render_qweb_html(
            self.report.report_name, self.marked.ids, data={"report_type": "pdf"})
        self.assertFalse(b"oski-report-watermark" in html,
                         "le HTML destiné au PDF porte le filigrane HTML")
        html, _kind = self.env["ir.actions.report"]._render_qweb_html(
            self.report.report_name, self.marked.ids)
        self.assertTrue(b"oski-report-watermark" in html,
                        "l'aperçu HTML a perdu son filigrane")
