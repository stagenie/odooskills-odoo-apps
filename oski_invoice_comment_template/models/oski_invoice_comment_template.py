# -*- coding: utf-8 -*-
from odoo import fields, models


class OskiInvoiceCommentTemplate(models.Model):
    """Modèle de remarque réutilisable inséré dans la narration d'une facture.

    La narration (`account.move.narration`) est imprimée nativement dans le
    PDF de la facture : aucun héritage de rapport n'est donc nécessaire.
    """

    _name = "oski.invoice.comment.template"
    _description = "Modèle de remarque de facture"
    _order = "sequence, name"

    name = fields.Char(string="Nom", required=True)
    body = fields.Html(string="Remarque", required=True, sanitize=True)
    sequence = fields.Integer(string="Séquence", default=10)
    active = fields.Boolean(string="Actif", default=True)
    move_types = fields.Selection(
        selection=[
            ("out", "Factures clients"),
            ("in", "Factures fournisseurs"),
            ("all", "Toutes"),
        ],
        string="Types de facture",
        default="all",
        required=True,
    )
