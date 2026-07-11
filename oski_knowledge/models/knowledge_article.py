from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext


class KnowledgeArticle(models.Model):
    _name = 'knowledge.article'
    _description = 'Article'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _parent_store = True
    _order = 'sequence, id'

    name = fields.Char(
        string="Titre", required=True, default="Nouvel article", tracking=True)
    icon = fields.Char(string="Icône", default="📄")
    body = fields.Html(string="Contenu")
    body_text = fields.Text(
        string="Texte", compute='_compute_body_text', store=True)
    parent_id = fields.Many2one(
        'knowledge.article', string="Article parent",
        ondelete='cascade', index=True)
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'knowledge.article', 'parent_id', string="Sous-articles")
    root_article_id = fields.Many2one(
        'knowledge.article', string="Article racine",
        compute='_compute_root_article_id', store=True, recursive=True)
    section = fields.Selection(
        [('workspace', "Espace de travail"), ('private', "Privé")],
        string="Espace", required=True, default='workspace',
        compute='_compute_section', store=True, readonly=False, recursive=True)
    owner_id = fields.Many2one(
        'res.users', string="Propriétaire", required=True, tracking=True,
        default=lambda self: self.env.user)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    child_count = fields.Integer(
        string="Nombre de sous-articles", compute='_compute_child_count')

    @api.depends('body')
    def _compute_body_text(self):
        for article in self:
            article.body_text = html2plaintext(article.body) if article.body else False

    @api.depends('parent_path')
    def _compute_root_article_id(self):
        for article in self:
            if article.parent_path:
                article.root_article_id = int(article.parent_path.split('/')[0])
            else:
                article.root_article_id = article.id

    @api.depends('parent_id', 'parent_id.section')
    def _compute_section(self):
        for article in self:
            if article.parent_id:
                article.section = article.parent_id.section
            elif not article.section:
                article.section = 'workspace'

    @api.depends('child_ids')
    def _compute_child_count(self):
        for article in self:
            article.child_count = len(article.child_ids)

    def write(self, vals):
        if 'parent_id' in vals and vals['parent_id']:
            for article in self:
                new_parent = self.browse(vals['parent_id'])
                # Check if new_parent is a descendant of article
                current = new_parent
                while current:
                    if current.id == article.id:
                        raise ValidationError(
                            self.env._("Un article ne peut pas être son propre ancêtre."))
                    current = current.parent_id
        return super().write(vals)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        for article in self:
            if article.parent_id:
                parent = article.parent_id
                while parent:
                    if parent.id == article.id:
                        raise ValidationError(
                            self.env._("Un article ne peut pas être son propre ancêtre."))
                    parent = parent.parent_id

    @api.constrains('section', 'owner_id')
    def _check_private_owner(self):
        for article in self:
            if article.section == 'private' and not article.owner_id:
                raise ValidationError(
                    self.env._("Un article privé doit avoir un propriétaire."))
