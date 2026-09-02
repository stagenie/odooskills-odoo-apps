"""Production already carries a hand-made "Request a module" menu (no xmlid) at
/apps/demande-developpement. Loading the data record as-is would duplicate the nav
entry (website.menu.create() spawns one generic record + one copy per website).
adopt_request_menu() must attach the xmlid to that existing menu instead."""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.oski_app_store.tests.common_i18n import activate_french
from odoo.addons.oski_dev_request.hooks import MENU_XMLID, REQUEST_URL, adopt_request_menu

DATA_MODULE = "oski_dev_request"
DATA_NAME = "menu_request_module"


@tagged("post_install", "-at_install")
class TestMenuAdoption(TransactionCase):

    def _data_rows(self):
        return self.env["ir.model.data"].search([
            ("module", "=", DATA_MODULE), ("name", "=", DATA_NAME),
        ])

    def _simulate_production(self):
        """Delete the data-created menu/xmlid and recreate a hand-made one exactly
        like production: website-specific, parented under the website's own top
        menu, no xmlid."""
        stale = self.env.ref(MENU_XMLID, raise_if_not_found=False)
        self._data_rows().unlink()
        if stale:
            stale.unlink()
        # Odoo's website.menu.unlink() already cascades the per-site copies of a
        # generic menu when the generic record above is removed; unlink explicitly
        # anyway so this simulation does not depend on that cascade.
        self.env["website.menu"].search([("url", "=", REQUEST_URL)]).unlink()
        self.env.registry.clear_cache()
        self.assertFalse(
            self.env["website.menu"].search([("url", "=", REQUEST_URL)]),
            "aucun menu ne doit subsister avant de simuler la production",
        )

        website = self.env["website"].get_current_website()
        return self.env["website.menu"].create({
            "name": "Demande de developpement",
            "url": REQUEST_URL,
            "website_id": website.id,
            "parent_id": website.menu_id.id,
            "sequence": 25,
        })

    def test_adopts_hand_made_menu_and_translates_it(self):
        handmade = self._simulate_production()
        self.assertFalse(self.env.ref(MENU_XMLID, raise_if_not_found=False))

        activate_french(self.env, modules=("oski_app_store", "oski_dev_request"))

        adopted = adopt_request_menu(self.env)
        self.assertEqual(adopted, handmade)

        menu = self.env.ref(MENU_XMLID)
        self.assertEqual(menu, handmade)
        self.assertEqual(menu.with_context(lang="en_US").name, "Request a module")
        self.assertEqual(menu.with_context(lang="fr_FR").name, "Demander un module")

        data_row = self._data_rows()
        self.assertEqual(len(data_row), 1)
        self.assertTrue(data_row.noupdate)

    def test_idempotent(self):
        self._simulate_production()
        first = adopt_request_menu(self.env)
        self.assertTrue(first)

        second = adopt_request_menu(self.env)
        self.assertFalse(second)
        self.assertEqual(len(self._data_rows()), 1)

    def test_noop_when_xmlid_already_exists(self):
        # Fresh-install state: the data file's xmlid is already there.
        self.assertTrue(self.env.ref(MENU_XMLID, raise_if_not_found=False))
        before = self.env["ir.model.data"].search([("model", "=", "website.menu")]).ids

        result = adopt_request_menu(self.env)

        self.assertFalse(result)
        after = self.env["ir.model.data"].search([("model", "=", "website.menu")]).ids
        self.assertEqual(sorted(before), sorted(after))

    def test_noop_when_no_menu_and_no_xmlid(self):
        # Neither the xmlid nor any menu at REQUEST_URL exists.
        stale = self.env.ref(MENU_XMLID, raise_if_not_found=False)
        self._data_rows().unlink()
        if stale:
            stale.unlink()
        self.env["website.menu"].search([("url", "=", REQUEST_URL)]).unlink()
        self.env.registry.clear_cache()
        self.assertFalse(self.env["website.menu"].search([("url", "=", REQUEST_URL)]))

        result = adopt_request_menu(self.env)

        self.assertFalse(result)
        self.assertFalse(self._data_rows())
