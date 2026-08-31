from odoo import _, api, fields, models


class OskiDevRequest(models.Model):
    _inherit = "oski.dev.request"

    lead_id = fields.Many2one(
        "crm.lead",
        string="Opportunité",
        readonly=True,
        copy=False,
        help="Opportunité ouverte à la soumission de la demande.",
    )

    def _selection_label(self, fname):
        """Libellé lisible d'un champ selection, statique ou dynamique.

        `_fields[...].selection` vaut le nom d'une méthode quand la liste est
        calculée (odoo_version la tire du référentiel des versions) : passer
        par _description_selection couvre les deux cas.
        """
        value = self[fname]
        labels = dict(self._fields[fname]._description_selection(self.env))
        return labels.get(value, value or "")

    def _prepare_crm_lead_values(self):
        """Valeurs de l'opportunité ouverte pour cette demande."""
        self.ensure_one()
        version = self._selection_label("odoo_version")
        budget = self._selection_label("budget_range")
        mode = self._selection_label("delivery_mode")
        lines = [
            "<p><b>%s</b> — %s</p>" % (self.name or "", self.subject or ""),
            "<p>%s</p>" % (self.description or "").replace("\n", "<br/>"),
            "<ul>",
            "<li>Version Odoo visée : %s</li>" % (version or "non précisée"),
            "<li>Budget annoncé : %s</li>" % (budget or "non précisé"),
            "<li>Mode de livraison : %s</li>" % (mode or "non précisé"),
            "<li>Catégorie : %s</li>" % (self.category_id.name or "non précisée"),
            "</ul>",
        ]
        return {
            "name": self.subject or self.name,
            "type": "opportunity",
            "contact_name": self.requester_name,
            "partner_name": self.company_name or False,
            "email_from": self.email,
            "phone": self.phone or False,
            "description": "".join(lines),
        }

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        for request in requests:
            # sudo : la demande naît d'un formulaire public, l'utilisateur
            # public n'a évidemment aucun droit sur le pipeline commercial.
            lead = self.env["crm.lead"].sudo().create(
                request._prepare_crm_lead_values())
            request.sudo().lead_id = lead.id
        return requests

    def action_open_lead(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Opportunité"),
            "res_model": "crm.lead",
            "res_id": self.lead_id.id,
            "view_mode": "form",
        }
