from odoo import fields, models


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

    _unique_user_article = models.Constraint(
        'UNIQUE (user_id, article_id)',
        "Cet article est déjà dans vos favoris.")
