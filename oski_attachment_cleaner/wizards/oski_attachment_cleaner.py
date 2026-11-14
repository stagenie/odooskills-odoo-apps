from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import human_size

DETAIL_MAX = 4000
PREVIEW_MAX = 200


class OskiAttachmentCleaner(models.TransientModel):
    _name = "oski.attachment.cleaner"
    _description = "Attachment Cleanup"

    min_age_days = fields.Integer(
        string="Minimum Age (Days)", default=30, required=True,
        help="More recent attachments are never offered: an upload in "
             "progress does not have its record yet.")
    include_orphans = fields.Boolean(string="Orphans", default=True)
    include_duplicates = fields.Boolean(string="Redundant Copies", default=True)

    scanned = fields.Boolean(string="Scan Done")
    # Les candidates sont montrées en clair, pas par une relation.
    # ``ir.attachment`` fait dépendre l'accès à une pièce de l'accès à son
    # document : une orpheline n'a plus de document, donc même l'écriture d'un
    # Many2many la refuserait à qui n'est pas superutilisateur. Et de toute
    # façon la purge rejoue le relevé : cette liste n'a jamais fait foi.
    candidate_preview = fields.Text(string="Selected Attachments", readonly=True)
    orphan_count = fields.Integer(string="Orphans", readonly=True)
    duplicate_count = fields.Integer(string="Redundant Copies", readonly=True)
    candidate_count = fields.Integer(string="Selected Attachments", readonly=True)
    # En octets, sur une colonne numérique : un ``Integer`` est un entier
    # PostgreSQL de 32 bits, et un magasin de fichiers dépasse vite 2 Go —
    # l'écriture du relevé échouait alors sur « integer out of range ».
    candidate_bytes = fields.Float(string="Selected Size", digits=(16, 0), readonly=True)
    store_bytes = fields.Float(string="Total Size", digits=(16, 0), readonly=True)
    candidate_size = fields.Char(string="Selected Size", compute="_compute_sizes")
    store_size = fields.Char(string="Total Size", compute="_compute_sizes")

    @api.depends("candidate_bytes", "store_bytes")
    def _compute_sizes(self):
        for wizard in self:
            wizard.candidate_size = human_size(wizard.candidate_bytes) or "0"
            wizard.store_size = human_size(wizard.store_bytes) or "0"

    @api.constrains("min_age_days")
    def _check_min_age_days(self):
        for wizard in self:
            if wizard.min_age_days < 0:
                raise ValidationError(_("The minimum age cannot be negative."))

    def _collect(self):
        """Rassemble les candidates du moment.

        Rejoué à la purge, jamais lu depuis la sélection enregistrée : entre le
        relevé et la purge, un enregistrement a pu renaître ou une pièce
        changer de mains.
        """
        self.ensure_one()
        Attachment = self.env["ir.attachment"].sudo()
        orphans = duplicates = Attachment.browse()
        if self.include_orphans:
            orphans = Attachment._oski_find_orphans(self.min_age_days)
        if self.include_duplicates:
            duplicates = Attachment._oski_find_duplicates(self.min_age_days) - orphans
        return orphans, duplicates

    @api.model
    def _describe(self, attachments, limit=PREVIEW_MAX):
        lines = [
            "%s — %s#%s — %s" % (att.name or "?", att.res_model or "-",
                                 att.res_id or 0, human_size(att.file_size) or "0")
            for att in attachments[:limit]]
        if len(attachments) > limit:
            lines.append(_("… and %s more.", len(attachments) - limit))
        return "\n".join(lines)

    def action_scan(self):
        self.ensure_one()
        orphans, duplicates = self._collect()
        retained = orphans | duplicates
        self.write({
            "scanned": True,
            "candidate_preview": self._describe(retained),
            "candidate_count": len(retained),
            "orphan_count": len(orphans),
            "duplicate_count": len(duplicates),
            "candidate_bytes": sum(retained.mapped("file_size")),
            "store_bytes": sum(self.env["ir.attachment"].sudo().search([]).mapped("file_size")),
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Attachment Cleanup"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _criteria_label(self):
        parts = []
        if self.include_orphans:
            parts.append(_("orphans"))
        if self.include_duplicates:
            parts.append(_("redundant copies"))
        return _("%(kinds)s, older than %(days)s days",
                 kinds=" + ".join(parts) or _("no criteria"), days=self.min_age_days)

    def action_purge(self):
        self.ensure_one()
        if not self.scanned:
            raise UserError(_("Run the scan first: nothing is deleted blindly."))
        orphans, duplicates = self._collect()
        retained = orphans | duplicates
        if not retained:
            raise UserError(_("Nothing left to purge: the scan is already outdated."))
        freed = sum(retained.mapped("file_size"))
        detail = "\n".join(
            "%s [%s#%s]" % (att.name or "?", att.res_model or "-", att.res_id or 0)
            for att in retained)[:DETAIL_MAX]
        count = len(retained)
        retained.unlink()
        self.env["oski.attachment.purge"].create({
            "attachment_count": count,
            "freed_bytes": freed,
            "criteria": self._criteria_label(),
            "detail": detail,
        })
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _("%(count)s attachment(s) deleted, %(size)s freed.",
                             count=count, size=human_size(freed) or "0"),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
