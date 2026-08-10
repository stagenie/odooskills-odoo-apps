import io

import xlsxwriter

from odoo import _, http
from odoo.http import content_disposition, request


def _columns():
    """Column titles, translated at CALL time.

    They used to be a module-level list of bare strings, so the exported
    file came out with English headers on a French database while the
    screen and the PDF right next to it were translated. `_()` cannot be
    applied at import time either: the language is only known once a
    request is being served, so the call has to happen here, per export.
    """
    return [
        (_('Partner'), 'partner', 32),
        (_('Section'), 'section', 12),
        (_('Date'), 'date', 12),
        (_('Journal'), 'journal', 10),
        (_('Document'), 'name', 18),
        (_('Label'), 'label', 30),
        (_('Due Date'), 'date_maturity', 12),
        (_('Debit'), 'debit', 14),
        (_('Credit'), 'credit', 14),
        (_('Running Balance'), 'cumulative', 16),
    ]


def build_xlsx(wizard):
    """Return the XLSX bytes for an already generated wizard."""
    stream = io.BytesIO()
    workbook = xlsxwriter.Workbook(stream, {'in_memory': True,
                                            'default_date_format': 'yyyy-mm-dd'})
    sheet = workbook.add_worksheet(_('Partner Balance'))
    header = workbook.add_format({'bold': True, 'bg_color': '#DDDDDD', 'border': 1})
    money = workbook.add_format({'num_format': '#,##0.00'})
    date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd'})

    columns = _columns()
    for index, (title, _key, width) in enumerate(columns):
        sheet.write(0, index, title, header)
        sheet.set_column(index, index, width)
    sheet.freeze_panes(1, 0)

    for row_index, line in enumerate(wizard.line_ids, start=1):
        values = {
            'partner': line.partner_id.display_name,
            'section': line.section,
            'date': line.date,
            'journal': line.journal_id.code or '',
            'name': line.name or '',
            'label': line.label or '',
            'date_maturity': line.date_maturity,
            'debit': line.debit,
            'credit': line.credit,
            'cumulative': line.cumulative,
        }
        for col_index, (_title, key, _width) in enumerate(columns):
            value = values[key]
            if key in ('date', 'date_maturity'):
                if value:
                    sheet.write_datetime(row_index, col_index, value, date_fmt)
                else:
                    sheet.write_blank(row_index, col_index, None)
            elif key in ('debit', 'credit', 'cumulative'):
                sheet.write_number(row_index, col_index, value or 0.0, money)
            else:
                sheet.write_string(row_index, col_index, value or '')

    workbook.close()
    return stream.getvalue()


class PartnerBalanceXlsxController(http.Controller):

    @http.route('/oski_partner_balance/xlsx/<int:wizard_id>', type='http', auth='user')
    def download_partner_balance_xlsx(self, wizard_id, **kwargs):
        wizard = request.env['oski.partner.balance.wizard'].browse(wizard_id)
        wizard.check_access('read')
        wizard.exists().ensure_one()
        content = build_xlsx(wizard)
        return request.make_response(content, headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.'
                             'spreadsheetml.sheet'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition('partner_balance.xlsx')),
        ])
