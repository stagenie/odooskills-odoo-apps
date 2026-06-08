import base64
import os

from odoo import http
from odoo.http import request

# Validation des pièces jointes (côté serveur)
ALLOWED_EXT = {
    "pdf", "png", "jpg", "jpeg", "zip",
    "doc", "docx", "odt", "xls", "xlsx",
}
MAX_FILE_SIZE = 10 * 1024 * 1024   # 10 Mo / fichier
MAX_FILES = 5
MAX_TOTAL_SIZE = 25 * 1024 * 1024  # 25 Mo au total


class OskiDevRequestController(http.Controller):

    def _render_form(self, values=None, error=None):
        env = request.env
        categories = env["oski.module.category"].sudo().search([])
        Req = env["oski.dev.request"]
        return request.render("oski_dev_request.form_page", {
            "categories": categories,
            "budget_options": Req._fields["budget_range"].selection,
            "version_options": Req._fields["odoo_version"].selection,
            "values": values or {},
            "error": error,
            "allowed_ext": ", ".join(sorted(ALLOWED_EXT)),
        })

    def _require_login(self):
        """Route website=True + auth=user accepte l'utilisateur public ;
        on force la connexion réelle (réservé aux inscrits)."""
        if not request.session.uid or request.env.user._is_public():
            return request.redirect(
                "/web/login?redirect=%s" % request.httprequest.full_path)
        return None

    @http.route("/apps/demande-developpement", type="http", auth="user",
                website=True, sitemap=True)
    def dev_request_form(self, **kw):
        redirect = self._require_login()
        if redirect:
            return redirect
        user = request.env.user
        partner = user.partner_id
        values = {
            "requester_name": user.name,
            "email": user.email or partner.email or "",
            "company_name": partner.commercial_company_name or "",
            "phone": partner.phone or "",
        }
        return self._render_form(values=values)

    @http.route("/apps/demande-developpement/submit", type="http", auth="user",
                website=True, methods=["POST"])
    def dev_request_submit(self, **post):
        redirect = self._require_login()
        if redirect:
            return redirect
        # Champs obligatoires
        required = ["requester_name", "email", "subject", "description", "budget_range"]
        missing = [f for f in required if not (post.get(f) or "").strip()]
        if missing:
            return self._render_form(values=post,
                                     error="Merci de remplir tous les champs obligatoires.")

        # Validation des fichiers (serveur)
        files = [f for f in request.httprequest.files.getlist("attachments") if f and f.filename]
        if len(files) > MAX_FILES:
            return self._render_form(values=post,
                                     error="Maximum %d fichiers." % MAX_FILES)
        total = 0
        prepared = []
        for f in files:
            data = f.read()
            size = len(data)
            total += size
            ext = os.path.splitext(f.filename)[1].lower().lstrip(".")
            if ext not in ALLOWED_EXT:
                return self._render_form(
                    values=post,
                    error="Type de fichier non autorisé : %s. Autorisés : %s." % (
                        f.filename, ", ".join(sorted(ALLOWED_EXT))))
            if size > MAX_FILE_SIZE:
                return self._render_form(
                    values=post,
                    error="Fichier trop volumineux : %s (max 10 Mo)." % f.filename)
            prepared.append((f.filename, data))
        if total > MAX_TOTAL_SIZE:
            return self._render_form(values=post,
                                     error="Taille totale des pièces jointes trop élevée (max 25 Mo).")

        # Création (sudo : l'utilisateur portail n'a pas le droit create direct)
        env = request.env
        category_id = post.get("category_id")
        vals = {
            "requester_name": post.get("requester_name").strip(),
            "company_name": (post.get("company_name") or "").strip(),
            "email": post.get("email").strip(),
            "phone": (post.get("phone") or "").strip(),
            "subject": post.get("subject").strip(),
            "description": post.get("description").strip(),
            "budget_range": post.get("budget_range"),
            "delivery_mode": post.get("delivery_mode") or "store",
            "odoo_version": post.get("odoo_version") or "19.0",
            "user_id": env.user.id,
        }
        if category_id and category_id.isdigit():
            vals["category_id"] = int(category_id)
        req = env["oski.dev.request"].sudo().create(vals)

        # Pièces jointes
        attach_ids = []
        for filename, data in prepared:
            att = env["ir.attachment"].sudo().create({
                "name": filename,
                "datas": base64.b64encode(data),
                "res_model": "oski.dev.request",
                "res_id": req.id,
            })
            attach_ids.append(att.id)
        if attach_ids:
            req.sudo().write({"attachment_ids": [(6, 0, attach_ids)]})

        # Emails (accusé + notif interne)
        try:
            ack = env.ref("oski_dev_request.mail_template_dev_request_ack", raise_if_not_found=False)
            if ack:
                ack.sudo().send_mail(req.id, force_send=False)
            notify = env.ref("oski_dev_request.mail_template_dev_request_notify", raise_if_not_found=False)
            if notify and notify.sudo().email_to:
                notify.sudo().send_mail(req.id, force_send=False)
        except Exception:
            pass  # un échec d'envoi ne doit pas casser la soumission

        return request.redirect("/apps/demande-developpement/merci?ref=%s" % req.name)

    @http.route("/apps/demande-developpement/merci", type="http", auth="user",
                website=True, sitemap=False)
    def dev_request_thanks(self, ref=None, **kw):
        return request.render("oski_dev_request.thanks_page", {"ref": ref})
