import os

from werkzeug.urls import url_encode

from odoo import _, http
from odoo.http import request

# Pièces jointes : captures d'écran et PDF, rien d'exécutable.
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024   # 5 Mo / fichier
MAX_FILES = 3
TYPES = ("bug", "change", "improvement", "other")


class OskiModuleFeedbackController(http.Controller):

    # ------------------------------------------------------------------
    # Outils
    # ------------------------------------------------------------------
    def _feedback_module(self, technical_name):
        """Module publié ET payant, sinon None (→ 404)."""
        module = request.env["oski.module"].sudo().search(
            [("technical_name", "=", technical_name)], limit=1
        )
        if not module or not module.is_published or module.is_free:
            return None
        return module

    def _versions(self, module):
        return module.version_line_ids.mapped("odoo_version_id").sorted("sequence", reverse=True)

    def _login_redirect(self, extra=None):
        """Anonyme → page de connexion, retour au formulaire (langue gardée)."""
        # Le routage du site a réécrit le chemin sans le préfixe /fr ;
        # REQUEST_URI garde l'adresse d'origine (Request.reroute ne la touche pas).
        # La page de connexion suit la langue par le cookie posé par /fr.
        environ = request.httprequest.environ
        target = environ.get("REQUEST_URI") or request.httprequest.full_path.rstrip("?")
        params = {"redirect": target}
        params.update(extra or {})
        return request.redirect("/web/login?" + url_encode(params), local=True)

    def _render_form(self, module, values=None, error=None, status=200):
        versions = self._versions(module)
        values = dict(values or {})
        values.setdefault("request_type", "improvement")
        if not values.get("odoo_version_id") and versions:
            values["odoo_version_id"] = str(versions[0].id)
        return request.render(
            "oski_module_feedback.feedback_form_page",
            {
                "module": module,
                "versions": versions,
                "values": values,
                "error": error,
                "max_files": MAX_FILES,
                "allowed_ext": ", ".join(sorted(ALLOWED_EXT)),
                "module_url": request.env["ir.http"]._url_for(module.website_url),
                "submit_url": request.env["ir.http"]._url_for(
                    "/apps/m/%s/feedback/submit" % module.technical_name),
            },
            status=status,
        )

    def _read_files(self):
        """[(nom, octets, mimetype)] ou message d'erreur."""
        files = [f for f in request.httprequest.files.getlist("attachments") if f and f.filename]
        if len(files) > MAX_FILES:
            return None, _("You can attach up to %s files.", MAX_FILES)
        prepared = []
        for f in files:
            ext = os.path.splitext(f.filename)[1].lower().lstrip(".")
            if ext not in ALLOWED_EXT:
                return None, _("File type not allowed: %(filename)s. Allowed: %(allowed)s.",
                               filename=f.filename, allowed=", ".join(sorted(ALLOWED_EXT)))
            data = f.read()
            if len(data) > MAX_FILE_SIZE:
                return None, _("File too large: %s (max 5 MB).", f.filename)
            prepared.append((f.filename, data, f.mimetype))
        return prepared, None

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    @http.route(
        ["/apps/m/<string:technical_name>/feedback"],
        type="http", auth="public", website=True, sitemap=False,
    )
    def feedback_form(self, technical_name, **kw):
        module = self._feedback_module(technical_name)
        if not module:
            return request.not_found()
        if request.env.user._is_public():
            return self._login_redirect()
        return self._render_form(module)

    @http.route(
        ["/apps/m/<string:technical_name>/feedback/submit"],
        type="http", auth="public", website=True, sitemap=False, methods=["POST"],
    )
    def feedback_submit(self, technical_name, **post):
        module = self._feedback_module(technical_name)
        if not module:
            return request.not_found()
        if request.env.user._is_public():
            return request.redirect(module.website_url)
        Feedback = request.env["oski.module.feedback"]
        partner = request.env.user.partner_id

        title = (post.get("title") or "").strip()
        description = (post.get("description") or "").strip()
        request_type = post.get("request_type")
        if not title or not description or request_type not in TYPES:
            return self._render_form(module, post, _("Please fill in the type, the title and the description."))
        if Feedback._count_last_24h(partner) >= Feedback._max_per_day():
            return self._render_form(module, post, _(
                "You have sent many requests today. Please try again tomorrow, "
                "or reply to one of your open requests."))
        files, error = self._read_files()
        if error:
            return self._render_form(module, post, error)

        version = request.env["oski.odoo.version"].sudo().browse(
            int(post["odoo_version_id"]) if (post.get("odoo_version_id") or "").isdigit() else 0
        ).exists()
        vals = {
            "module_id": module.id,
            "odoo_version_id": version.id if version in self._versions(module) else False,
            "request_type": request_type,
            "title": title[:200],
            "description": description,
            "steps": (post.get("steps") or "").strip() if request_type == "bug" else False,
            "partner_id": partner.id,
            "source": "module_page",
        }
        vals.update(self._trial_vals(post))
        rec = Feedback.sudo().create(vals)
        attachments = request.env["ir.attachment"].sudo().create([{
            "name": name, "raw": data, "mimetype": mimetype,
            "res_model": rec._name, "res_id": rec.id,
        } for name, data, mimetype in files])
        if attachments:
            rec.attachment_ids = [(6, 0, attachments.ids)]
        rec._send_new_notifications()
        return request.redirect(
            request.env["ir.http"]._url_for("/apps/feedback/thanks/%s" % rec.id), local=True)

    def _trial_vals(self, post):
        """Rattachement à un essai (tâche 5)."""
        return {}

    @http.route(
        ["/apps/feedback/thanks/<int:feedback_id>"],
        type="http", auth="user", website=True, sitemap=False,
    )
    def feedback_thanks(self, feedback_id, **kw):
        rec = request.env["oski.module.feedback"].sudo().browse(feedback_id).exists()
        if not rec or rec.partner_id != request.env.user.partner_id:
            return request.not_found()
        return request.render("oski_module_feedback.feedback_thanks_page", {
            "feedback": rec,
            "module": rec.module_id,
            "module_url": request.env["ir.http"]._url_for(rec.module_id.website_url),
        })
