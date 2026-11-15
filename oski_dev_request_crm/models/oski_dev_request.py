from odoo import _, api, fields, models


class OskiDevRequest(models.Model):
    _inherit = "oski.dev.request"

    lead_id = fields.Many2one(
        "crm.lead",
        string="Opportunity",
        readonly=True,
        copy=False,
        help="Opportunity opened when the request was submitted.",
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

    def _oski_crm_reader_lang(self):
        """Langue de l'équipe commerciale qui lit l'opportunité.

        La demande naît d'un formulaire public : la langue de la requête est
        celle du visiteur, pas celle de qui traitera l'affaire. On écrit donc
        dans la langue de la société, à défaut celle de l'administrateur.
        """
        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        return (self.env.company.partner_id.lang
                or (admin and admin.sudo().lang) or "en_US")

    def _prepare_crm_lead_values(self):
        """Valeurs de l'opportunité ouverte pour cette demande."""
        self.ensure_one()
        rec = self.with_context(lang=self._oski_crm_reader_lang())
        version = rec._selection_label("odoo_version")
        budget = rec._selection_label("budget_range")
        mode = rec._selection_label("delivery_mode")
        category = rec.category_id.name
        lines = [
            "<p><b>%s</b> — %s</p>" % (self.name or "", self.subject or ""),
            "<p>%s</p>" % (self.description or "").replace("\n", "<br/>"),
            "<ul>",
            "<li>%s</li>" % (rec.env._("Target Odoo version: %s", version) if version
                             else rec.env._("Target Odoo version: not specified")),
            "<li>%s</li>" % (rec.env._("Stated budget: %s", budget) if budget
                             else rec.env._("Stated budget: not specified")),
            "<li>%s</li>" % (rec.env._("Delivery mode: %s", mode) if mode
                             else rec.env._("Delivery mode: not specified")),
            "<li>%s</li>" % (rec.env._("Category: %s", category) if category
                             else rec.env._("Category: not specified")),
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
            "name": _("Opportunity"),
            "res_model": "crm.lead",
            "res_id": self.lead_id.id,
            "view_mode": "form",
        }
