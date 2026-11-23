import logging

from odoo import _, api, fields, models
from odoo.tools.misc import format_datetime

_logger = logging.getLogger(__name__)

DEFAULT_MAX_PENDING_HOURS = 6.0


class OskiMailQueueCheck(models.Model):
    _name = "oski.mail.queue.check"
    # L'alerte prend la forme d'une activité, et ``mail.activity`` abonne
    # d'office le destinataire au fil du document : le modèle doit donc porter
    # ``mail.thread``, faute de quoi la création d'activité échoue.
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Email Queue Check"
    _order = "checked_on desc, id desc"
    _rec_name = "checked_on"

    checked_on = fields.Datetime(
        string="Checked On", required=True, default=fields.Datetime.now, index=True)
    pending_count = fields.Integer(string="Pending")
    failed_count = fields.Integer(string="Failed")
    oldest_pending_hours = fields.Float(string="Oldest Pending (h)", digits=(10, 1))
    verdict = fields.Selection(
        [("ok", "Healthy"), ("warning", "Slowed Down"), ("critical", "Failed")],
        string="Verdict", required=True, default="ok", index=True)
    note = fields.Text(string="Details")

    def _max_pending_hours(self):
        value = self.env["ir.config_parameter"].sudo().get_param(
            "oski_mail_queue_monitor.max_pending_hours", DEFAULT_MAX_PENDING_HOURS)
        try:
            return float(value)
        except (TypeError, ValueError):
            return DEFAULT_MAX_PENDING_HOURS

    @api.depends("checked_on")
    def _compute_display_name(self):
        # Le nom affiché (fil d'Ariane, liens) : la date du relevé dans la langue et
        # le fuseau du lecteur, pas la valeur UTC brute du champ.
        for check in self:
            check.display_name = format_datetime(self.env, check.checked_on) if check.checked_on else ""

    @api.model
    def _measure_queue(self):
        """Relève l'état de la file, sans rien en conclure.

        Séparé du verdict pour que la règle de décision soit éprouvable sans
        avoir à fabriquer une file entière.
        """
        Mail = self.env["mail.mail"].sudo()
        pending = Mail.search([("state", "=", "outgoing")], order="create_date asc")
        failed = Mail.search([("state", "=", "exception")])
        oldest_hours = 0.0
        if pending:
            delta = fields.Datetime.now() - pending[0].create_date
            oldest_hours = delta.total_seconds() / 3600.0
        causes = {}
        for mail in failed:
            label = dict(Mail._fields["failure_type"]._description_selection(
                self.env)).get(
                mail.failure_type, _("Unspecified cause"))
            causes[label] = causes.get(label, 0) + 1
        return {
            "pending_count": len(pending),
            "failed_count": len(failed),
            "oldest_pending_hours": oldest_hours,
            "causes": causes,
        }

    @api.model
    def _verdict_for(self, measure):
        """Un seul courriel en échec suffit à alerter : notre propre file en a
        laissé mourir vingt et un en silence pendant trois mois et demi."""
        if measure["failed_count"]:
            return "critical"
        if measure["oldest_pending_hours"] > self._max_pending_hours():
            return "warning"
        return "ok"

    @api.model
    def _note_for(self, measure):
        lines = []
        if measure["oldest_pending_hours"]:
            lines.append(_("The oldest pending email has been waiting for %.1f h.",
                           measure["oldest_pending_hours"]))
        for label, count in sorted(measure["causes"].items(), key=lambda item: -item[1]):
            lines.append(self.env._("%(cause)s: %(count)s", cause=label, count=count))
        return "\n".join(lines) or False

    @api.model
    def _cron_check_queue(self):
        if not self.env.context.get("lang"):
            # Une tâche planifiée tourne sans langue : le relevé est écrit
            # dans celle de l'administrateur, qui le lit.
            admin = self.env.ref("base.user_admin", raise_if_not_found=False)
            self = self.with_context(lang=(admin or self.env.user).lang)
        measure = self._measure_queue()
        check = self.create({
            "checked_on": fields.Datetime.now(),
            "pending_count": measure["pending_count"],
            "failed_count": measure["failed_count"],
            "oldest_pending_hours": measure["oldest_pending_hours"],
            "verdict": self._verdict_for(measure),
            "note": self._note_for(measure),
        })
        if check.verdict != "ok":
            check._raise_alert()
        return check

    def _alert_user_ids(self):
        """Les administrateurs vivants.

        En 18, ``users`` porte aussi ceux qui tiennent le groupe par
        implication (le cœur les y inscrit). Le superutilisateur technique est
        écarté : une activité posée à OdooBot n'est lue par personne.
        """
        root = self.env.ref("base.user_root", raise_if_not_found=False)
        users = self.env.ref("base.group_system").users.filtered(
            lambda user: user.active and not user.share)
        return users - root if root else users

    def _open_alerts(self):
        """Les alertes encore ouvertes, tous relevés confondus."""
        return self.env["mail.activity"].sudo().search([
            ("res_model", "=", self._name),
            ("activity_type_id", "=", self.env.ref("mail.mail_activity_data_todo").id),
        ])

    def _raise_alert(self):
        """Pose une activité aux administrateurs — jamais un courriel.

        Prévenir d'une file de courriels morte en envoyant un courriel
        reviendrait à confier le diagnostic au malade. Une activité se lit dans
        l'interface, quel que soit l'état du serveur sortant.

        Une seule alerte reste ouverte à la fois : une panne qui dure des
        semaines ne doit pas produire une activité par jour.
        """
        self.ensure_one()
        if self._open_alerts():
            return False
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        model_id = self.env["ir.model"]._get(self._name).id
        def summary_for(user):
            # Chaque administrateur lit l'alerte dans sa langue.
            env = self.with_context(lang=user.lang or self.env.lang).env
            if self.verdict == "critical":
                return env._("Failed emails: %s", self.failed_count)
            return env._("Email queue stalled for %.1f h",
                         self.oldest_pending_hours)
        # ``mail_activity_quick_update`` coupe la notification que Odoo
        # enverrait à l'assigné : prévenir d'une file de courriels morte par
        # courriel reviendrait à confier le diagnostic au malade.
        activities = self.env["mail.activity"].sudo().with_context(
            mail_activity_quick_update=True).create([{
            "res_model_id": model_id,
            "res_id": self.id,
            "activity_type_id": activity_type.id,
            "summary": summary_for(user),
            "note": self.note or False,
            "user_id": user.id,
        } for user in self._alert_user_ids()])
        return activities

    def action_open_failed_mails(self):
        # Libellé sorti du dict : l'extracteur d'Odoo 19/20 prendrait aussi
        # le tuple du domaine qui suit pour un texte à traduire.
        name = self.env._("Failed Emails")
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "mail.mail",
            "view_mode": "list,form",
            "domain": [("state", "=", "exception")],
        }

    def action_retry_failed_mails(self):
        """Remet en file d'attente tout ce qui est en échec."""
        failed = self.env["mail.mail"].sudo().search([("state", "=", "exception")])
        failed.mark_outgoing()
        return len(failed)
