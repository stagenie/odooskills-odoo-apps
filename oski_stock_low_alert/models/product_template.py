# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Libellé unique de l'activité d'alerte : sert aussi de clé d'anti-doublon.
ALERT_SUMMARY = "Stock bas"


class ProductTemplate(models.Model):
    _inherit = "product.template"

    oski_alert_threshold = fields.Float(
        string="Seuil d'alerte stock",
        default=0.0,
        help="En dessous de cette quantité disponible, le produit est signalé "
        "en stock bas. Laisser à 0 pour désactiver l'alerte.",
    )
    # Non stocké : qty_available est calculé dynamiquement par le module stock,
    # le stocker produirait des valeurs périmées dès qu'un mouvement a lieu.
    oski_low_stock = fields.Boolean(
        string="Stock bas",
        compute="_compute_oski_low_stock",
        search="_search_oski_low_stock",
        help="Vrai lorsqu'un seuil est défini et que la quantité disponible "
        "est strictement inférieure à ce seuil.",
    )

    @api.depends("oski_alert_threshold", "qty_available")
    def _compute_oski_low_stock(self):
        for product in self:
            threshold = product.oski_alert_threshold
            product.oski_low_stock = bool(
                threshold > 0 and product.qty_available < threshold
            )

    def _search_oski_low_stock(self, operator, value):
        """Recherche en deux temps : pré-filtre SQL sur le seuil, puis filtre
        Python sur qty_available (champ calculé non stocké, non interrogeable
        directement en SQL)."""
        if operator not in ("=", "!="):
            raise NotImplementedError(
                "Opérateur non supporté pour oski_low_stock : %s" % operator
            )

        # Normalise la requête en "produits réellement en stock bas".
        looking_for_low = (operator == "=") == bool(value)

        candidates = self.search([("oski_alert_threshold", ">", 0)])
        low_ids = candidates.filtered(
            lambda p: p.qty_available < p.oski_alert_threshold
        ).ids

        if looking_for_low:
            return [("id", "in", low_ids)]
        return [("id", "not in", low_ids)]

    def _oski_low_stock_responsible(self):
        """Retourne l'utilisateur destinataire de l'activité : premier
        responsable de stock, sinon l'administrateur."""
        # En v18, le champ inverse de res.groups vers les utilisateurs est
        # « users » (renommé « user_ids » en v19).
        managers = self.env.ref("stock.group_stock_manager").users
        manager = managers[:1]
        if manager:
            return manager
        return self.env.ref("base.user_admin")

    @api.model
    def _oski_cron_low_stock_alert(self):
        """Cron quotidien : planifie une activité « à faire » sur chaque produit
        en stock bas pour le responsable de stock, sans créer de doublon."""
        low_products = self.search([("oski_low_stock", "=", True)])
        if not low_products:
            return

        responsible = self._oski_low_stock_responsible()
        existing = self.env["mail.activity"].search([
            ("res_model", "=", self._name),
            ("res_id", "in", low_products.ids),
            ("summary", "=", ALERT_SUMMARY),
        ])
        already_flagged = set(existing.mapped("res_id"))

        for product in low_products:
            if product.id in already_flagged:
                continue

            note = (
                "Le produit « %s » est passé sous son seuil d'alerte "
                "(disponible : %s, seuil : %s)."
                % (
                    product.display_name,
                    product.qty_available,
                    product.oski_alert_threshold,
                )
            )
            product.activity_schedule(
                "mail.mail_activity_data_todo",
                summary=ALERT_SUMMARY,
                note=note,
                user_id=responsible.id,
            )
