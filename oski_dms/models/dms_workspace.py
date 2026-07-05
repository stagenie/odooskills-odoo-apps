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

    document_ids = fields.One2many(
        'oski.dms.document', 'workspace_id', string="Documents")
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

    @api.depends('document_ids')
    def _compute_document_count(self):
        for ws in self:
            ws.document_count = len(ws.document_ids)
