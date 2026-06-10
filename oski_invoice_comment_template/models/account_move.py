# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    oski_comment_template_id = fields.Many2one(
        comodel_name="oski.invoice.comment.template",
        string="Modèle de remarque",
        copy=False,
    )

    def _oski_apply_comment_template(self):
        """Recopie le corps du modèle sélectionné dans la narration.

        Lorsqu'un modèle est choisi, sa remarque remplace la narration afin
        d'être imprimée dans le PDF. Retirer le modèle ne vide pas la
        narration : le texte déjà inséré est conservé.
        """
        for move in self:
            if move.oski_comment_template_id:
                move.narration = move.oski_comment_template_id.body

    @api.onchange("oski_comment_template_id")
    def _onchange_oski_comment_template_id(self):
        self._oski_apply_comment_template()

    def action_oski_apply_comment_template(self):
        """Applique le modèle de remarque (même logique que l'onchange).

        Exposée pour un usage programmatique et pour les tests.
        """
        self._oski_apply_comment_template()
        return True
