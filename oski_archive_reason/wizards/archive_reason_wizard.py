from odoo import _, fields, models
from odoo.exceptions import UserError


class OskiArchiveReasonWizard(models.TransientModel):
    _name = "oski.archive.reason.wizard"
    _description = "Archive Reason"

    reason = fields.Text(string="Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])
        if not active_model or not active_ids:
            raise UserError(_("No record to archive."))
        records = self.env[active_model].browse(active_ids)
        for record in records:
            if hasattr(record, "message_post"):
                record.message_post(
                    body=_("Archived — reason: %s", self.reason)
                )
        records.with_context(oski_archive_confirmed=True).action_archive()
        return {"type": "ir.actions.act_window_close"}
