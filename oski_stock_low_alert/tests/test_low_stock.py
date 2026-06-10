# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOskiLowStock(TransactionCase):
    """Tests de l'alerte de stock bas par produit."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ProductTemplate = cls.env["product.template"]
        # Emplacement de stock interne (WH/Stock).
        cls.stock_location = cls.env.ref("stock.stock_location_stock")

    def _make_product(self, name, threshold, qty):
        """Crée un produit stockable avec une quantité en stock donnée."""
        template = self.ProductTemplate.create({
            "name": name,
            # En v17 le produit stockable se définit via detailed_type='product'
            # (le champ is_storable n'existe qu'à partir de la v18).
            "detailed_type": "product",
            "oski_alert_threshold": threshold,
        })
        if qty:
            self.env["stock.quant"].create({
                "product_id": template.product_variant_id.id,
                "location_id": self.stock_location.id,
                "quantity": qty,
            })
        return template

    def test_low_stock_compute(self):
        """Seuil 10 + qty 0 => stock bas ; seuil 0 => jamais en alerte."""
        low = self._make_product("Produit alerte", threshold=10.0, qty=0.0)
        self.assertTrue(low.oski_low_stock, "Le produit sous le seuil doit être en alerte")

        disabled = self._make_product("Produit sans seuil", threshold=0.0, qty=0.0)
        self.assertFalse(
            disabled.oski_low_stock,
            "Un seuil à 0 désactive l'alerte même à quantité nulle",
        )

    def test_low_stock_above_threshold(self):
        """Quantité au-dessus du seuil => pas d'alerte."""
        ok = self._make_product("Produit fourni", threshold=5.0, qty=20.0)
        self.assertFalse(ok.oski_low_stock, "Stock supérieur au seuil => pas d'alerte")

    def test_search_low_stock(self):
        """Le search retourne uniquement les produits réellement en alerte."""
        low = self._make_product("Bas search", threshold=10.0, qty=2.0)
        high = self._make_product("Haut search", threshold=10.0, qty=50.0)
        disabled = self._make_product("Off search", threshold=0.0, qty=0.0)

        found = self.ProductTemplate.search([("oski_low_stock", "=", True)])
        self.assertIn(low, found, "Le produit en alerte doit être trouvé")
        self.assertNotIn(high, found, "Le produit bien fourni ne doit pas être trouvé")
        self.assertNotIn(disabled, found, "Le produit sans seuil ne doit pas être trouvé")

        # Recherche inverse.
        not_low = self.ProductTemplate.search([("oski_low_stock", "=", False)])
        self.assertNotIn(low, not_low)
        self.assertIn(high, not_low)
        self.assertIn(disabled, not_low)

    def test_cron_creates_activity_and_no_duplicate(self):
        """Le cron crée 1 activité ; une seconde exécution n'en recrée pas."""
        low = self._make_product("Cron bas", threshold=10.0, qty=1.0)

        self.ProductTemplate._oski_cron_low_stock_alert()
        activities = self.env["mail.activity"].search([
            ("res_model", "=", "product.template"),
            ("res_id", "=", low.id),
            ("summary", "=", "Stock bas"),
        ])
        self.assertEqual(len(activities), 1, "Une activité doit être créée pour le produit bas")

        # Anti-doublon : relancer ne doit pas créer de seconde activité.
        self.ProductTemplate._oski_cron_low_stock_alert()
        activities = self.env["mail.activity"].search([
            ("res_model", "=", "product.template"),
            ("res_id", "=", low.id),
            ("summary", "=", "Stock bas"),
        ])
        self.assertEqual(len(activities), 1, "Le cron ne doit pas créer de doublon")
