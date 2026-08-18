import logging

from odoo import models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_rendering_context(self, report, docids, data):
        """Pose le filigrane dans les valeurs du rendu.

        Le calcul passe par le contexte de rendu et non par une réécriture du
        HTML produit : le gabarit décide seul de l'afficher, et un rapport qui
        n'appelle pas ``web.html_container`` reste intact.
        """
        data = super()._get_rendering_context(report, docids, data)
        data["oski_watermark"] = self._oski_watermark_values(report, docids)
        return data

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
                "oski_pdf_watermark : %s documents du rapport %s appellent des "
                "filigranes différents, aucun n'est posé.",
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
