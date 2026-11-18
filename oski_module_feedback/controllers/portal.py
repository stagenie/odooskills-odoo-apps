"""Espace client : « My requests » — statut et réponse de chaque demande."""
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

PAGE_SIZE = 20


class OskiModuleFeedbackPortal(CustomerPortal):

    def _feedback_domain(self):
        return [("partner_id", "=", request.env.user.partner_id.id)]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "feedback_count" in counters:
            Feedback = request.env["oski.module.feedback"]
            values["feedback_count"] = (
                Feedback.search_count(self._feedback_domain())
                if Feedback.has_access("read") else 0
            )
        return values

    @http.route(["/my/module-requests", "/my/module-requests/page/<int:page>"],
                type="http", auth="user", website=True)
    def portal_my_feedback(self, page=1, **kw):
        Feedback = request.env["oski.module.feedback"]
        domain = self._feedback_domain()
        total = Feedback.search_count(domain)
        pager = portal_pager(url="/my/module-requests", total=total, page=page, step=PAGE_SIZE)
        values = self._prepare_portal_layout_values()
        values.update({
            "requests": Feedback.search(domain, limit=PAGE_SIZE, offset=pager["offset"]),
            "pager": pager,
            "page_name": "module_requests",
            "default_url": "/my/module-requests",
        })
        return request.render("oski_module_feedback.portal_my_feedback", values)

    @http.route(["/my/module-requests/<int:feedback_id>"],
                type="http", auth="public", website=True)
    def portal_my_feedback_detail(self, feedback_id, access_token=None, **kw):
        try:
            rec = self._document_check_access("oski.module.feedback", feedback_id, access_token)
        except (AccessError, MissingError):
            return request.redirect("/my")
        values = self._get_page_view_values(
            rec, access_token, {"feedback": rec, "page_name": "module_request"},
            "my_feedback_history", False)
        return request.render("oski_module_feedback.portal_my_feedback_detail", values)
