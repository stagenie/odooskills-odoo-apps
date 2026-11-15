"""Internal notification template is noupdate: an update does not reload it.

19/20 default `use_default_to` to True, which replaces `email_to` (the team
address) by the record's default recipient, the requester. Write the two
fields only: translations and any wording customized in the database stay.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    template = env.ref("oski_dev_request.mail_template_dev_request_notify", raise_if_not_found=False)
    if template:
        template.write({
            "use_default_to": False,
            "lang": "{{ object.env.company.partner_id.lang }}",
        })
