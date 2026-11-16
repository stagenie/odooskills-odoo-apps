"""Statistiques du store : vues de fiche, compteurs triables, rapport SQL, droits, affichage."""
from datetime import timedelta
from unittest.mock import PropertyMock, patch

from odoo import fields
from odoo.exceptions import AccessError
from odoo.http import GeoIP
from odoo.tests import new_test_user, tagged
from odoo.tests.common import HttpCase

from .common_i18n import activate_french

BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)


@tagged("post_install", "-at_install")
class TestStoreStats(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")
        cls.v19 = cls.env["oski.odoo.version"].search([("name", "=", "19.0")], limit=1)
        cls.manager = new_test_user(
            cls.env, login="oski_stats_manager", password="oski_stats_manager",
            groups="base.group_user,oski_app_store.group_manager",
        )
        cls.employee = new_test_user(
            cls.env, login="oski_stats_employee", password="oski_stats_employee",
            groups="base.group_user",
        )
        cls.portal = new_test_user(
            cls.env, login="oski_stats_portal", password="oski_stats_portal",
            groups="base.group_portal",
        )

    def _module(self, name, is_free=True, price=0.0):
        product = self.env["product.template"]
        if not is_free:
            product = product.create({"name": name, "type": "service", "list_price": price,
                                      "taxes_id": [(6, 0, [])], "is_published": True})
        module = self.env["oski.module"].create({
            "name": name, "technical_name": name, "is_free": is_free, "is_published": True,
            "price": price, "product_tmpl_id": product.id if product else False,
        })
        att = self.env["ir.attachment"].create({"name": name + ".zip", "raw": b"ZIP",
                                                "mimetype": "application/zip"})
        version = self.env["oski.module.version"].create({
            "module_id": module.id, "odoo_version_id": self.v19.id,
            "module_version": "19.0.1.0.0", "attachment_id": att.id})
        return module, version

    def _views(self, module):
        rows = self.env["oski.module.view.daily"].search([("module_id", "=", module.id)])
        rows.invalidate_recordset()
        return sum(rows.mapped("view_count"))

    def _open(self, url, ua=BROWSER_UA, **kw):
        return self.url_open(url, headers={"User-Agent": ua}, **kw)

    def _set_counters(self, show, minimum=10):
        Param = self.env["ir.config_parameter"].sudo()
        Param.set_param("oski_app_store.show_counters", "True" if show else "False")
        Param.set_param("oski_app_store.counters_min", str(minimum))

    # ---- Vues de fiche -------------------------------------------------

    def test_view_counted_once_per_session(self):
        module, _version = self._module("oski_st_view")
        self.assertEqual(self._open(module.website_url).status_code, 200)
        self._open(module.website_url)
        self.assertEqual(self._views(module), 1, "refresh within 30 min = same view")
        self.opener.cookies.clear()
        self._open(module.website_url)
        self.assertEqual(self._views(module), 2, "another session counts again")
        rows = self.env["oski.module.view.daily"].search([("module_id", "=", module.id)])
        self.assertEqual(len(rows), 1, "one aggregate row per module, day and country")
        self.assertEqual(rows.day, fields.Date.today())

    def test_view_country_from_geoip(self):
        module, _version = self._module("oski_st_view_geo")
        with patch.object(GeoIP, "country_code", new_callable=PropertyMock, return_value="DZ"):
            self._open(module.website_url)
        row = self.env["oski.module.view.daily"].search([("module_id", "=", module.id)])
        self.assertEqual(row.country_id, self.env.ref("base.dz"))

    def test_robots_and_internal_users_not_counted(self):
        module, version = self._module("oski_st_robot")
        for ua in ("Mozilla/5.0 (compatible; Googlebot/2.1)", "curl/8.5.0",
                   "Mozilla/5.0 (publish_check)", ""):
            self.opener.cookies.clear()
            self._open(module.website_url, ua=ua)
            self._open("/apps/download/%d" % version.id, ua=ua)
        self.assertEqual(self._views(module), 0)
        version.invalidate_recordset(["download_count"])
        self.assertEqual(version.download_count, 0, "robot downloads are not counted")
        self.assertFalse(self.env["oski.module.download"].search([("module_id", "=", module.id)]))

        self.authenticate("oski_stats_employee", "oski_stats_employee")
        self._open(module.website_url)
        self._open("/apps/download/%d" % version.id)
        self.assertEqual(self._views(module), 0, "internal users are not counted")
        version.invalidate_recordset(["download_count"])
        self.assertEqual(version.download_count, 0)

        self.authenticate("oski_stats_portal", "oski_stats_portal")
        self._open(module.website_url)
        self.assertEqual(self._views(module), 1, "portal customers are counted")

    def test_unpublished_page_not_counted(self):
        module, _version = self._module("oski_st_unpub")
        module.is_published = False
        self.assertEqual(self._open(module.website_url).status_code, 404)
        self.assertEqual(self._views(module), 0)

    # ---- Compteurs stockés et rapport SQL ------------------------------

    def _order(self, module, partner, state="sale", price=None):
        variant = module.product_tmpl_id.product_variant_id
        line = {"product_id": variant.id, "product_uom_qty": 1}
        if price is not None:
            line["price_unit"] = price
        order = self.env["sale.order"].create({
            "partner_id": partner.id, "order_line": [(0, 0, line)],
        })
        if state in ("sale", "cancel"):
            order.action_confirm()
        if state == "cancel":
            order._action_cancel()
        return order

    def _populate(self):
        free, free_version = self._module("oski_st_free")
        paid, paid_version = self._module("oski_st_paid", is_free=False, price=40.0)
        View = self.env["oski.module.view.daily"]
        dz = self.env.ref("base.dz").id
        for _i in range(4):
            View._record_view(free.id, dz)
        for _i in range(10):
            View._record_view(paid.id)
        Download = self.env["oski.module.download"]
        Download._log(free_version, country=self.env.ref("base.dz"), source="geoip")
        Download._log(free_version)
        Download._log(paid_version)
        buyer = self.env["res.partner"].create({"name": "Stats buyer",
                                                "country_id": self.env.ref("base.fr").id})
        self._order(paid, buyer)                 # compte : 40
        self._order(paid, buyer)                 # compte : 40
        self._order(paid, buyer, state="draft")  # devis : non
        self._order(paid, buyer, state="cancel")  # annulée : non
        self._order(paid, buyer, price=0.0)      # montant nul : non
        Trial = self.env["oski.module.trial"].sudo()
        for state in ("expired", "ready", "error"):
            Trial.create({"module_id": paid.id, "odoo_version": "19.0",
                          "email": "t@example.com", "state": state})
        return free, paid

    def test_stats_refresh_counts(self):
        free, paid = self._populate()
        self.env["oski.module"]._stats_refresh()
        self.assertEqual(
            (free.stat_view_count, free.stat_download_count, free.stat_purchase_count),
            (4, 2, 0),
        )
        self.assertEqual(free.stat_download_rate, 50.0)
        self.assertEqual(
            (paid.stat_view_count, paid.stat_download_count, paid.stat_purchase_count,
             paid.stat_trial_count),
            (10, 1, 2, 2),
        )
        self.assertEqual(paid.stat_revenue, 80.0)
        self.assertEqual(paid.stat_purchase_rate, 20.0)
        # Triables : ce sont des colonnes stockées.
        self.assertTrue(self.env["oski.module"]._fields["stat_download_count"].store)
        top = self.env["oski.module"].search(
            [("id", "in", (free | paid).ids)], order="stat_view_count desc", limit=1)
        self.assertEqual(top, paid)

    def test_report_aggregates(self):
        free, paid = self._populate()
        Report = self.env["oski.module.stats.report"]
        groups = Report._read_group(
            [("module_id", "in", (free | paid).ids)],
            ["module_id"],
            ["view_count:sum", "download_count:sum", "purchase_count:sum",
             "trial_count:sum", "revenue:sum"],
        )
        by_module = {g[0]: g[1:] for g in groups}
        self.assertEqual(by_module[free], (4, 2, 0, 0, 0.0))
        self.assertEqual(by_module[paid], (10, 1, 2, 2, 80.0))
        # Pays, version Odoo et tarif sont des axes du rapport.
        dz_rows = Report.search([("module_id", "=", free.id),
                                 ("country_id", "=", self.env.ref("base.dz").id)])
        self.assertEqual(sum(dz_rows.mapped("view_count")), 4)
        self.assertEqual(sum(dz_rows.mapped("download_count")), 1)
        self.assertEqual(
            sum(Report.search([("module_id", "=", free.id),
                               ("odoo_version", "=", "19.0")]).mapped("download_count")), 2)
        self.assertEqual(set(Report.search([("module_id", "=", paid.id)]).mapped("pricing")),
                         {"paid"})
        sales = Report.search([("module_id", "=", paid.id), ("purchase_count", ">", 0)])
        self.assertEqual(sales.country_id, self.env.ref("base.fr"))
        # Filtre « 7 derniers jours » : tout est d'aujourd'hui.
        week_ago = fields.Date.today() - timedelta(days=6)
        self.assertEqual(
            sum(Report.search([("module_id", "=", paid.id), ("date", ">=", week_ago)])
                .mapped("view_count")), 10)
        self.assertFalse(Report.search([("module_id", "=", paid.id),
                                        ("date", "<", week_ago)]))

    def test_cron_refresh(self):
        free, _paid = self._populate()
        cron = self.env.ref("oski_app_store.ir_cron_oski_stats_refresh")
        cron.method_direct_trigger()
        free.invalidate_recordset()
        self.assertEqual(free.stat_view_count, 4)

    # ---- Droits ---------------------------------------------------------

    def test_access_rights(self):
        self._populate()
        Report = self.env["oski.module.stats.report"]
        self.assertTrue(Report.with_user(self.manager).search_count([]))
        self.assertTrue(self.env["oski.module.view.daily"].with_user(self.manager).search_count([]))
        for user in (self.employee, self.portal):
            with self.assertRaises(AccessError):
                Report.with_user(user).search_count([])
            with self.assertRaises(AccessError):
                self.env["oski.module.view.daily"].with_user(user).search_count([])
        with self.assertRaises(AccessError):
            self.env["oski.module.view.daily"].with_user(self.manager).create(
                {"module_id": self._module("oski_st_acl")[0].id, "day": fields.Date.today()})
        menu = self.env.ref("oski_app_store.menu_oski_analysis")
        self.assertEqual(menu.group_ids, self.env.ref("oski_app_store.group_manager"))
        self.assertIn(menu.id, self.env["ir.ui.menu"].with_user(self.manager)._visible_menu_ids())
        self.assertNotIn(menu.id, self.env["ir.ui.menu"].with_user(self.employee)._visible_menu_ids())

    def test_analysis_views_load(self):
        for model, view_types in (
            ("oski.module.stats.report", ["pivot", "graph", "list", "search"]),
            ("oski.module", ["list", "form"]),
        ):
            for view_type in view_types:
                self.env[model].with_user(self.manager).get_views([(False, view_type)])
        for xmlid in ("oski_module_view_list_ranking", "oski_module_view_list_ranking_purchase",
                      "oski_module_view_list_ranking_view",
                      "oski_module_view_list_ranking_conversion"):
            view = self.env.ref("oski_app_store." + xmlid)
            self.env["oski.module"].with_user(self.manager).get_views([(view.id, "list")])
        # Le bouton de la liste recalcule sans erreur.
        self.env["oski.module"].with_user(self.manager).action_stats_refresh()

    # ---- Affichage public -------------------------------------------------

    def test_purchase_counter_never_on_free_module(self):
        module, _version = self._module("oski_st_free_buy")
        self._set_counters(True, minimum=0)
        self.assertFalse(module.counters_visible("purchase"))
        self.assertTrue(module.counters_visible("download"))
        page = self._open(module.website_url).text
        self.assertIn("0 downloads", " ".join(page.split()))
        self.assertNotIn("oski-count-buy", page)

    def test_paid_module_shows_purchases_above_threshold(self):
        module, version = self._module("oski_st_paid_show", is_free=False, price=19.0)
        version.write({"download_count": 12})
        for name in ("Buyer A", "Buyer B"):
            self._order(module, self.env["res.partner"].create({"name": name}))
        self._set_counters(True, minimum=2)
        page = " ".join(self._open(module.website_url).text.split())
        self.assertIn("12 downloads", page)
        self.assertIn("2 purchases", page)
        catalog = self._open("/apps").text
        self.assertIn("oski-count-buy", catalog)
        self._set_counters(True, minimum=3)
        page = self._open(module.website_url).text
        self.assertNotIn("oski-count-buy", page, "2 buyers < threshold 3")
        self.assertIn("12 downloads", " ".join(page.split()))
        self._set_counters(False, minimum=0)
        self.assertNotIn("oski-count", self._open(module.website_url).text)

    def test_counters_in_french(self):
        activate_french(self.env)
        module, version = self._module("oski_st_fr", is_free=False, price=19.0)
        version.write({"download_count": 1})
        self._order(module, self.env["res.partner"].create({"name": "Acheteur"}))
        self._set_counters(True, minimum=0)
        page = " ".join(self._open("/fr" + module.website_url).text.split())
        self.assertIn("1 téléchargement", page)
        self.assertIn("1 achat", page)
        version.write({"download_count": 5})
        page = " ".join(self._open("/fr" + module.website_url).text.split())
        self.assertIn("5 téléchargements", page)

    # ---- Point de départ des compteurs publics (décision du 16/11) -----

    def test_public_counters_start_date(self):
        module, version = self._module("oski_st_since", is_free=False, price=30.0)
        Download = self.env["oski.module.download"]
        since = fields.Datetime.now() - timedelta(hours=1)
        old_log = Download._log(version)
        old_log.date = since - timedelta(days=2)
        Download._log(version)
        version.write({"download_count": 48})   # historique du compteur des archives
        old_buyer = self.env["res.partner"].create({"name": "Old buyer"})
        new_buyer = self.env["res.partner"].create({"name": "New buyer"})
        self._order(module, old_buyer).date_order = since - timedelta(days=2)
        self._order(module, new_buyer)
        self.env.flush_all()

        # Sans point de départ : comportement d'origine (compteur des archives).
        module.invalidate_recordset(["download_count", "purchase_count"])
        self.assertEqual((module.download_count, module.purchase_count), (48, 2))

        self.env["ir.config_parameter"].sudo().set_param(
            "oski_app_store.public_counter_since", fields.Datetime.to_string(since))
        module.invalidate_recordset(["download_count", "purchase_count"])
        self.assertEqual((module.download_count, module.purchase_count), (1, 1))
        # Rien n'est effacé : compteur d'archive, journal et analyse gardent l'historique.
        self.assertEqual(version.download_count, 48)
        self.assertEqual(len(Download.search([("module_id", "=", module.id)])), 2)
        Report = self.env["oski.module.stats.report"]
        rows = Report.search([("module_id", "=", module.id)])
        self.assertEqual(sum(rows.mapped("download_count")), 2)
        self.assertEqual(sum(rows.mapped("purchase_count")), 2)
        recent = Report.search([("module_id", "=", module.id), ("public_period", "=", True)])
        self.assertEqual(sum(recent.mapped("download_count")), 1)
        self.assertEqual(sum(recent.mapped("purchase_count")), 1)
        # Affichage : 1 < seuil 10 → rien ; seuil 0 → « 1 download ».
        self._set_counters(True, minimum=10)
        self.assertNotIn("oski-count", self._open(module.website_url).text)
        self._set_counters(True, minimum=0)
        page = " ".join(self._open(module.website_url).text.split())
        self.assertIn("1 download", page)
        self.assertIn("1 purchase", page)

    def test_migration_sets_public_start(self):
        import importlib.util
        from odoo.modules.module import get_module_path
        path = get_module_path("oski_app_store") + "/migrations/19.0.7.7.4/post-migration.py"
        spec = importlib.util.spec_from_file_location("oski_mig_19_0_7_7_4", path)
        mig = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mig)
        Param = self.env["ir.config_parameter"].sudo()
        for key in ("public_counter_since", "show_counters", "counters_min"):
            Param.search([("key", "=", "oski_app_store." + key)]).unlink()
        mig.migrate(self.env.cr, "19.0.7.7.3")
        self.assertTrue(Param.get_param("oski_app_store.public_counter_since"))
        self.assertEqual(Param.get_param("oski_app_store.show_counters"), "True")
        self.assertEqual(Param.get_param("oski_app_store.counters_min"), "10")
        # Relancée : la date de départ ne bouge pas.
        Param.set_param("oski_app_store.public_counter_since", "2026-11-16 10:00:00")
        mig.migrate(self.env.cr, "19.0.7.7.3")
        self.assertEqual(Param.get_param("oski_app_store.public_counter_since"),
                         "2026-11-16 10:00:00")
