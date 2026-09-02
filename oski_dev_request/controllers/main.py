import base64
import os
import time

from odoo import _, http
from odoo.http import request

# Validation des pièces jointes (côté serveur)
ALLOWED_EXT = {
    "pdf", "png", "jpg", "jpeg", "zip",
    "doc", "docx", "odt", "xls", "xlsx",
}
MAX_FILE_SIZE = 10 * 1024 * 1024   # 10 Mo / fichier
MAX_FILES = 5
MAX_TOTAL_SIZE = 25 * 1024 * 1024  # 25 Mo au total

# Anti-spam d'un formulaire ouvert à tous, sans clé ni service tiers :
# un piège invisible, un délai minimum et un plafond par session.
HONEYPOT_FIELD = "website"      # laissé vide par un humain, rempli par un robot
MIN_FILL_SECONDS = 3            # personne ne remplit ce formulaire en 3 secondes
                                # (réglable : ir.config_parameter
                                #  oski_dev_request.min_fill_seconds)
FORM_MAX_AGE = 2 * 60 * 60      # un formulaire ouvert il y a 2 h est périmé
MAX_PER_HOUR = 3                # au-delà, c'est du bruit


class OskiDevRequestController(http.Controller):

    def _render_form(self, values=None, error=None):
        env = request.env
        # Horodatage de l'affichage : il sert à mesurer le temps de remplissage.
        request.session["oski_dev_form_ts"] = time.time()
        categories = env["oski.module.category"].sudo().search([])
        Req = env["oski.dev.request"]
        return request.render("oski_dev_request.form_page", {
            "categories": categories,
            "budget_options": Req._fields["budget_range"].selection,
            "version_options": Req._selection_odoo_version(),
            "default_version": env["oski.odoo.version"].sudo().get_default(),
            "values": values or {},
            "error": error,
            "allowed_ext": ", ".join(sorted(ALLOWED_EXT)),
            "honeypot_field": HONEYPOT_FIELD,
        })

    def _spam_verdict(self, post):
        """None si la soumission est plausible, sinon la raison du refus.

        Le formulaire est ouvert à tous : sans garde-fou, il devient une boîte
        à spam. Trois filtres suffisent et n'imposent rien à l'internaute :
        un champ piège qu'aucun humain ne voit, un temps de remplissage
        minimum, et un plafond par session.
        """
        if (post.get(HONEYPOT_FIELD) or "").strip():
            return "honeypot"

        min_delay = MIN_FILL_SECONDS
        param = request.env["ir.config_parameter"].sudo().get_param(
            "oski_dev_request.min_fill_seconds")
        if param not in (None, False, ""):
            try:
                min_delay = float(param)
            except ValueError:
                pass

        opened_at = request.session.get("oski_dev_form_ts")
        if not opened_at:
            return _("Your form has expired. Please reopen it and resend it.")
        elapsed = time.time() - opened_at
        if elapsed < min_delay:
            return _("Form submitted too fast. Please try again.")
        if elapsed > FORM_MAX_AGE:
            return _("Your form has expired. Please reopen it and resend it.")

        recent = [t for t in request.session.get("oski_dev_sent", [])
                  if time.time() - t < 3600]
        if len(recent) >= MAX_PER_HOUR:
            return _("You have already sent %d requests this hour. "
                      "Please write to us instead at apps@odooskills.com."
                      ) % MAX_PER_HOUR
        request.session["oski_dev_sent"] = recent
        return None

    def _remember_submission(self):
        sent = list(request.session.get("oski_dev_sent", []))
        sent.append(time.time())
        request.session["oski_dev_sent"] = sent

    @http.route("/apps/demande-developpement", type="http", auth="public",
                website=True, sitemap=True)
    def dev_request_form(self, **kw):
        # Ouvert à tous : un prospect qui découvre le catalogue doit pouvoir
        # décrire son besoin sans d'abord créer un compte.
        user = request.env.user
        values = {}
        if not user._is_public():
            partner = user.partner_id
            values = {
                "requester_name": user.name,
                "email": user.email or partner.email or "",
                "company_name": partner.commercial_company_name or "",
                "phone": partner.phone or "",
            }
        return self._render_form(values=values)

    @http.route("/apps/demande-developpement/submit", type="http", auth="public",
                website=True, methods=["POST"])
    def dev_request_submit(self, **post):
        verdict = self._spam_verdict(post)
        if verdict == "honeypot":
            # Un robot ne doit pas apprendre qu'il a été repéré : page de
            # remerciement, aucune demande créée.
            return request.redirect("/apps/demande-developpement/merci")
        if verdict:
            return self._render_form(values=post, error=verdict)

        # Champs obligatoires
        required = ["requester_name", "email", "subject", "description", "budget_range"]
        missing = [f for f in required if not (post.get(f) or "").strip()]
        if missing:
            return self._render_form(values=post,
                                     error=_("Please fill in all required fields."))

        # File validation (server-side)
        files = [f for f in request.httprequest.files.getlist("attachments") if f and f.filename]
        if len(files) > MAX_FILES:
            return self._render_form(values=post,
                                     error=_("Maximum %d files.") % MAX_FILES)
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
                    error=_("File type not allowed: %(filename)s. Allowed: %(allowed)s.") % {
                        "filename": f.filename,
                        "allowed": ", ".join(sorted(ALLOWED_EXT)),
                    })
            if size > MAX_FILE_SIZE:
                return self._render_form(
                    values=post,
                    error=_("File too large: %s (max 10 MB).") % f.filename)
            prepared.append((f.filename, data))
        if total > MAX_TOTAL_SIZE:
            return self._render_form(values=post,
                                     error=_("Total attachment size too high (max 25 MB)."))

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
        }
        # Le modèle rattache la demande à l'utilisateur courant par défaut :
        # pour un visiteur, ce serait l'utilisateur « public », ce qui ne veut
        # rien dire. On coupe explicitement le lien.
        vals["user_id"] = False if env.user._is_public() else env.user.id
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

        self._remember_submission()
        return request.redirect("/apps/demande-developpement/merci?ref=%s" % req.name)

    @http.route("/apps/demande-developpement/merci", type="http", auth="public",
                website=True, sitemap=False)
    def dev_request_thanks(self, ref=None, **kw):
        return request.render("oski_dev_request.thanks_page", {"ref": ref})
