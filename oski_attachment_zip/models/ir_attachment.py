import io
import re
import zipfile

from odoo import _, api, models
from odoo.exceptions import UserError

MAX_RECORDS = 200
DEFAULT_MAX_SIZE_MB = 200
UNSAFE = re.compile(r"[\\/:*?\"<>|\x00-\x1f]")


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def _oski_zip_action(self, records):
        """Ce que rend l'entrée de menu : une URL de téléchargement.

        Le refus se prononce ici, devant l'utilisateur, et non dans le
        contrôleur : une page d'erreur du navigateur n'explique rien, une
        boîte de dialogue si.
        """
        if not records:
            raise UserError(_("Aucune fiche sélectionnée."))
        if len(records) > MAX_RECORDS:
            raise UserError(_(
                "Le téléchargement groupé s'arrête à %(max)s fiches ; "
                "%(count)s sont sélectionnées.",
                max=MAX_RECORDS, count=len(records)))
        if not self._oski_zip_attachments(records):
            raise UserError(_(
                "Ces fiches ne portent aucune pièce jointe téléchargeable."))
        return {
            "type": "ir.actions.act_url",
            "target": "download",
            "url": "/oski/attachment/zip?model=%s&ids=%s" % (
                records._name, ",".join(str(res_id) for res_id in records.ids)),
        }

    @api.model
    def _oski_zip_attachments(self, records):
        """Les pièces d'un jeu de fiches, lues avec les droits de l'appelant.

        Aucun ``sudo`` : une pièce jointe hérite de l'accès à son document, et
        le document vient d'être vérifié. Faire autrement livrerait des
        fichiers que l'utilisateur n'a pas le droit de voir.

        Sont écartés les valeurs de champs binaires (``res_field``), qui ne
        sont pas des pièces jointes, et les pièces servies par une URL, qui
        n'ont aucun contenu à mettre dans l'archive.
        """
        records.check_access("read")
        return self.search(
            [
                ("res_model", "=", records._name),
                ("res_id", "in", records.ids),
                ("res_field", "=", False),
                ("url", "=", False),
            ],
            order="res_id, name, id",
        )

    @api.model
    def _oski_zip_bytes(self, records):
        attachments = self._oski_zip_attachments(records)
        if not attachments:
            raise UserError(_(
                "Ces fiches ne portent aucune pièce jointe téléchargeable."))
        limit = self._oski_zip_size_limit()
        total = sum(attachments.mapped("file_size"))
        if limit and total > limit:
            raise UserError(_(
                "L'archive pèserait %(size)s Mo, au-delà de la limite de "
                "%(limit)s Mo. Réduisez la sélection.",
                size=round(total / (1024 * 1024)),
                limit=round(limit / (1024 * 1024))))

        by_record = {record.id: record for record in records}
        buffer = io.BytesIO()
        used = set()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for attachment in attachments:
                content = attachment.raw
                if content is None:
                    continue
                folder = ""
                if len(records) > 1:
                    record = by_record.get(attachment.res_id)
                    folder = self._oski_zip_safe(
                        record.display_name if record else str(attachment.res_id))
                name = self._oski_zip_unique(
                    folder, self._oski_zip_safe(attachment.name or "piece"), used)
                archive.writestr(name, content)
        return self._oski_zip_name(records), buffer.getvalue()

    @api.model
    def _oski_zip_size_limit(self):
        raw = self.env["ir.config_parameter"].sudo().get_param(
            "oski_attachment_zip.max_size_mb", DEFAULT_MAX_SIZE_MB)
        try:
            megabytes = float(raw)
        except (TypeError, ValueError):
            megabytes = DEFAULT_MAX_SIZE_MB
        # Zéro — ou moins — lève la limite : c'est la façon documentée de
        # dire « pas de plafond », et non une valeur à corriger en silence.
        return int(megabytes * 1024 * 1024) if megabytes > 0 else 0

    @api.model
    def _oski_zip_name(self, records):
        label = self.env["ir.model"]._get(records._name).name or records._name
        if len(records) == 1:
            return "%s - %s.zip" % (
                self._oski_zip_safe(label),
                self._oski_zip_safe(records.display_name or str(records.id)))
        return "%s - %s fiches.zip" % (self._oski_zip_safe(label), len(records))

    @api.model
    def _oski_zip_safe(self, name):
        """Un nom de fichier, jamais un chemin.

        Une pièce jointe nommée ``../../etc/passwd`` écrirait hors de son
        dossier chez qui décompresse l'archive.
        """
        cleaned = UNSAFE.sub("_", (name or "").strip()).lstrip(". ")
        return cleaned[:120] or "piece"

    @api.model
    def _oski_zip_unique(self, folder, name, used):
        candidate = "%s/%s" % (folder, name) if folder else name
        if candidate not in used:
            used.add(candidate)
            return candidate
        stem, dot, suffix = name.rpartition(".")
        if not dot:
            stem, suffix = name, ""
        index = 2
        while True:
            numbered = "%s (%s)%s%s" % (stem, index, "." if suffix else "", suffix)
            candidate = "%s/%s" % (folder, numbered) if folder else numbered
            if candidate not in used:
                used.add(candidate)
                return candidate
            index += 1
