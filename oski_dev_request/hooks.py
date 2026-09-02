"""Adoption of a hand-made "Request a module" menu (production has one without xmlid)."""
from odoo import SUPERUSER_ID, api

REQUEST_URL = "/apps/demande-developpement"
MENU_XMLID = "oski_dev_request.menu_request_module"
MENU_NAMES = {"en_US": "Request a module", "fr_FR": "Demander un module"}


def adopt_request_menu(env):
    """Attach MENU_XMLID to an existing menu at REQUEST_URL that has no xmlid, so the
    noupdate data record is skipped instead of creating a duplicate. Idempotent.
    Returns the adopted menu (empty recordset if nothing to adopt)."""
    Menu = env["website.menu"]
    if env.ref(MENU_XMLID, raise_if_not_found=False):
        return Menu
    module, name = MENU_XMLID.split(".", 1)
    candidates = Menu.search([("url", "=", REQUEST_URL)], order="id")
    with_xmlid = set(env["ir.model.data"].search([("model", "=", "website.menu"), ("res_id", "in", candidates.ids)]).mapped("res_id"))
    menu = next((m for m in candidates if m.id not in with_xmlid), Menu)
    if not menu:
        return Menu
    env["ir.model.data"].create({"module": module, "name": name, "model": "website.menu", "res_id": menu.id, "noupdate": True})
    installed = {code for code, _ in env["res.lang"].get_installed()} | {"en_US"}
    menu.update_field_translations("name", {lang: value for lang, value in MENU_NAMES.items() if lang in installed})
    return menu
