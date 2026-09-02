from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oski_show_counters = fields.Boolean(
        string="Show download and purchase counters",
        config_parameter="oski_app_store.show_counters")
    oski_counters_min = fields.Integer(
        string="Minimum value to display a counter", default=10,
        config_parameter="oski_app_store.counters_min")
