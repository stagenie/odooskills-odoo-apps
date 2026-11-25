"""Les paniers anonymes abandonnés ne s'accumulent plus en devis brouillons."""
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAnonymousCartPurge(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env["website"].search([], limit=1)
        cls.public = cls.website.user_id.partner_id
        cls.product = cls.env["product.product"].create(
            {"name": "oski_purge_product", "type": "service", "list_price": 10.0}
        )
        cls.customer = cls.env["res.partner"].create({"name": "Vrai client"})

    def _order(self, partner, days_old, state="draft", website=True):
        order = self.env["sale.order"].create({
            "partner_id": partner.id,
            "website_id": self.website.id if website else False,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 1})],
        })
        if state == "sale":
            order.action_confirm()
        old = fields.Datetime.now() - timedelta(days=days_old)
        self.env.cr.execute("UPDATE sale_order SET create_date=%s WHERE id=%s", (old, order.id))
        order.invalidate_recordset(["create_date"])
        return order

    def test_purges_old_anonymous_carts_only(self):
        old_anon = self._order(self.public, 10)
        recent_anon = self._order(self.public, 1)
        customer_draft = self._order(self.customer, 10)
        backend_quote = self._order(self.public, 10, website=False)
        confirmed = self._order(self.customer, 10, state="sale")
        count = self.env["sale.order"]._cron_oski_purge_anonymous_carts()
        self.assertEqual(count, 1)
        self.assertFalse(old_anon.exists())
        self.assertTrue(recent_anon.exists())
        self.assertTrue(customer_draft.exists())
        self.assertTrue(backend_quote.exists())
        self.assertTrue(confirmed.exists())

    def test_cart_with_payment_attempt_is_kept(self):
        order = self._order(self.public, 10)
        provider = self.env["payment.provider"].search([], limit=1)
        if not provider:
            self.skipTest("aucun moyen de paiement")
        self.env["payment.transaction"].create({
            "provider_id": provider.id,
            "payment_method_id": provider.payment_method_ids[:1].id or self.env.ref("payment.payment_method_unknown").id,
            "amount": 10.0,
            "currency_id": order.currency_id.id,
            "partner_id": self.public.id,
            "reference": "oski-purge-%s" % order.id,
            "sale_order_ids": [(6, 0, order.ids)],
        })
        self.env["sale.order"]._cron_oski_purge_anonymous_carts()
        self.assertTrue(order.exists())
