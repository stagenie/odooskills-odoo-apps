"""Statistiques du store : vues de fiche, compteurs triables, rafraîchissement.

Les vues de fiche sont agrégées par (module, jour, pays) dans
`oski.module.view.daily` : une visite = un INSERT … ON CONFLICT DO UPDATE sur
une petite ligne d'agrégat, jamais un write ORM sur `oski.module` (qui
verrouillerait la fiche et invaliderait son cache à chaque visite).

Les compteurs `stat_*` de `oski.module` sont stockés pour pouvoir trier la
liste du back-end ; ils sont recalculés en une seule requête SQL par le cron
horaire (et à la mise à jour du module). Les compteurs publics de la fiche
(`download_count`, `purchase_count`) restent calculés en direct.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OskiModuleViewDaily(models.Model):
    _name = "oski.module.view.daily"
    _description = "Store module page views per day"
    _order = "day desc, id desc"
    _rec_name = "module_id"
    _log_access = False

    module_id = fields.Many2one(
        "oski.module", string="Module", required=True, ondelete="cascade", index=True
    )
    day = fields.Date(string="Day", required=True, index=True)
    country_id = fields.Many2one("res.country", string="Country", ondelete="set null")
    view_count = fields.Integer(string="Views", default=0)

    def init(self):
        # Une ligne par (module, jour, pays) ; pays vide compté comme 0 pour
        # que l'upsert retrouve la même ligne (NULL n'est jamais « égal »).
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS oski_module_view_daily_key
                ON oski_module_view_daily (module_id, day, (COALESCE(country_id, 0)))
            """
        )

    @api.model
    def _record_view(self, module_id, country_id=None):
        """+1 vue pour aujourd'hui (UTC). SQL pur, appelé en sudo par le contrôleur."""
        self.env.cr.execute(
            """
            INSERT INTO oski_module_view_daily (module_id, day, country_id, view_count)
            VALUES (%s, (now() AT TIME ZONE 'UTC')::date, %s, 1)
            ON CONFLICT (module_id, day, (COALESCE(country_id, 0)))
            DO UPDATE SET view_count = oski_module_view_daily.view_count + 1
            """,
            [module_id, country_id or None],
        )


class OskiModule(models.Model):
    _inherit = "oski.module"

    company_currency_id = fields.Many2one(
        "res.currency",
        string="Company currency",
        compute="_compute_company_currency_id",
    )
    stat_view_count = fields.Integer(
        string="Page views",
        readonly=True,
        copy=False,
        help="Views of the public module page (robots and internal users excluded). "
             "Refreshed every hour.",
    )
    stat_download_count = fields.Integer(
        string="Logged downloads",
        readonly=True,
        copy=False,
        help="Archives served and recorded in the download log. Refreshed every hour.",
    )
    stat_purchase_count = fields.Integer(
        string="Sales",
        readonly=True,
        copy=False,
        help="Confirmed paid order lines for this module (quotations, cancelled "
             "orders and zero-amount lines excluded). Refreshed every hour.",
    )
    stat_trial_count = fields.Integer(
        string="Trials",
        readonly=True,
        copy=False,
        help="1-hour trials requested (trials that could not start excluded). "
             "Refreshed every hour.",
    )
    stat_revenue = fields.Monetary(
        string="Revenue",
        currency_field="company_currency_id",
        readonly=True,
        copy=False,
        help="Untaxed amount of the confirmed sales, in the company currency. "
             "Refreshed every hour.",
    )
    stat_download_rate = fields.Float(
        string="View → download (%)",
        readonly=True,
        copy=False,
        aggregator="avg",
        digits=(16, 1),
        help="Logged downloads per 100 page views.",
    )
    stat_purchase_rate = fields.Float(
        string="View → sale (%)",
        readonly=True,
        copy=False,
        aggregator="avg",
        digits=(16, 1),
        help="Sales per 100 page views.",
    )

    def _compute_company_currency_id(self):
        currency = self.env.company.currency_id
        for record in self:
            record.company_currency_id = currency

    def counters_visible(self, kind):
        """Jamais de compteur d'achats sur un module gratuit (« 0 achat »)."""
        self.ensure_one()
        if kind == "purchase" and self.is_free:
            return False
        return super().counters_visible(kind)

    # ---- Compteurs publics : point de départ ---------------------------
    # `oski_app_store.public_counter_since` (UTC, posé par la migration 19.0.7.7.4) :
    # les compteurs PUBLICS ne comptent que ce qui est journalisé après cette date.
    # Rien n'est effacé : journal, `oski.module.version.download_count` et rapport
    # d'analyse gardent tout l'historique. Sans paramètre (installation neuve),
    # comportement d'origine : somme des compteurs des archives.

    @api.model
    def _public_counter_since(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "oski_app_store.public_counter_since"
        )
        if not value:
            return False
        try:
            return fields.Datetime.to_datetime(value)
        except ValueError:
            _logger.warning("Invalid oski_app_store.public_counter_since: %r", value)
            return False

    def _compute_download_count(self):
        since = self._public_counter_since()
        if not since:
            return super()._compute_download_count()
        groups = self.env["oski.module.download"].sudo()._read_group(
            [("module_id", "in", self.ids), ("date", ">=", since)],
            ["module_id"],
            ["__count"],
        )
        counts = {module.id: count for module, count in groups}
        for record in self:
            record.download_count = counts.get(record.id, 0)

    def _compute_purchase_count(self):
        since = self._public_counter_since()
        if not since:
            return super()._compute_purchase_count()
        paid = self.filtered(lambda m: not m.is_free and m.product_tmpl_id)
        (self - paid).purchase_count = 0
        if not paid:
            return
        groups = self.env["sale.order.line"].sudo()._read_group(
            [
                ("product_id.product_tmpl_id", "in", paid.product_tmpl_id.ids),
                ("state", "=", "sale"),
                ("order_id.date_order", ">=", since),
            ],
            ["product_id", "order_partner_id"],
            [],
        )
        buyers = {}
        for product, partner in groups:
            if product and partner:
                buyers.setdefault(product.product_tmpl_id.id, set()).add(partner.id)
        for record in paid:
            record.purchase_count = len(buyers.get(record.product_tmpl_id.id, ()))

    @api.model
    def _stats_refresh(self):
        """Recalcule tous les compteurs `stat_*` en une requête (depuis le rapport SQL)."""
        report = self.env["oski.module.stats.report"]
        self.env.flush_all()
        self.env.cr.execute(
            """
            WITH agg AS (
                SELECT module_id,
                       SUM(view_count)     AS views,
                       SUM(download_count) AS downloads,
                       SUM(purchase_count) AS purchases,
                       SUM(trial_count)    AS trials,
                       SUM(revenue)        AS revenue
                  FROM (%s) r
              GROUP BY module_id
            )
            UPDATE oski_module m
               SET stat_view_count     = COALESCE(agg.views, 0),
                   stat_download_count = COALESCE(agg.downloads, 0),
                   stat_purchase_count = COALESCE(agg.purchases, 0),
                   stat_trial_count    = COALESCE(agg.trials, 0),
                   stat_revenue        = COALESCE(agg.revenue, 0),
                   stat_download_rate  = CASE WHEN COALESCE(agg.views, 0) > 0
                        THEN round(100.0 * agg.downloads / agg.views, 1) ELSE 0 END,
                   stat_purchase_rate  = CASE WHEN COALESCE(agg.views, 0) > 0
                        THEN round(100.0 * agg.purchases / agg.views, 1) ELSE 0 END
              FROM oski_module m2
         LEFT JOIN agg ON agg.module_id = m2.id
             WHERE m.id = m2.id
            """ % report._stats_sql()
        )
        self.invalidate_model(
            [
                "stat_view_count", "stat_download_count", "stat_purchase_count",
                "stat_trial_count", "stat_revenue", "stat_download_rate",
                "stat_purchase_rate",
            ]
        )
        return True

    @api.model
    def _cron_stats_refresh(self):
        self._stats_refresh()

    def action_stats_refresh(self):
        """Bouton « Refresh statistics » des listes d'analyse."""
        self._stats_refresh()
        return {"type": "ir.actions.client", "tag": "soft_reload"}
