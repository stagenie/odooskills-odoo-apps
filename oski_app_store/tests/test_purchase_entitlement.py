"""Le droit de téléchargement né d'un achat, et sa traduction à l'écran.

Le trou couvert ici : avant, un acheteur revoyait « Acheter » sur la fiche
qu'il venait de payer, et rien ne le menait à son archive.
"""
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestPurchaseEntitlement(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

        cls.buyer = cls.env["res.users"].create(
            {
                "name": "Acheteur Test",
                "login": "oski_buyer",
                "password": "oski_buyer_pwd",
                "email": "buyer@example.com",
                "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
            }
        )

    def _ver(self, name="19.0"):
        rec = self.env["oski.odoo.version"].search([("name", "=", name)], limit=1)
        if not rec:
            raise ValueError("oski.odoo.version %r absente du référentiel" % name)
        return rec

    def _make_paid_module(self, technical_name, price=49.0, published=True,
                          product_published=True):
        """Module payant complet : produit lié, version 19.0 et archive."""
        product = self.env["product.template"].create(
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
                "product_tmpl_id": product.id,
            }
        )
        version = self.env["oski.module.version"].create(
            {
                "module_id": module.id,
                "odoo_version_id": self._ver().id,
                "module_version": "19.0.1.0.0",
                "attachment_id": attachment.id,
            }
        )
        return module, version

    def _confirm_order(self, module, partner):
        """Commande confirmée : c'est elle, et pas le devis, qui ouvre le droit."""
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": module.product_tmpl_id.product_variant_id.id,
                            "product_uom_qty": 1,
                        },
                    )
                ],
            }
        )
        order.action_confirm()
        return order

    # --- règle d'entitlement ------------------------------------------------

    def test_not_purchased_without_order(self):
        module, _ = self._make_paid_module("oski_ent_none")
        self.assertFalse(module.is_purchased_by(self.buyer.partner_id))

    def test_quotation_does_not_entitle(self):
        """Un devis non confirmé ne donne aucun droit."""
        module, _ = self._make_paid_module("oski_ent_quote")
        self.env["sale.order"].create(
            {
                "partner_id": self.buyer.partner_id.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": module.product_tmpl_id.product_variant_id.id,
                            "product_uom_qty": 1,
                        },
                    )
                ],
            }
        )
        self.assertFalse(module.is_purchased_by(self.buyer.partner_id))

    def test_confirmed_order_entitles(self):
        module, _ = self._make_paid_module("oski_ent_sale")
        self._confirm_order(module, self.buyer.partner_id)
        self.assertTrue(module.is_purchased_by(self.buyer.partner_id))

    def test_entitlement_is_per_partner(self):
        """L'achat d'un client n'ouvre aucun droit à un autre."""
        module, _ = self._make_paid_module("oski_ent_other")
        other = self.env["res.partner"].create({"name": "Tiers"})
        self._confirm_order(module, self.buyer.partner_id)
        self.assertFalse(module.is_purchased_by(other))

    def test_free_module_always_entitled(self):
        module = self.env["oski.module"].create(
            {"name": "oski_ent_free", "technical_name": "oski_ent_free"}
        )
        self.assertTrue(module.is_purchased_by(self.env["res.partner"]))

    def test_purchased_by_lists_only_bought_modules(self):
        bought, _ = self._make_paid_module("oski_ent_list_yes")
        other, _ = self._make_paid_module("oski_ent_list_no")
        self._confirm_order(bought, self.buyer.partner_id)
        modules = self.env["oski.module"].purchased_by(self.buyer.partner_id)
        self.assertIn(bought, modules)
        self.assertNotIn(other, modules)

    # --- traduction à l'écran ----------------------------------------------

    def test_page_shows_buy_button_with_price(self):
        module, _ = self._make_paid_module("oski_cta_buy", price=49.0)
        self.authenticate(None, None)
        body = self.url_open(module.website_url).text
        self.assertIn("Acheter", body)
        self.assertIn("49", body)

    def test_page_swaps_to_download_once_bought(self):
        """Le trou historique : « Acheter » restait affiché après paiement."""
        module, _ = self._make_paid_module("oski_cta_owned")
        self._confirm_order(module, self.buyer.partner_id)
        self.authenticate("oski_buyer", "oski_buyer_pwd")
        body = self.url_open(module.website_url).text
        self.assertIn("Télécharger", body)
        self.assertNotIn("oski-btn-buy", body)

    def test_paid_module_without_product_shows_no_dead_button(self):
        """Sans produit lié, le bouton d'achat mènerait à un panier vide."""
        module, _ = self._make_paid_module("oski_cta_orphan")
        module.product_tmpl_id = False
        self.authenticate(None, None)
        body = self.url_open(module.website_url).text
        self.assertIn("Bientôt en vente", body)
        self.assertNotIn("/shop/cart/update?product_id=False", body)

    def test_paid_module_with_unpublished_product_is_not_sellable(self):
        """État d'avant go-live : le produit existe mais n'est pas publié.

        Proposer « Acheter » enverrait l'acheteur sur un panier qui refuse le
        produit ; la fiche annonce l'ouverture prochaine.
        """
        module, _ = self._make_paid_module("oski_cta_unpub", product_published=False)
        self.authenticate(None, None)
        body = self.url_open(module.website_url).text
        self.assertIn("Bientôt en vente", body)
        self.assertNotIn("oski-btn-buy", body)

    def test_paid_module_page_is_readable_by_public(self):
        """Régression : la fiche d'un module payant rendait 403 au public.

        `product.template` est illisible pour l'utilisateur public ; la page la
        touchait directement. Le produit doit être résolu en sudo.
        """
        module, _ = self._make_paid_module("oski_cta_public")
        self.authenticate(None, None)
        resp = self.url_open(module.website_url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("403: Forbidden", resp.text)

    # --- espace client ------------------------------------------------------

    def test_portal_lists_purchased_module(self):
        module, version = self._make_paid_module("oski_portal_owned")
        self._confirm_order(module, self.buyer.partner_id)
        self.authenticate("oski_buyer", "oski_buyer_pwd")
        resp = self.url_open("/my/apps")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("oski_portal_owned", resp.text)
        self.assertIn("/apps/download/%s" % version.id, resp.text)

    def test_portal_hides_unbought_module(self):
        module, _ = self._make_paid_module("oski_portal_unbought")
        self.authenticate("oski_buyer", "oski_buyer_pwd")
        self.assertNotIn("oski_portal_unbought", self.url_open("/my/apps").text)

    def test_portal_requires_login(self):
        self.authenticate(None, None)
        resp = self.url_open("/my/apps", allow_redirects=False)
        self.assertIn(resp.status_code, (302, 303))

    def test_buyer_downloads_paid_archive(self):
        """Bout de chaîne : la commande confirmée sert réellement le zip."""
        module, version = self._make_paid_module("oski_dl_owned")
        self._confirm_order(module, self.buyer.partner_id)
        self.authenticate("oski_buyer", "oski_buyer_pwd")
        resp = self.url_open("/apps/download/%s" % version.id)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"ZIPDATA")

    def test_non_buyer_is_redirected(self):
        module, version = self._make_paid_module("oski_dl_stranger")
        self.authenticate("oski_buyer", "oski_buyer_pwd")
        resp = self.url_open(
            "/apps/download/%s" % version.id, allow_redirects=False
        )
        self.assertIn(resp.status_code, (302, 303))
