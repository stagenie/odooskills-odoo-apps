from odoo import fields, models


class OskiLoginLog(models.Model):
    _name = "oski.login.log"
    _description = "Login Log"
    _order = "create_date desc, id desc"
    _rec_name = "login"

    login = fields.Char(string="Login Entered", required=True, index=True, readonly=True)
    user_id = fields.Many2one(
        "res.users", string="User", readonly=True, ondelete="set null",
        help="Empty when the login entered matches no account.",
    )
    result = fields.Selection(
        [("success", "Success"), ("failure", "Failure")],
        string="Result", required=True, index=True, readonly=True,
    )
    ip_address = fields.Char(string="IP Address", readonly=True)
    create_date = fields.Datetime(string="Date", readonly=True)
