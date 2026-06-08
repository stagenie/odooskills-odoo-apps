from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    oski_duplicate_id = fields.Many2one(
        "res.partner", string="Doublon possible", readonly=True,
        help="Contact existant partageant le même email ou téléphone.",
    )

    def _oski_check_enabled(self, kind):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "oski_dup.check_%s" % kind, "True"
        )
        return value not in ("False", "false", "0", "", None)

    def _oski_find_duplicate(self, email=None, phone=None):
        """Renvoie le premier contact existant en doublon (email ou tél), ou vide."""
        email = self.email if email is None else email
        phone = self.phone if phone is None else phone
        leaves = []
        if self._oski_check_enabled("email") and email:
            leaves.append(("email", "=ilike", email))
        if self._oski_check_enabled("phone") and phone:
            leaves.append(("phone", "=", phone))
        if not leaves:
            return self.browse()
        domain = ["|"] * (len(leaves) - 1) + leaves
        current_id = self.id or self._origin.id
        if current_id:
            domain = [("id", "!=", current_id)] + domain
        return self.with_context(active_test=False).search(domain, limit=1)

    @api.onchange("email")
    def _onchange_oski_email_duplicate(self):
        if not self.email:
            return
        dup = self._oski_find_duplicate(email=self.email, phone=False)
        self.oski_duplicate_id = dup
        if dup:
            return {"warning": {
                "title": _("Doublon possible"),
                "message": _("Un contact avec cet email existe déjà : %s") % dup.display_name,
            }}

    @api.onchange("phone")
    def _onchange_oski_phone_duplicate(self):
        if not self.phone:
            return
        dup = self._oski_find_duplicate(email=False, phone=self.phone)
        if dup:
            self.oski_duplicate_id = dup
            return {"warning": {
                "title": _("Doublon possible"),
                "message": _("Un contact avec ce téléphone existe déjà : %s") % dup.display_name,
            }}

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        for partner in partners:
            dup = partner._oski_find_duplicate()
            if dup:
                partner.oski_duplicate_id = dup
        return partners
