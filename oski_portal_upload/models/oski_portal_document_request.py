from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

DEFAULT_MAX_SIZE_MB = 15
DEFAULT_EXTENSIONS = "pdf,png,jpg,jpeg,doc,docx,xls,xlsx,odt,ods,csv,zip"


class OskiPortalDocumentRequest(models.Model):
    """Un document réclamé au client, sur une fiche qu'il voit déjà.

    La demande porte sa propre fiche cible (modèle et identifiant) plutôt que
    d'être greffée sur un modèle précis : le devis, la facture et la tâche
    partagent le même portail, et le module n'a donc à dépendre que de lui.
    """

    _name = "oski.portal.document.request"
    _description = "Document demandé au client"
    _order = "deadline, id"

    name = fields.Char(string="Document demandé", required=True)
    resource_ref = fields.Reference(
        selection="_selection_target_model", string="Fiche", required=True,
        help="La fiche du portail sur laquelle le client déposera son document.")
    res_model = fields.Char(
        string="Modèle", compute="_compute_resource", store=True, index=True)
    res_id = fields.Integer(
        string="Identifiant", compute="_compute_resource", store=True, index=True)
    partner_id = fields.Many2one(
        "res.partner", string="Client", required=True, index=True,
        help="Le contact à qui le document est demandé. Les autres contacts de "
             "la même société peuvent également le déposer.")
    state = fields.Selection(
        [("pending", "Attendu"), ("received", "Reçu"), ("cancelled", "Annulé")],
        string="État", default="pending", required=True, index=True)
    deadline = fields.Date(string="Attendu pour")
    note = fields.Text(
        string="Précisions", help="Texte affiché au client sous le nom du document.")
    attachment_id = fields.Many2one(
        "ir.attachment", string="Document reçu", readonly=True, copy=False,
        ondelete="set null")
    received_on = fields.Datetime(string="Reçu le", readonly=True, copy=False)
    company_id = fields.Many2one(
        "res.company", string="Société", required=True,
        default=lambda self: self.env.company)

    @api.model
    def _selection_target_model(self):
        """Les modèles qui ont une page portail — ceux qui portent une adresse
        de partage. Proposer les autres promettrait une page inexistante."""
        fields_ = self.env["ir.model.fields"].sudo().search([
            ("name", "=", "access_url"), ("ttype", "=", "char")])
        models_ = fields_.model_id.filtered(lambda model: model.model in self.env)
        return [(model.model, model.name) for model in models_.sorted("name")]

    @api.depends("resource_ref")
    def _compute_resource(self):
        for request in self:
            reference = request.resource_ref
            request.res_model = reference._name if reference else False
            request.res_id = reference.id if reference else False

    @api.onchange("resource_ref")
    def _onchange_resource_ref(self):
        record = self.resource_ref
        if record and not self.partner_id and "partner_id" in record._fields:
            self.partner_id = record.partner_id

    @api.constrains("resource_ref")
    def _check_resource_ref(self):
        for request in self:
            record = request.resource_ref
            if record and not record.exists():
                raise ValidationError(_("Cette fiche n'existe plus."))

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset(self):
        for request in self:
            if request.state == "received":
                raise UserError(_(
                    "« %s » a déjà été reçu : annulez la demande plutôt que de "
                    "la rouvrir, l'historique du dépôt doit rester lisible.",
                    request.name))
        self.write({"state": "pending"})

    def action_open_record(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
        }

    # -- Portail ---------------------------------------------------------

    @api.model
    def _oski_pending_for(self, record, partner):
        """Les demandes qu'un visiteur donné peut honorer sur cette fiche.

        Le rapprochement se fait sur la société du contact : dans une
        entreprise, ce n'est pas toujours la personne nommée dans la demande
        qui dépose le fichier.
        """
        if not record or not partner:
            return self.browse()
        commercial = partner.commercial_partner_id
        return self.sudo().search([
            ("res_model", "=", record._name),
            ("res_id", "=", record.id),
            ("state", "=", "pending"),
        ]).filtered(
            lambda req: req.partner_id.commercial_partner_id == commercial)

    def _oski_receive(self, attachment):
        """Enregistre le dépôt et le raconte sur la fiche.

        La trace part dans le fil de discussion de la fiche visée, là où
        l'équipe regarde, et non sur la demande elle-même que personne n'ouvre.
        """
        self.ensure_one()
        self.sudo().write({
            "attachment_id": attachment.id,
            "state": "received",
            "received_on": fields.Datetime.now(),
        })
        record = self.sudo().resource_ref
        if record and hasattr(record, "message_post"):
            record.message_post(
                body=Markup("<p>%s</p>") % _(
                    "Document déposé depuis le portail : %(request)s — "
                    "%(filename)s",
                    request=self.name, filename=attachment.name),
                attachment_ids=attachment.ids,
                subtype_xmlid="mail.mt_note",
            )

    @api.model
    def _oski_max_size(self):
        raw = self.env["ir.config_parameter"].sudo().get_param(
            "oski_portal_upload.max_size_mb", DEFAULT_MAX_SIZE_MB)
        try:
            megabytes = int(raw)
        except (TypeError, ValueError):
            megabytes = DEFAULT_MAX_SIZE_MB
        return max(megabytes, 1) * 1024 * 1024

    @api.model
    def _oski_allowed_extensions(self):
        raw = self.env["ir.config_parameter"].sudo().get_param(
            "oski_portal_upload.allowed_extensions", DEFAULT_EXTENSIONS)
        return [part.strip().lower().lstrip(".")
                for part in (raw or "").split(",") if part.strip()]
