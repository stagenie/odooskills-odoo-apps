from odoo import SUPERUSER_ID, api
from odoo.addons.oski_dev_request.hooks import adopt_request_menu


def migrate(cr, version):
    adopt_request_menu(api.Environment(cr, SUPERUSER_ID, {}))
