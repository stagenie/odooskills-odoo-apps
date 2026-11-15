# -*- coding: utf-8 -*-
from odoo import fields, models


class OskiInvoiceCommentTemplate(models.Model):
    """Modèle de remarque réutilisable inséré dans la narration d'une facture.

    La narration (`account.move.narration`) est imprimée nativement dans le
    PDF de la facture : aucun héritage de rapport n'est donc nécessaire.
    """

    _name = "oski.invoice.comment.template"
    _description = "Invoice Note Template"
    _order = "sequence, name"

    name = fields.Char(string="Name", required=True)
    body = fields.Html(string="Note", required=True, sanitize=True)
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)
    move_types = fields.Selection(
        selection=[
            ("out", "Customer Invoices"),
            ("in", "Vendor Bills"),
            ("all", "All"),
        ],
        string="Invoice Types",
        default="all",
        required=True,
    )
