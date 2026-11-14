# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Le libellé de l'activité d'alerte sert aussi de clé d'anti-doublon : il est
# cherché dans chaque langue installée (``_oski_alert_summaries``).


class ProductTemplate(models.Model):
    _inherit = "product.template"

    oski_alert_threshold = fields.Float(
        string="Stock Alert Threshold",
        default=0.0,
        help="Below this available quantity, the product is flagged as low on "
        "stock. Leave at 0 to disable the alert.",
    )
    # Non stocké : qty_available est calculé dynamiquement par le module stock,
    # le stocker produirait des valeurs périmées dès qu'un mouvement a lieu.
    oski_low_stock = fields.Boolean(
        string="Low Stock",
        compute="_compute_oski_low_stock",
        search="_search_oski_low_stock",
        help="True when a threshold is set and the available quantity is "
        "strictly below it.",
    )

    @api.depends("oski_alert_threshold", "qty_available", "is_storable")
    def _compute_oski_low_stock(self):
        # Seuls les produits suivis en stock ont une quantité disponible qui
        # veut dire quelque chose : un consommable non suivi est toujours à 0
        # et serait en alerte permanente.
        for product in self:
            threshold = product.oski_alert_threshold
            product.oski_low_stock = bool(
                product.is_storable
                and threshold > 0
                and product.qty_available < threshold
            )

    def _search_oski_low_stock(self, operator, value):
        """Recherche en deux temps : pré-filtre SQL sur le seuil, puis filtre
        Python sur qty_available (champ calculé non stocké, non interrogeable
        directement en SQL)."""
        if operator not in ("=", "!="):
            raise NotImplementedError(
                "Unsupported operator for oski_low_stock: %s" % operator
            )

        # Normalise la requête en "produits réellement en stock bas".
        looking_for_low = (operator == "=") == bool(value)

        candidates = self.search([
            ("oski_alert_threshold", ">", 0),
            ("is_storable", "=", True),
        ])
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
    def _oski_alert_summaries(self):
        """Le libellé de l'alerte dans chaque langue installée.

        Il sert de clé d'anti-doublon : une activité posée quand le
        responsable lisait une autre langue doit encore être reconnue.
        """
        codes = {code for code, _label in self.env["res.lang"].get_installed()}
        return sorted({
            self.with_context(lang=code).env._("Low Stock")
            for code in codes | {"en_US"}})

    @api.model
    def _oski_cron_low_stock_alert(self):
        """Cron quotidien : planifie une activité « à faire » sur chaque produit
        en stock bas pour le responsable de stock, sans créer de doublon."""
        low_products = self.search([("oski_low_stock", "=", True)])
        if not low_products:
            return

        responsible = self._oski_low_stock_responsible()
        # La tâche planifiée tourne sans langue : l'activité est écrite dans
        # celle du responsable, qui la lit.
        reader = self.with_context(lang=responsible.lang or self.env.lang)
        existing = self.env["mail.activity"].search([
            ("res_model", "=", self._name),
            ("res_id", "in", low_products.ids),
            ("summary", "in", self._oski_alert_summaries()),
        ])
        already_flagged = set(existing.mapped("res_id"))

        for product in low_products:
            if product.id in already_flagged:
                continue

            note = reader.env._(
                "Product “%(product)s” fell below its alert threshold "
                "(available: %(available)s, threshold: %(threshold)s).",
                product=product.with_context(lang=reader.env.lang).display_name,
                available=product.qty_available,
                threshold=product.oski_alert_threshold,
            )
            product.activity_schedule(
                "mail.mail_activity_data_todo",
                summary=reader.env._("Low Stock"),
                note=note,
                user_id=responsible.id,
            )
