"""Lien « Request a change » dans le courriel de fin d'essai du store.

Un gabarit de courriel ne s'hérite pas : à l'installation on insère un
paragraphe dans chaque langue de `body_html` (colonne jsonb), avant la
signature ; à la désinstallation on remet le corps d'origine, gardé dans
un paramètre système. Le store (oski_app_store) n'est pas modifié.
"""
import json

TEMPLATE_XMLID = "oski_app_store.mail_template_trial_ended"
BACKUP_PARAM = "oski_module_feedback.trial_body_backup"
MARKER = 'data-oski-feedback="1"'

TEXTS = {
    "en_US": ("Missing something?", "Request a change", "we read every request."),
    "fr_FR": ("Il vous manque quelque chose ?", "Demander une évolution", "chaque demande est lue."),
}


def _paragraph(lang):
    question, link, tail = TEXTS.get(lang) or TEXTS["en_US"]
    return (
        '<p %s>%s <a t-att-href="object._feedback_url()" '
        'style="color: #714B67; font-weight: bold;">%s</a> — %s</p>\n    '
        % (MARKER, question, link, tail)
    )


def _insert(html, lang):
    if MARKER in html:
        return html
    # Avant le dernier paragraphe (la signature) ; sinon avant la fin du bloc.
    index = html.rfind("<p")
    if index == -1:
        index = html.rfind("</div>")
    if index == -1:
        return html + _paragraph(lang)
    return html[:index] + _paragraph(lang) + html[index:]


def _template(env):
    return env.ref(TEMPLATE_XMLID, raise_if_not_found=False)


def _read_body(env, template):
    env.flush_all()
    env.cr.execute("SELECT body_html FROM mail_template WHERE id = %s", (template.id,))
    return env.cr.fetchone()[0] or {}


def _write_body(env, template, body):
    env.cr.execute(
        "UPDATE mail_template SET body_html = %s::jsonb WHERE id = %s",
        (json.dumps(body), template.id),
    )
    template.invalidate_recordset(["body_html"])


def post_init_hook(env):
    template = _template(env)
    if not template:
        return
    body = _read_body(env, template)
    params = env["ir.config_parameter"].sudo()
    if not params.get_param(BACKUP_PARAM) and not any(MARKER in v for v in body.values()):
        params.set_param(BACKUP_PARAM, json.dumps(body))
    _write_body(env, template, {lang: _insert(html, lang) for lang, html in body.items()})


def uninstall_hook(env):
    template = _template(env)
    if not template:
        return
    params = env["ir.config_parameter"].sudo()
    backup = params.get_param(BACKUP_PARAM)
    if backup:
        _write_body(env, template, json.loads(backup))
    else:
        body = _read_body(env, template)
        cleaned = {}
        for lang, html in body.items():
            start = html.find("<p %s" % MARKER)
            end = html.find("</p>", start)
            cleaned[lang] = html if start == -1 else html[:start] + html[end + len("</p>\n    "):]
        _write_body(env, template, cleaned)
    params.set_param(BACKUP_PARAM, False)
