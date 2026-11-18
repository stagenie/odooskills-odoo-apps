from odoo import models


class OskiModuleTrial(models.Model):
    _inherit = "oski.module.trial"

    def _feedback_url(self):
        """Formulaire de demande du module essayé, rattaché à cet essai."""
        self.ensure_one()
        return "%s/apps/m/%s/feedback?source=trial&trial=%s-%s" % (
            self.get_base_url(), self.module_id.technical_name, self.id, self.access_token,
        )
