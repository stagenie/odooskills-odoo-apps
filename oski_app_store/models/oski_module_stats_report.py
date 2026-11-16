"""Rapport SQL du store : une ligne par module × jour × pays × version Odoo.

Sources (toutes déjà enregistrées par le store) :
- vues de fiche   : oski.module.view.daily (agrégat jour/pays) ;
- téléchargements : oski.module.download (journal, pays, version Odoo servie) ;
- ventes          : sale.order.line confirmées (`state = 'sale'`) d'un module payant,
                    montant hors taxes > 0, converti en devise société comme sale.report ;
- essais 1 h      : oski.module.trial (hors essais « Not started »).
Les jours sont des jours UTC.
"""
from odoo import fields, models


class OskiModuleStatsReport(models.Model):
    _name = "oski.module.stats.report"
    _description = "Store statistics"
    _auto = False
    _rec_name = "module_id"
    _order = "date desc"
    # Lire le rapport vide d'abord ces champs en base : sans cela, une vente
    # confirmée dans la même transaction n'y apparaîtrait pas encore.
    _depends = {
        "oski.module": ["is_free", "category_id", "product_tmpl_id"],
        "oski.module.view.daily": ["module_id", "day", "country_id", "view_count"],
        "oski.module.download": ["module_id", "date", "country_id", "odoo_version"],
        "oski.module.trial": ["module_id", "create_date", "country_id", "odoo_version", "state"],
        "sale.order": ["state", "date_order", "currency_rate", "oski_country_id"],
        "sale.order.line": ["order_id", "product_id", "price_subtotal"],
        "product.product": ["product_tmpl_id"],
    }

    date = fields.Date(string="Date", readonly=True)
    module_id = fields.Many2one("oski.module", string="Module", readonly=True)
    category_id = fields.Many2one(
        "oski.module.category", string="Category", readonly=True
    )
    pricing = fields.Selection(
        [("free", "Open source"), ("paid", "Paid")], string="Pricing", readonly=True
    )
    odoo_version = fields.Char(string="Odoo version", readonly=True)
    country_id = fields.Many2one("res.country", string="Country", readonly=True)
    view_count = fields.Integer(string="Page views", readonly=True)
    download_count = fields.Integer(string="Downloads", readonly=True)
    purchase_count = fields.Integer(string="Sales", readonly=True)
    trial_count = fields.Integer(string="Trials", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    revenue = fields.Monetary(
        string="Revenue", currency_field="currency_id", readonly=True
    )
    public_period = fields.Boolean(
        string="Since public counter start",
        readonly=True,
        help="Day on or after the start of the public counters "
             "(system parameter oski_app_store.public_counter_since).",
    )

    def _stats_sql(self):
        """Lignes brutes (non regroupées) des quatre sources — réutilisées par le
        rafraîchissement des compteurs de `oski.module`."""
        return """
            SELECT v.module_id, v.day AS date, v.country_id,
                   NULL::varchar AS odoo_version,
                   v.view_count, 0 AS download_count, 0 AS purchase_count,
                   0 AS trial_count, 0::numeric AS revenue
              FROM oski_module_view_daily v
            UNION ALL
            SELECT d.module_id, d.date::date, d.country_id,
                   d.odoo_version, 0, 1, 0, 0, 0
              FROM oski_module_download d
            UNION ALL
            SELECT m.id, so.date_order::date, so.oski_country_id,
                   NULL, 0, 0, 1, 0,
                   (sol.price_subtotal / CASE COALESCE(so.currency_rate, 0)
                        WHEN 0 THEN 1.0 ELSE so.currency_rate END)::numeric
              FROM sale_order_line sol
              JOIN sale_order so ON so.id = sol.order_id
              JOIN product_product pp ON pp.id = sol.product_id
              JOIN oski_module m ON m.product_tmpl_id = pp.product_tmpl_id
             WHERE so.state = 'sale'
               AND NOT COALESCE(m.is_free, FALSE)
               AND sol.price_subtotal > 0
            UNION ALL
            SELECT t.module_id, t.create_date::date, t.country_id,
                   t.odoo_version, 0, 0, 0, 1, 0
              FROM oski_module_trial t
             WHERE t.state != 'error'
        """

    @property
    def _table_query(self):
        currency_id = self.env.company.currency_id.id or "NULL"
        since = self.env["oski.module"]._public_counter_since()
        public_period = (
            "(r.date >= DATE '%s')" % since.date().isoformat() if since else "FALSE"
        )
        return """
            SELECT row_number() OVER (ORDER BY r.date, r.module_id) AS id,
                   r.date,
                   r.module_id,
                   m.category_id,
                   CASE WHEN m.is_free THEN 'free' ELSE 'paid' END AS pricing,
                   r.odoo_version,
                   r.country_id,
                   SUM(r.view_count)     AS view_count,
                   SUM(r.download_count) AS download_count,
                   SUM(r.purchase_count) AS purchase_count,
                   SUM(r.trial_count)    AS trial_count,
                   %s AS currency_id,
                   SUM(r.revenue)        AS revenue,
                   %s AS public_period
              FROM (%s) r
              JOIN oski_module m ON m.id = r.module_id
          GROUP BY r.date, r.module_id, m.category_id, m.is_free,
                   r.odoo_version, r.country_id
        """ % (
            int(currency_id) if currency_id != "NULL" else "NULL",
            public_period,
            self._stats_sql(),
        )
