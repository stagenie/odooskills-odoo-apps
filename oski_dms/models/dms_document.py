from odoo import api, fields, models


class DmsDocument(models.Model):
    _name = 'oski.dms.document'
    _description = "Document GED"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(required=True, tracking=True)
    workspace_id = fields.Many2one(
        'oski.dms.workspace', string="Espace", required=True,
        ondelete='restrict', tracking=True)
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

    mimetype = fields.Char(related='attachment_id.mimetype', store=True)
    file_size = fields.Integer(related='attachment_id.file_size', store=True)

    version_no = fields.Integer(string="Version", default=1, copy=False)
    previous_version_id = fields.Many2one(
        'oski.dms.document', string="Version précédente", copy=False)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        related='workspace_id.company_id', store=True, string="Société")

    @api.depends('attachment_id.datas')
    def _compute_file(self):
        for doc in self:
            doc.file = doc.attachment_id.datas if doc.attachment_id else False

    def _inverse_file(self):
        for doc in self:
            if not doc.file:
                continue
            fname = doc.file_name or doc.name
            if doc.attachment_id:
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
                rec = self.env[doc.res_model].browse(doc.res_id).exists()
                name = rec.display_name if rec else False
            doc.res_name = name
