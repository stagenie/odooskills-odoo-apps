"""Le bouton « Acheter » doit vraiment remplir le panier.

Le trou couvert ici : la fiche pointait sur `/shop/cart/update?product_id=…`,
qui en Odoo 19 est une route **jsonrpc en POST**. Un lien GET n'y ajoutait
rien — le visiteur atterrissait sur « Votre panier est vide ! » sans le
moindre message d'erreur, et aucune vente n'était possible.
"""
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestBuyRoute(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def _ver(self, name="19.0"):
        rec = self.env["oski.odoo.version"].search([("name", "=", name)], limit=1)
        if not rec:
            raise ValueError("oski.odoo.version %r absente du référentiel" % name)
        return rec

    def _make_paid_module(self, technical_name, price=1.0, published=True,
                          product_published=True, with_product=True):
        product = self.env["product.template"]
        if with_product:
            product = product.create(
                {
                    "name": technical_name,
                    "type": "service",
                    "list_price": price,
                    "taxes_id": [(6, 0, [])],
                    "is_published": product_published,
                }
            )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "%s.zip" % technical_name,
                "raw": b"ZIPDATA",
                "mimetype": "application/zip",
            }
        )
        module = self.env["oski.module"].create(
            {
                "name": technical_name,
                "technical_name": technical_name,
                "is_free": False,
                "is_published": published,
                "price": price,
                "product_tmpl_id": product.id if product else False,
            }
        )
        self.env["oski.module.version"].create(
            {
                "module_id": module.id,
                "odoo_version_id": self._ver().id,
                "module_version": "19.0.1.0.0",
                "attachment_id": attachment.id,
            }
        )
        return module, product

    def _cart_lines(self, product):
        """Lignes de panier portant ce produit, toutes commandes confondues.

        On interroge l'ORM plutôt que le texte de la page : la base de test est
        en anglais et un « Votre panier est vide » n'y apparaîtrait jamais.
        """
        return self.env["sale.order.line"].search(
            [("product_id.product_tmpl_id", "=", product.id)]
        )

    # --- le panier se remplit vraiment -------------------------------------

    def test_buy_route_fills_the_cart(self):
        module, product = self._make_paid_module("oski_buy_ok")
        self.authenticate(None, None)
        resp = self.url_open("/apps/buy/%s" % module.id)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.url.endswith("/shop/cart"), resp.url)
        lines = self._cart_lines(product)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.product_uom_qty, 1)
        self.assertEqual(lines.order_id.state, "draft")

    def test_buy_route_is_idempotent(self):
        """Un rafraîchissement ne doit pas facturer le module deux fois."""
        module, product = self._make_paid_module("oski_buy_twice")
        self.authenticate(None, None)
        self.url_open("/apps/buy/%s" % module.id)
        self.url_open("/apps/buy/%s" % module.id)
        order = self.env["sale.order"].search(
            [("order_line.product_id.product_tmpl_id", "=", product.id)], limit=1
        )
        self.assertTrue(order)
        line = order.order_line.filtered(
            lambda sol: sol.product_id.product_tmpl_id == product
        )
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_uom_qty, 1)

    # --- refus ---------------------------------------------------------------

    def test_buy_route_refuses_unpublished_module(self):
        module, _ = self._make_paid_module("oski_buy_unpub_mod", published=False)
        self.authenticate(None, None)
        resp = self.url_open("/apps/buy/%s" % module.id)
        self.assertEqual(resp.status_code, 404)

    def test_buy_route_refuses_unpublished_product(self):
        module, product = self._make_paid_module(
            "oski_buy_unpub_prod", product_published=False
        )
        self.authenticate(None, None)
        resp = self.url_open("/apps/buy/%s" % module.id)
        self.assertTrue(resp.url.rstrip("/").endswith(module.website_url), resp.url)
        self.assertFalse(self._cart_lines(product))

    def test_buy_route_refuses_module_without_product(self):
        module, _ = self._make_paid_module("oski_buy_orphan", with_product=False)
        self.authenticate(None, None)
        resp = self.url_open("/apps/buy/%s" % module.id)
        self.assertTrue(resp.url.rstrip("/").endswith(module.website_url), resp.url)

    def test_buy_route_404_on_unknown_module(self):
        self.authenticate(None, None)
        self.assertEqual(self.url_open("/apps/buy/999999").status_code, 404)

    # --- la fiche pointe sur la bonne route ---------------------------------

    def test_page_button_uses_buy_route(self):
        module, _ = self._make_paid_module("oski_buy_cta")
        self.authenticate(None, None)
        body = self.url_open(module.website_url).text
        self.assertIn("/apps/buy/%s" % module.id, body)
        self.assertNotIn("/shop/cart/update", body)

    # --- la mention de possession ne vaut que pour un module payé ----------

    def test_free_module_does_not_claim_to_be_owned(self):
        """`is_purchased_by()` répond True d'office sur un module gratuit.

        La fiche en tirait « Vous possédez ce module — toutes vos applications »,
        montrée à n'importe quel visiteur anonyme, avec un lien vers un portail
        qui lui demanderait de se connecter.
        """
        module, product = self._make_paid_module("oski_free_owned")
        module.write({"is_free": True, "price": 0.0})
        self.authenticate(None, None)
        body = self.url_open(module.website_url).text
        self.assertIn("oski-btn-download", body)
        self.assertNotIn("oski-owned-note", body)

    def test_paid_module_still_claims_ownership_once_bought(self):
        buyer = self.env["res.users"].create(
            {
                "name": "Acheteur Route",
                "login": "oski_buy_owner",
                "password": "oski_buy_owner_pwd",
                "email": "owner@example.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        module, product = self._make_paid_module("oski_paid_owned")
        order = self.env["sale.order"].create(
            {
                "partner_id": buyer.partner_id.id,
                "order_line": [
                    (0, 0, {"product_id": product.product_variant_id.id, "product_uom_qty": 1})
                ],
            }
        )
        order.action_confirm()
        self.authenticate("oski_buy_owner", "oski_buy_owner_pwd")
        body = self.url_open(module.website_url).text
        self.assertIn("oski-owned-note", body)
