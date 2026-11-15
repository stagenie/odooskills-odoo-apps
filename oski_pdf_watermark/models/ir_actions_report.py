import io
import logging
import math

from odoo import models
from odoo.exceptions import AccessError
from odoo.tools.pdf import NameObject, PdfFileReader, PdfFileWriter

_logger = logging.getLogger(__name__)

WATERMARK_FONT = "Helvetica-Bold"


def _oski_call(obj, *names):
    """Méthode de PyPDF2 1.x (camelCase) ou de PyPDF2 2.x / pypdf (snake_case)."""
    for name in names:
        method = getattr(obj, name, None)
        if method is not None:
            return method
    raise AttributeError(names[0])


def _oski_rgb(color):
    """``#abc``, ``#aabbcc`` ou ``#aabbccdd`` (canal alpha ignoré) -> (r, g, b) entre 0 et 1."""
    value = (color or "#000000").lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_rendering_context(self, report, docids, data):
        """Pose le filigrane dans les valeurs du rendu HTML.

        Le rendu PDF n'en veut pas : il ne garde du HTML que les ``div.article``
        (``_prepare_html``), et wkhtmltopdf ne répète pas un élément en
        position fixe sur les pages suivantes. Le PDF reçoit son filigrane page
        par page, une fois produit (``_render_qweb_pdf_prepare_streams``).
        """
        data = super()._get_rendering_context(report, docids, data)
        if data.get("report_type") == "pdf":
            data["oski_watermark"] = False
        else:
            data["oski_watermark"] = self._oski_watermark_values(report, docids)
        return data

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        """Tamponne chaque page des PDF que le rendu vient de produire.

        Un PDF repris d'une pièce jointe enregistrée (rapport « à conserver »)
        n'est pas retouché : il porte déjà ce qui valait à sa première impression.
        """
        streams = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
        report = self._get_report(report_ref)
        values = self._oski_watermark_values(report, res_ids or [])
        if not values:
            return streams
        for stream_data in streams.values():
            if stream_data.get("attachment") or not stream_data.get("stream"):
                continue
            stream_data["stream"] = self._oski_stamp_pdf(stream_data["stream"], values)
        return streams

    def _oski_stamp_pdf(self, stream, values):
        """Pose le mot en diagonale, au centre de chaque page, derrière le contenu.

        Le mot reste du texte (lisible par un extracteur, sélectionnable) ; sa
        taille, en points, est réduite si le mot incliné dépasserait la page.
        """
        from reportlab.lib.colors import Color  # noqa: PLC0415
        from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: PLC0415
        from reportlab.pdfgen import canvas  # noqa: PLC0415

        try:
            stream.seek(0)
            reader = PdfFileReader(stream, strict=False)
            pages = list(reader.pages)
            packet = io.BytesIO()
            sheet = canvas.Canvas(packet)
            red, green, blue = _oski_rgb(values["color"])
            angle = math.radians(abs(values["angle"]))
            text = values["text"]
            for page in pages:
                box = getattr(page, "mediabox", None) or page.mediaBox
                left, bottom, right, top = (float(coord) for coord in box)
                width, height = abs(right - left), abs(top - bottom)
                size = float(values["font_size"])
                text_width = stringWidth(text, WATERMARK_FONT, size)
                span_x = text_width * math.cos(angle) + size * math.sin(angle)
                span_y = text_width * math.sin(angle) + size * math.cos(angle)
                size *= min(1.0, 0.9 * width / span_x, 0.9 * height / span_y)
                sheet.setPageSize((width, height))
                sheet.saveState()
                # Angle du gabarit HTML (CSS, sens horaire) -> sens trigonométrique.
                sheet.translate(min(left, right) + width / 2, min(bottom, top) + height / 2)
                sheet.rotate(-values["angle"])
                sheet.setFont(WATERMARK_FONT, size)
                sheet.setFillColor(Color(red, green, blue, alpha=values["opacity"]))
                sheet.drawCentredString(0, -size * 0.35, text)
                sheet.restoreState()
                sheet.showPage()
            sheet.save()
            packet.seek(0)
            marks = PdfFileReader(packet, strict=False)
            writer = PdfFileWriter()
            for page, mark in zip(pages, marks.pages):
                # Le contenu de la page est fusionné PAR-DESSUS le mot, puis
                # le tout revient dans la page d'origine : le mot passe derrière
                # le texte, la page garde ses liens, ses dimensions, son parent.
                _oski_call(mark, "merge_page", "mergePage")(page)
                page[NameObject("/Contents")] = mark["/Contents"]
                page[NameObject("/Resources")] = mark["/Resources"]
                _oski_call(writer, "add_page", "addPage")(page)
            output = io.BytesIO()
            writer.write(output)
            output.seek(0)
            return output
        except Exception:
            # Une impression ne doit pas échouer à cause du filigrane.
            _logger.exception("oski_pdf_watermark: the PDF could not be stamped.")
            stream.seek(0)
            return stream

    def _oski_watermark_values(self, report, docids):
        rules = self.env["oski.report.watermark"].sudo().search([
            ("report_id", "=", report.id)])
        if not rules:
            return False

        model = report.model
        records = None
        if model and model in self.env and docids:
            try:
                records = self.env[model].browse(docids).exists()
                records.check_access("read")
            except AccessError:
                # L'impression échouera d'elle-même sur les droits ; le
                # filigrane n'a pas à porter cette erreur.
                return False

        if not records:
            # Rapport sans enregistrement (état, tableau de bord) : seule une
            # règle sans condition peut s'y appliquer.
            unconditional = rules.filtered(
                lambda rule: not rule._oski_domain()
                and rule.company_id in (self.env["res.company"], self.env.company))
            return unconditional[0]._oski_values() if unconditional else False

        matched = [self._oski_first_match(rules, record) for record in records]
        if not all(matched):
            # Un des documents ne porte aucun filigrane : en poser un le
            # marquerait à tort, puisqu'un élément fixe se répète sur toutes
            # les pages du PDF produit.
            return False
        if len({rule.id for rule in matched}) > 1:
            _logger.info(
                "oski_pdf_watermark: %s documents of report %s call for "
                "different watermarks, none is applied.",
                len(matched), report.report_name)
            return False
        return matched[0]._oski_values()

    def _oski_first_match(self, rules, record):
        # La société qui compte est celle du document imprimé, pas celle sous
        # laquelle on est connecté : un utilisateur multi-société imprime des
        # documents qui ne sont pas tous les siens.
        company = self.env.company
        if "company_id" in record._fields and record.company_id:
            company = record.company_id
        for rule in rules:
            if rule.company_id and rule.company_id != company:
                continue
            if record.filtered_domain(rule._oski_domain()):
                return rule
        return False
