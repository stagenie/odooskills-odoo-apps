import base64
from io import BytesIO

from odoo import api, fields, models

try:
    import qrcode
except ImportError:  # pragma: no cover
    qrcode = None


def _vcard_escape(value):
    """Échappe une valeur texte vCard 3.0 (RFC 2426 §4) : \\ , ; et sauts de ligne."""
    value = (value or "").replace("\\", "\\\\")
    for char in (",", ";"):
        value = value.replace(char, "\\" + char)
    return value.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")


class ResPartner(models.Model):
    _inherit = "res.partner"

    oski_qr_vcard = fields.Binary(
        string="QR vCard",
        compute="_compute_oski_qr_vcard",
        attachment=True,
        help="Code QR encodant la fiche au format vCard 3.0 (à scanner avec un smartphone).",
    )

    def _oski_build_vcard(self):
        """Construit la chaîne vCard 3.0 du contact."""
        self.ensure_one()
        org = self.company_name or (self.parent_id.name if self.parent_id else "")
        lines = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"FN:{_vcard_escape(self.name)}",
            f"N:{_vcard_escape(self.name)};;;;",
        ]
        if org:
            lines.append(f"ORG:{_vcard_escape(org)}")
        if self.function:
            lines.append(f"TITLE:{_vcard_escape(self.function)}")
        if self.email:
            lines.append(f"EMAIL;TYPE=INTERNET:{_vcard_escape(self.email)}")
        if self.phone:
            lines.append(f"TEL;TYPE=WORK,VOICE:{_vcard_escape(self.phone)}")
        if self.website:
            lines.append(f"URL:{_vcard_escape(self.website)}")
        lines.append("END:VCARD")
        return "\r\n".join(lines)

    @api.depends(
        "name", "email", "phone",
        "function", "website", "company_name", "parent_id.name",
    )
    def _compute_oski_qr_vcard(self):
        for partner in self:
            if not qrcode or not partner.name:
                partner.oski_qr_vcard = False
                continue
            img = qrcode.make(partner._oski_build_vcard())
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            partner.oski_qr_vcard = base64.b64encode(buffer.getvalue())
