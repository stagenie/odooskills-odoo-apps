from odoo import api, fields, models


class DmsWorkspace(models.Model):
    _name = 'oski.dms.workspace'
    _description = "Espace GED"
    _inherit = ['mail.thread']
    _parent_store = True
    _parent_name = 'parent_id'
    _order = 'complete_name'

    name = fields.Char(required=True, tracking=True)
    parent_id = fields.Many2one(
        'oski.dms.workspace', string="Espace parent",
        ondelete='cascade', index=True)
    parent_path = fields.Char(index=True)
    complete_name = fields.Char(
        compute='_compute_complete_name', store=True, recursive=True,
        string="Nom complet")
    child_ids = fields.One2many('oski.dms.workspace', 'parent_id', string="Sous-espaces")

    read_group_ids = fields.Many2many(
        'res.groups', 'oski_dms_ws_read_group_rel', 'ws_id', 'group_id',
        string="Groupes lecture")
    write_group_ids = fields.Many2many(
        'res.groups', 'oski_dms_ws_write_group_rel', 'ws_id', 'group_id',
        string="Groupes écriture")
    manage_group_ids = fields.Many2many(
        'res.groups', 'oski_dms_ws_manage_group_rel', 'ws_id', 'group_id',
        string="Groupes gestion")

    # NOTE(Task 1→3): `oski.dms.document` n'existe pas encore (créé en Task 3).
    # Un One2many vers un comodel absent du registre fait planter le chargement
    # du module (assertion ORM sur `comodel_name` — voir odoo/orm/fields_relational.py,
    # setup_nonrelated). `document_ids` sera ajouté ici en Task 3, en même temps
    # que le modèle document ; `document_count` restera à 0 en attendant.
    document_count = fields.Integer(
        compute='_compute_document_count', string="Nb documents")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string="Société", default=lambda s: s.env.company)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for ws in self:
            if ws.parent_id:
                ws.complete_name = f"{ws.parent_id.complete_name} / {ws.name}"
            else:
                ws.complete_name = ws.name

    @api.depends()
    def _compute_document_count(self):
        # Placeholder Task 1 : recalculé sur `document_ids` dès Task 3.
        for ws in self:
            ws.document_count = 0
