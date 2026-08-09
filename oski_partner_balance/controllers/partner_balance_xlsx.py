import io

import xlsxwriter

from odoo import http
from odoo.http import content_disposition, request

COLUMNS = [
    ('Partner', 'partner', 32),
    ('Section', 'section', 12),
    ('Date', 'date', 12),
    ('Journal', 'journal', 10),
    ('Document', 'name', 18),
    ('Label', 'label', 30),
    ('Due Date', 'date_maturity', 12),
    ('Debit', 'debit', 14),
    ('Credit', 'credit', 14),
    ('Running Balance', 'cumulative', 16),
]


def build_xlsx(wizard):
    """Return the XLSX bytes for an already generated wizard."""
    stream = io.BytesIO()
    workbook = xlsxwriter.Workbook(stream, {'in_memory': True,
                                            'default_date_format': 'yyyy-mm-dd'})
    sheet = workbook.add_worksheet('Partner Balance')
    header = workbook.add_format({'bold': True, 'bg_color': '#DDDDDD', 'border': 1})
    money = workbook.add_format({'num_format': '#,##0.00'})
    date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd'})

    for index, (title, _key, width) in enumerate(COLUMNS):
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
        for col_index, (_title, key, _width) in enumerate(COLUMNS):
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
