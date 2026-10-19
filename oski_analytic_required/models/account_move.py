from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        self._oski_check_analytic()
        return super()._post(soft=soft)

    def _oski_check_analytic(self):
        missing = self.env["account.move.line"]
        for move in self:
            missing |= move.line_ids.filtered(
                lambda line: line._oski_analytic_is_missing())
        if not missing:
            return
        raise UserError(_(
            "Ces lignes doivent porter une ventilation analytique avant "
            "comptabilisation :\n%s",
            "\n".join(
                "• %(move)s — %(account)s — %(label)s" % {
                    "move": line.move_id.display_name,
                    "account": line.account_id.display_name,
                    "label": line.name or "",
                }
                for line in missing)))
