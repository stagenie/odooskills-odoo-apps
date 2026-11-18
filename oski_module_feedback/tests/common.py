"""Données partagées : un module payant publié, un gratuit, un client portail."""
from odoo import Command


def make_store_data(cls):
    env = cls.env
    cls.v19 = env["oski.odoo.version"].search([("name", "=", "19.0")], limit=1)
    product = env["product.template"].create({
        "name": "oski_fb_paid", "type": "service", "list_price": 100.0,
        "taxes_id": [(6, 0, [])], "is_published": True, "sale_ok": True,
    })
    cls.paid = env["oski.module"].create({
        "name": "Paid Demo", "technical_name": "oski_fb_paid",
        "is_free": False, "is_published": True, "price": 100.0,
        "product_tmpl_id": product.id,
    })
    cls.free = env["oski.module"].create({
        "name": "Free Demo", "technical_name": "oski_fb_free",
        "is_free": True, "is_published": True,
    })
    for module in (cls.paid, cls.free):
        attachment = env["ir.attachment"].create({
            "name": "%s.zip" % module.technical_name, "raw": b"ZIP",
            "mimetype": "application/zip",
        })
        env["oski.module.version"].create({
            "module_id": module.id, "odoo_version_id": cls.v19.id,
            "module_version": "19.0.1.0.0", "attachment_id": attachment.id,
        })
    cls.portal_user = env["res.users"].with_context(no_reset_password=True).create({
        "name": "Awa Diop", "login": "awa_fb", "password": "awa_fb_12345",
        "email": "awa@example.com", "lang": "en_US",
        "group_ids": [Command.set([env.ref("base.group_portal").id])],
    })
    cls.other_user = env["res.users"].with_context(no_reset_password=True).create({
        "name": "Ben Other", "login": "ben_fb", "password": "ben_fb_12345",
        "email": "ben@example.com", "lang": "en_US",
        "group_ids": [Command.set([env.ref("base.group_portal").id])],
    })


def feedback_vals(cls, **kw):
    vals = {
        "module_id": cls.paid.id, "odoo_version_id": cls.v19.id,
        "request_type": "improvement", "title": "Export to Excel",
        "description": "Please add an export.",
        "partner_id": cls.portal_user.partner_id.id,
    }
    vals.update(kw)
    return vals


def prod_languages(env):
    """Comme la prod : anglais par défaut, français sous /fr."""
    fr = env["res.lang"]._activate_lang("fr_FR")
    en = env["res.lang"]._activate_lang("en_US")
    env["website"].get_current_website().write({
        "language_ids": [(4, fr.id), (4, en.id)], "default_lang_id": en.id})
    env.registry.clear_cache()
