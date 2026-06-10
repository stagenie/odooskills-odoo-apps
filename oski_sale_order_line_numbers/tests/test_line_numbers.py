# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestOskiLineNumbers(TransactionCase):
    """Vérifie la numérotation automatique des lignes de commande."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Client Test Oski"})
        cls.products = cls.env["product.product"].create([
            {"name": "Produit A Oski"},
            {"name": "Produit B Oski"},
            {"name": "Produit C Oski"},
        ])

    def _new_order(self):
        return self.env["sale.order"].create({"partner_id": self.partner.id})

    def _product_line_vals(self, product, sequence):
        return {
            "product_id": product.id,
            "product_uom_qty": 1.0,
            "sequence": sequence,
        }

    def test_three_product_lines_numbered_1_2_3(self):
        """Trois lignes produit -> numéros 1, 2, 3 dans l'ordre sequence, id."""
        order = self._new_order()
        order.write({
            "order_line": [
                (0, 0, self._product_line_vals(self.products[0], 10)),
                (0, 0, self._product_line_vals(self.products[1], 20)),
                (0, 0, self._product_line_vals(self.products[2], 30)),
            ]
        })

        numbers = order.order_line.sorted(lambda l: (l.sequence, l.id)).mapped(
            "oski_line_number"
        )
        self.assertEqual(
            numbers, [1, 2, 3],
            "Les trois lignes produit doivent être numérotées 1, 2, 3.",
        )

    def test_sections_and_notes_excluded(self):
        """Section + note insérées -> display_type = 0, produits restent 1..3."""
        order = self._new_order()
        order.write({
            "order_line": [
                (0, 0, {"display_type": "line_section", "name": "Section 1", "sequence": 5}),
                (0, 0, self._product_line_vals(self.products[0], 10)),
                (0, 0, {"display_type": "line_note", "name": "Une note", "sequence": 15}),
                (0, 0, self._product_line_vals(self.products[1], 20)),
                (0, 0, self._product_line_vals(self.products[2], 30)),
            ]
        })

        product_lines = order.order_line.filtered(lambda l: not l.display_type)
        display_lines = order.order_line.filtered(lambda l: l.display_type)

        self.assertEqual(
            display_lines.mapped("oski_line_number"), [0, 0],
            "Les lignes section/note doivent avoir le numéro 0.",
        )
        product_numbers = product_lines.sorted(
            lambda l: (l.sequence, l.id)
        ).mapped("oski_line_number")
        self.assertEqual(
            product_numbers, [1, 2, 3],
            "Les lignes produit doivent rester numérotées 1, 2, 3 malgré les sections/notes.",
        )

    def test_resequence_renumbers(self):
        """Inversion des sequence -> la numérotation suit le nouvel ordre."""
        order = self._new_order()
        order.write({
            "order_line": [
                (0, 0, self._product_line_vals(self.products[0], 10)),
                (0, 0, self._product_line_vals(self.products[1], 20)),
                (0, 0, self._product_line_vals(self.products[2], 30)),
            ]
        })

        line_a = order.order_line.filtered(
            lambda l: l.product_id == self.products[0]
        )
        line_c = order.order_line.filtered(
            lambda l: l.product_id == self.products[2]
        )

        # Inversion : A passe en dernier, C passe en premier.
        line_a.sequence = 50
        line_c.sequence = 1

        self.assertEqual(
            line_c.oski_line_number, 1,
            "La ligne déplacée en tête doit prendre le numéro 1.",
        )
        self.assertEqual(
            line_a.oski_line_number, 3,
            "La ligne déplacée en fin doit prendre le numéro 3.",
        )
