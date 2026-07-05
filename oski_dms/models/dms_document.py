from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class DmsDocument(models.Model):
    _name = 'oski.dms.document'
    _description = "Document GED"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string="Nom", required=True, tracking=True)
    workspace_id = fields.Many2one(
        'oski.dms.workspace', string="Espace", required=True,
        ondelete='restrict', tracking=True,
        default=lambda self: self._default_workspace())
    attachment_id = fields.Many2one(
        'ir.attachment', string="Pièce jointe", ondelete='cascade', copy=False)

    file = fields.Binary(
        string="Fichier", compute='_compute_file', inverse='_inverse_file')
    file_name = fields.Char(string="Nom du fichier")

    tag_ids = fields.Many2many('oski.dms.tag', string="Étiquettes")
    res_model = fields.Char(string="Modèle lié")
    res_id = fields.Many2oneReference(
        string="Enregistrement lié", model_field='res_model')
    res_name = fields.Char(
        compute='_compute_res_name', string="Nom lié", store=False)
    owner_id = fields.Many2one(
        'res.users', string="Propriétaire", default=lambda s: s.env.user)

    mimetype = fields.Char(
        related='attachment_id.mimetype', store=True, string="Type de fichier")
    file_size = fields.Integer(
        related='attachment_id.file_size', store=True, string="Taille (octets)")

    version_no = fields.Integer(string="Version", default=1, copy=False)
    previous_version_id = fields.Many2one(
        'oski.dms.document', string="Version précédente", copy=False)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        related='workspace_id.company_id', store=True, string="Société")

    @api.model
    def _default_workspace(self):
        """Espace proposé par défaut, réglable via Configuration > Documents."""
        param = self.env['ir.config_parameter'].sudo().get_param(
            'oski_dms.default_workspace_id')
        return int(param) if param else False

    @api.depends('attachment_id.datas')
    def _compute_file(self):
        for doc in self:
            doc.file = doc.attachment_id.datas if doc.attachment_id else False

    def _inverse_file(self):
        max_mb = int(self.env['ir.config_parameter'].sudo().get_param(
            'oski_dms.max_upload_mb', 0) or 0)
        for doc in self:
            if not doc.file:
                continue
            if max_mb:
                # doc.file est du base64 ; taille binaire ≈ len*3/4
                size_mb = (len(doc.file) * 3 / 4) / (1024 * 1024)
                if size_mb > max_mb:
                    raise ValidationError(
                        self.env._("Fichier trop volumineux (max %s Mo).", max_mb))
            fname = doc.file_name or doc.name
            # Un document peut pointer vers un attachment EXTERNE partagé
            # (classé via « Classer une PJ existante », res_model='res.partner'
            # par ex.). N'écraser QUE les attachments POSSÉDÉS par la GED :
            # sinon déposer un nouveau fichier muterait la PJ d'origine de
            # l'enregistrement métier source (perte de données).
            owned = doc.attachment_id and doc.attachment_id.res_model == 'oski.dms.document'
            if owned:
                doc.attachment_id.write({'datas': doc.file, 'name': fname})
            else:
                doc.attachment_id = self.env['ir.attachment'].create({
                    'name': fname,
                    'datas': doc.file,
                    'res_model': 'oski.dms.document',
                    'res_id': doc.id,
                })

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for doc in self:
            name = False
            if doc.res_model and doc.res_id:
                try:
                    rec = self.env[doc.res_model].browse(doc.res_id).exists()
                    name = rec.display_name if rec else False
                except (KeyError, AccessError):
                    name = False
            doc.res_name = name

    version_ids = fields.One2many(
        'oski.dms.document', 'previous_version_id', string="Versions suivantes")

    def action_new_version(self, datas, file_name=None):
        """Crée une nouvelle version courante ; archive la version actuelle.

        `attachment_id`/`version_no`/`previous_version_id` sont `copy=False` :
        la nouvelle version reconstruit son propre `ir.attachment` via
        `file`/`file_name` (inverse `_inverse_file`) plutôt que de partager
        celui de l'ancienne version.
        """
        self.ensure_one()
        new = self.copy({
            'version_no': self.version_no + 1,
            'previous_version_id': self.id,
            'active': True,
            'name': self.name,
            'file': datas,
            'file_name': file_name or self.file_name,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            'res_model': self.res_model,
            'res_id': self.res_id,
        })
        self.active = False
        return new

    def _version_chain(self):
        """Retourne tous les documents de la chaîne de versions (actifs ou non)."""
        self.ensure_one()
        root = self
        while root.previous_version_id:
            root = root.previous_version_id
        chain = root
        cursor = root
        nxt = self.with_context(active_test=False).search(
            [('previous_version_id', '=', cursor.id)], limit=1)
        while nxt:
            chain |= nxt
            cursor = nxt
            nxt = self.with_context(active_test=False).search(
                [('previous_version_id', '=', cursor.id)], limit=1)
        return chain

    def action_restore_version(self):
        """Ré-active cette version comme courante ; archive le reste de la chaîne."""
        self.ensure_one()
        chain = self._version_chain()
        (chain - self).write({'active': False})
        self.active = True
        return self

    def action_view_versions(self):
        self.ensure_one()
        chain = self._version_chain()
        return {
            'type': 'ir.actions.act_window',
            'name': "Versions",
            'res_model': 'oski.dms.document',
            'view_mode': 'list,form',
            'domain': [('id', 'in', chain.ids)],
            'context': {'active_test': False},
        }

    def action_open_version_wizard(self):
        """Ouvre le wizard de dépôt d'une nouvelle version (point d'entrée UI)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': "Nouvelle version",
            'res_model': 'oski.dms.version.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_document_id': self.id},
        }

    def action_open_linked_record(self):
        """Ouvre le formulaire de l'enregistrement métier rattaché.

        Utilisé par le bouton du header form : reste discret (`invisible`
        tant que `res_id` n'est pas renseigné) plutôt que de lever une erreur.
        """
        self.ensure_one()
        if not (self.res_model and self.res_id):
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    def unlink(self):
        # Ne supprimer que les attachments réellement POSSÉDÉS par la GED
        # (créés via l'upload — `res_model='oski.dms.document'`). Un document
        # peut pointer vers un attachment EXTERNE partagé (« classer une PJ
        # existante », res_model='res.partner' par ex.) : le détruire causerait
        # une perte de données sur l'enregistrement métier source.
        owned = self.attachment_id.filtered(
            lambda a: a.res_model == 'oski.dms.document')
        res = super().unlink()
        # `super().unlink()` supprime déjà les attachments possédés dont
        # res_model/res_id pointent vers ce document (nettoyage natif Odoo) ;
        # `.exists()` évite le MissingError sur ceux-là tout en supprimant un
        # éventuel attachment possédé restant.
        owned.exists().unlink()
        return res
