# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    oski_line_number = fields.Integer(
        string="N°",
        compute="_compute_oski_line_number",
        store=True,
        help="Numéro d'ordre 1..n des lignes produit de la commande. "
        "Les sections et notes ne sont pas numérotées (0).",
    )

    @api.depends(
        "order_id.order_line",
        "order_id.order_line.sequence",
        "display_type",
    )
    def _compute_oski_line_number(self):
        """Numérote 1..n les lignes produit de chaque commande.

        L'ordre suit ``sequence, id`` (l'ordre d'affichage). Les lignes
        techniques (sections, sous-sections, notes) portant un ``display_type``
        sont exclues du comptage et reçoivent le numéro 0.
        """
        # On regroupe par commande pour numéroter chaque devis indépendamment.
        orders = self.mapped("order_id")
        for order in orders:
            counter = 0

            # On parcourt TOUTES les lignes de la commande dans l'ordre
            # d'affichage afin que le compteur reste cohérent même si seul un
            # sous-ensemble de lignes est recalculé.
            ordered_lines = order.order_line.sorted(
                key=lambda line: (line.sequence, line.id or 0)
            )
            for line in ordered_lines:
                if line.display_type:
                    line.oski_line_number = 0
                    continue

                counter += 1
                line.oski_line_number = counter

        # Filet de sécurité : une ligne sans commande (cas transitoire en
        # création) reçoit tout de même une valeur déterministe.
        for line in self.filtered(lambda l: not l.order_id):
            line.oski_line_number = 0
