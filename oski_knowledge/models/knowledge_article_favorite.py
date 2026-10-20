from odoo import api, fields, models


class KnowledgeArticleFavorite(models.Model):
    _name = 'knowledge.article.favorite'
    _description = "Favori d'article"
    _order = 'sequence, id'

    user_id = fields.Many2one(
        'res.users', string="Utilisateur", required=True, ondelete='cascade',
        default=lambda self: self.env.user, index=True)
    article_id = fields.Many2one(
        'knowledge.article', string="Article", required=True,
        ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ('unique_user_article', 'UNIQUE (user_id, article_id)',
         "Cet article est déjà dans vos favoris."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        # Un favori ne peut viser qu'un article LISIBLE par l'appelant : sinon
        # un id d'article privé d'autrui suffit à lire son titre via
        # article_id (display_name du Many2one lu en sudo).
        article_ids = {vals['article_id'] for vals in vals_list if vals.get('article_id')}
        if article_ids:
            self.env['knowledge.article'].browse(article_ids).check_access('read')
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('article_id'):
            self.env['knowledge.article'].browse(vals['article_id']).check_access('read')
        return super().write(vals)
