# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    oski_comment_template_id = fields.Many2one(
        comodel_name="oski.invoice.comment.template",
        string="Modèle de remarque",
        copy=False,
        domain="[('move_types', 'in', ('all', oski_comment_direction))]",
    )
    oski_comment_direction = fields.Selection(
        selection=[("out", "Client"), ("in", "Fournisseur")],
        string="Sens de la facture (remarques)",
        compute="_compute_oski_comment_direction",
        help="Sert à ne proposer que les modèles prévus pour ce type de facture.",
    )

    @api.depends("move_type")
    def _compute_oski_comment_direction(self):
        for move in self:
            if move.move_type in ("out_invoice", "out_refund"):
                move.oski_comment_direction = "out"
            elif move.move_type in ("in_invoice", "in_refund"):
                move.oski_comment_direction = "in"
            else:
                move.oski_comment_direction = False

    @api.constrains("oski_comment_template_id", "move_type")
    def _check_oski_comment_template_direction(self):
        """Un modèle réservé aux factures clients ne se pose pas sur une
        facture fournisseur, et inversement : le champ `move_types` du modèle
        n'aurait sinon aucun effet."""
        for move in self:
            template = move.oski_comment_template_id
            if template and template.move_types != "all" \
                    and template.move_types != move.oski_comment_direction:
                raise ValidationError(_(
                    "Le modèle de remarque « %(template)s » est réservé aux %(types)s.",
                    template=template.name,
                    types=dict(template._fields["move_types"]._description_selection(
                        self.env))[template.move_types].lower(),
                ))

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
