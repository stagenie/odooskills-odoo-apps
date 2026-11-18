from odoo import models


class OskiModuleTrial(models.Model):
    _inherit = "oski.module.trial"

    def _feedback_url(self):
        """Formulaire de demande du module essayé, rattaché à cet essai."""
        self.ensure_one()
        return "%s%s/apps/m/%s/feedback?source=trial&trial=%s-%s" % (
            self.get_base_url(), self._feedback_lang_prefix(),
            self.module_id.technical_name, self.id, self.access_token,
        )

    def _feedback_lang_prefix(self):
        """« /fr » pour un essai en français ; rien pour la langue par défaut du site."""
        lang = self.env["res.lang"]._get_data(code=self.lang) if self.lang else None
        website = self.env["website"].sudo().search([], limit=1)
        if not lang or not website or self.lang == website.default_lang_id.code:
            return ""
        return "/" + lang.url_code
