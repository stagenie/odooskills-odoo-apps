from odoo import api, fields, models


class OskiDevRequest(models.Model):
    _name = "oski.dev.request"
    _description = "Demande de développement de module"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(
        string="Référence", required=True, copy=False, readonly=True,
        index=True, default=lambda self: "Nouveau",
    )
    # Demandeur
    requester_name = fields.Char(string="Nom / Personne", required=True, tracking=True)
    company_name = fields.Char(string="Entreprise")
    email = fields.Char(string="Email", required=True, tracking=True)
    phone = fields.Char(string="Téléphone")
    user_id = fields.Many2one(
        "res.users", string="Demandeur", readonly=True,
        default=lambda self: self.env.user,
    )
    # Besoin
    subject = fields.Char(string="Objet", required=True, tracking=True)
    description = fields.Text(string="Description du besoin", required=True)
    category_id = fields.Many2one("oski.module.category", string="Catégorie")
    odoo_version = fields.Selection(
        [
            ("15.0", "15.0"),
            ("16.0", "16.0"),
            ("17.0", "17.0"),
            ("18.0", "18.0"),
            ("19.0", "19.0"),
        ],
        string="Version Odoo cible",
        default="19.0",
    )
    budget_range = fields.Selection(
        [
            ("lt_500", "Moins de 500 €"),
            ("b_500_1500", "500 – 1 500 €"),
            ("b_1500_5000", "1 500 – 5 000 €"),
            ("gt_5000", "Plus de 5 000 €"),
            ("to_discuss", "À discuter"),
        ],
        string="Budget",
        required=True,
        default="to_discuss",
    )
    delivery_mode = fields.Selection(
        [
            ("store", "Publié sur le store (tarif standard)"),
            ("exclusive", "Exclusif pour moi (tarif nettement supérieur)"),
        ],
        string="Mode de livraison",
        required=True,
        default="store",
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", string="Pièces jointes",
    )
    state = fields.Selection(
        [
            ("new", "Nouveau"),
            ("analysis", "En analyse"),
            ("quoted", "Devis envoyé"),
            ("accepted", "Accepté"),
            ("rejected", "Refusé"),
            ("delivered", "Livré"),
        ],
        string="État",
        default="new",
        tracking=True,
        group_expand="_group_expand_state",
    )
    assigned_id = fields.Many2one(
        "res.users", string="Assigné à", tracking=True,
        domain="[('share', '=', False)]",
    )
    module_id = fields.Many2one(
        "oski.module", string="Module livré",
        help="Module du store créé en réponse à cette demande.",
    )
    priority = fields.Selection(
        [("0", "Normale"), ("1", "Haute"), ("2", "Urgente")],
        string="Priorité", default="0",
    )

    @api.model
    def _group_expand_state(self, states, domain):
        return [s[0] for s in type(self).state.selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "Nouveau":
                vals["name"] = self.env["ir.sequence"].sudo().next_by_code(
                    "oski.dev.request"
                ) or "Nouveau"
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Transitions d'état (boutons header)
    # ------------------------------------------------------------------
    def action_set_analysis(self):
        self.write({"state": "analysis"})

    def action_set_quoted(self):
        self.write({"state": "quoted"})

    def action_accept(self):
        self.write({"state": "accepted"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_set_delivered(self):
        self.write({"state": "delivered"})
