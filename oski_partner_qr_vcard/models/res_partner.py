import base64
from io import BytesIO

from odoo import api, fields, models

try:
    import qrcode
except ImportError:  # pragma: no cover
    qrcode = None


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
            f"FN:{self.name or ''}",
            f"N:{self.name or ''};;;;",
        ]
        if org:
            lines.append(f"ORG:{org}")
        if self.function:
            lines.append(f"TITLE:{self.function}")
        if self.email:
            lines.append(f"EMAIL;TYPE=INTERNET:{self.email}")
        if self.phone:
            lines.append(f"TEL;TYPE=WORK,VOICE:{self.phone}")
        if self.website:
            lines.append(f"URL:{self.website}")
        lines.append("END:VCARD")
        return "\r\n".join(lines)

    @api.depends(
        "name", "email", "phone",
        "function", "website", "company_name", "parent_id",
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
