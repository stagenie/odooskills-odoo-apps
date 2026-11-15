from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    oski_show_counters = fields.Boolean(
        string="Show download and purchase counters",
        config_parameter="oski_app_store.show_counters")
    oski_counters_min = fields.Integer(
        string="Minimum value to display a counter", default=10,
        config_parameter="oski_app_store.counters_min")
    oski_trial_enabled = fields.Boolean(
        string="1-hour trials of premium modules",
        config_parameter="oski.trial.enabled")
    oski_trial_api_url = fields.Char(
        string="Trial service URL",
        config_parameter="oski.trial.api_url")
    oski_trial_max_per_email = fields.Integer(
        string="Trials per e-mail address in 24 hours",
        default=3,
        config_parameter="oski.trial.max_per_email_per_day")
    oski_trial_max_per_ip = fields.Integer(
        string="Trials per connection in 24 hours",
        default=3,
        config_parameter="oski.trial.max_per_ip_per_day")
