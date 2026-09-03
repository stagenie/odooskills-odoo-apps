from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAnalyticRequired(AccountTestInvoicingCommon):
    """La suite s'appuie sur le plan comptable d'essai du cœur : sans comptes
    réels, aucun préfixe ne veut rien dire."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.company_data["default_journal_purchase"]
        cls.other_journal = cls.company_data["default_journal_sale"]
        cls.plan = cls.env["account.analytic.plan"].create({"name": "Chantiers"})
        cls.analytic_account = cls.env["account.analytic.account"].create({
            "name": "Chantier Bertrand", "plan_id": cls.plan.id})
        cls.rule = cls.env["oski.analytic.journal.rule"].create({
            "journal_id": cls.journal.id})

    def _bill(self, journal=None, distribution=None):
        move = self.env["account.move"].create({
            "move_type": "in_invoice",
            "journal_id": (journal or self.journal).id,
            "partner_id": self.partner_a.id,
            "invoice_date": "2026-01-15",
            "invoice_line_ids": [(0, 0, {
                "name": "Fourniture",
                "quantity": 1,
                "price_unit": 100.0,
                "analytic_distribution": distribution,
            })],
        })
        return move

    def _distribution(self):
        return {str(self.analytic_account.id): 100}

    # -- Le blocage -------------------------------------------------------

    def test_posting_without_analytic_is_refused(self):
        move = self._bill()
        with self.assertRaises(UserError):
            move.action_post()
        self.assertEqual(move.state, "draft")

    def test_posting_with_analytic_goes_through(self):
        move = self._bill(distribution=self._distribution())
        move.action_post()
        self.assertEqual(move.state, "posted")

    def test_another_journal_is_left_alone(self):
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "journal_id": self.other_journal.id,
            "partner_id": self.partner_a.id,
            "invoice_date": "2026-01-15",
            "invoice_line_ids": [(0, 0, {
                "name": "Vente", "quantity": 1, "price_unit": 100.0})],
        })
        move.action_post()
        self.assertEqual(move.state, "posted")

    def test_an_archived_rule_blocks_nothing(self):
        self.rule.active = False
        move = self._bill()
        move.action_post()
        self.assertEqual(move.state, "posted")

    def test_the_refusal_names_the_offending_lines(self):
        move = self._bill()
        with self.assertRaises(UserError) as caught:
            move.action_post()
        self.assertIn("Fourniture", str(caught.exception))

    def test_the_counterpart_is_never_asked_for_analytic(self):
        """Le compte fournisseur solde l'écriture : il ne consomme rien."""
        move = self._bill(distribution=self._distribution())
        counterpart = move.line_ids.filtered(
            lambda line: line.account_id.account_type == "liability_payable")
        self.assertTrue(counterpart)
        self.assertFalse(counterpart.analytic_distribution)
        self.assertFalse(counterpart._oski_analytic_is_missing())

    # -- Les préfixes -----------------------------------------------------

    def test_a_prefix_narrows_the_requirement(self):
        line = self._bill().invoice_line_ids
        code = line.account_id.code
        self.rule.account_prefix = code[:2]
        self.assertTrue(line._oski_analytic_is_missing())
        self.rule.account_prefix = "999"
        line.invalidate_recordset()
        self.assertFalse(line._oski_analytic_is_missing())

    def test_several_prefixes_can_be_listed(self):
        line = self._bill().invoice_line_ids
        self.rule.account_prefix = "999, %s" % line.account_id.code[:2]
        self.assertTrue(line._oski_analytic_is_missing())

    def test_a_prefix_must_be_digits(self):
        with self.assertRaises(ValidationError):
            self.rule.account_prefix = "ABC"

    def test_a_journal_cannot_hold_twice_the_same_rule(self):
        """Sans normalisation, deux règles sans préfixe cohabiteraient :
        PostgreSQL ne compare jamais deux NULL comme égaux."""
        self.assertEqual(self.rule.account_prefix, "")
        with self.assertRaises(Exception):
            self.env["oski.analytic.journal.rule"].create({
                "journal_id": self.journal.id})
            self.env.flush_all()

    def test_clearing_the_prefix_keeps_the_constraint_alive(self):
        second = self.env["oski.analytic.journal.rule"].create({
            "journal_id": self.journal.id, "account_prefix": "60"})
        with self.assertRaises(Exception):
            second.account_prefix = False
            self.env.flush_all()

    def test_a_posted_line_no_longer_blocks_anything(self):
        move = self._bill(distribution=self._distribution())
        move.action_post()
        line = move.invoice_line_ids
        line.analytic_distribution = False
        self.assertFalse(line._oski_analytic_is_missing())

    # -- Le contrôle avant comptabilisation -------------------------------

    def test_the_control_screen_lists_what_will_block(self):
        blocked = self._bill()
        clean = self._bill(distribution=self._distribution())
        found = self.env["account.move.line"].search([
            ("oski_analytic_missing", "=", True),
            ("move_id.state", "=", "draft"),
        ])
        self.assertIn(blocked.invoice_line_ids, found)
        self.assertNotIn(clean.invoice_line_ids, found)

    def test_the_boolean_filter_survives_its_normalisation(self):
        """Odoo 19 change ``= True`` en ``in {True}`` avant d'appeler la
        méthode de recherche du champ."""
        blocked = self._bill()
        found = self.env["account.move.line"].search([
            ("oski_analytic_missing", "in", [True])])
        self.assertIn(blocked.invoice_line_ids, found)
        spared = self.env["account.move.line"].search([
            ("oski_analytic_missing", "not in", [True])])
        self.assertNotIn(blocked.invoice_line_ids, spared)

    def test_the_control_screen_answers_the_other_way_round(self):
        clean = self._bill(distribution=self._distribution())
        found = self.env["account.move.line"].search([
            ("oski_analytic_missing", "=", False),
            ("id", "in", clean.invoice_line_ids.ids),
        ])
        self.assertEqual(found, clean.invoice_line_ids)

    def test_the_control_screen_is_empty_without_any_rule(self):
        self.rule.unlink()
        self._bill()
        found = self.env["account.move.line"].search([
            ("oski_analytic_missing", "=", True)])
        self.assertFalse(found)

    def test_the_flag_follows_the_prefix(self):
        line = self._bill().invoice_line_ids
        self.rule.account_prefix = "999"
        found = self.env["account.move.line"].search([
            ("oski_analytic_missing", "=", True), ("id", "=", line.id)])
        self.assertFalse(found)
        self.rule.account_prefix = line.account_id.code[:2]
        found = self.env["account.move.line"].search([
            ("oski_analytic_missing", "=", True), ("id", "=", line.id)])
        self.assertEqual(found, line)

    # -- L'écran ----------------------------------------------------------

    def test_an_archived_rule_can_be_found_again(self):
        """Une règle coupée doit rester atteignable depuis l'écran.

        `active` retire la ligne de la liste ; sans filtre pour la ramener,
        couper une règle revient à la perdre. Le comportement était juste et
        la suite verte : c'est l'écran qui manquait.
        """
        arch = self.env["oski.analytic.journal.rule"].get_view(
            self.env.ref(
                "oski_analytic_required.view_oski_analytic_rule_search").id,
            "search")["arch"]
        self.assertIn("oski_inactive", arch)

        self.rule.active = False
        self.assertFalse(self.env["oski.analytic.journal.rule"].search(
            [("journal_id", "=", self.journal.id)]))
        retrouvee = self.env["oski.analytic.journal.rule"].search(
            [("journal_id", "=", self.journal.id), ("active", "=", False)])
        self.assertEqual(retrouvee, self.rule)

    def test_the_list_offers_the_switch(self):
        arch = self.env["oski.analytic.journal.rule"].get_view(
            self.env.ref(
                "oski_analytic_required.view_oski_analytic_rule_list").id,
            "list")["arch"]
        self.assertIn('name="active"', arch)
