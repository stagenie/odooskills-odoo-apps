from collections import defaultdict
from datetime import datetime

from odoo import _, api, models

ACCOUNT_TYPES = {
    'receivable': ['asset_receivable'],
    'payable': ['liability_payable'],
    'net': ['asset_receivable', 'liability_payable'],
}


class PartnerBalanceEngine(models.AbstractModel):
    _name = 'oski.partner.balance.engine'
    _description = 'Partner Balance Engine'

    @api.model
    def _sections(self, scope):
        """Return the list of sections a given scope produces."""
        if scope == 'both':
            return ['receivable', 'payable']
        if scope == 'net':
            return ['net']
        return [scope]

    @api.model
    def _account_types(self, section):
        return list(ACCOUNT_TYPES[section])

    @api.model
    def _base_domain(self, options, section):
        """Domain on account.move.line, without any date boundary."""
        domain = [
            ('account_id.account_type', 'in', self._account_types(section)),
            ('partner_id', '!=', False),
            ('move_id.oski_exclude_from_balance', '=', False),
        ]
        if options.get('target_moves', 'posted') == 'all':
            domain.append(('parent_state', 'in', ('draft', 'posted')))
        else:
            domain.append(('parent_state', '=', 'posted'))
        if options.get('partner_ids'):
            domain.append(('partner_id', 'in', list(options['partner_ids'])))
        journal_ids = list(options.get('journal_ids') or [])
        journal_filter = options.get('journal_filter', 'all')
        if journal_ids and journal_filter == 'include':
            domain.append(('journal_id', 'in', journal_ids))
        elif journal_ids and journal_filter == 'exclude':
            domain.append(('journal_id', 'not in', journal_ids))
        return domain

    @api.model
    def _opening_balances(self, options, section):
        """Balance carried forward, per partner, strictly before date_from."""
        domain = self._base_domain(options, section) + [
            ('date', '<', options['date_from']),
        ]
        groups = self.env['account.move.line']._read_group(
            domain, ['partner_id'], ['balance:sum'])
        return {partner.id: balance for partner, balance in groups}

    @api.model
    def _sort_key(self, line):
        """Chronological key: date, then operation datetime, then id.

        `id` is the last resort so that the order is total even when two moves
        share both a date and an operation datetime.
        """
        return (
            line.date,
            line.move_id.oski_operation_datetime or datetime(1970, 1, 1),
            line.id,
        )

    @api.model
    def _partner_axis(self, options, partner_ids):
        """Which partner each line's running balance accumulates on.

        The identity here: a statement speaks of one partner, and its running
        balance belongs to that partner alone.

        The seam exists so a consolidation module can remap a subtree of
        companies onto its root WITHOUT restating the chronological rules
        below. A group statement whose sections replay one subsidiary after
        the other teaches nobody anything: the whole point is a single
        balance, running in global date order over the group.

        A row keeps its OWN partner in `partner_id` whatever the axis says:
        a consolidated statement where one can no longer see which company
        each entry came from is unusable for the person doing the chasing.
        """
        return {partner_id: partner_id for partner_id in partner_ids}

    @api.model
    def _build_rows(self, options):
        """Ordered, cumulated statement rows. One source for screen, PDF, XLSX."""
        AccountMoveLine = self.env['account.move.line']
        rows = []
        sequence = 0
        include_opening = bool(options.get('include_opening'))
        for section in self._sections(options['scope']):
            openings = self._opening_balances(options, section) if include_opening else {}
            domain = self._base_domain(options, section) + [
                ('date', '>=', options['date_from']),
                ('date', '<=', options['date_to']),
            ]
            lines = AccountMoveLine.search(domain)
            axis = self._partner_axis(
                options, set(lines.partner_id.ids) | set(openings))
            per_partner = defaultdict(list)
            for line in lines:
                per_partner[axis[line.partner_id.id]].append(line)
            axis_openings = defaultdict(float)
            for partner_id, amount in openings.items():
                axis_openings[axis[partner_id]] += amount
            partner_ids = set(per_partner) | {
                pid for pid, amount in axis_openings.items() if amount
            }
            partners = self.env['res.partner'].browse(sorted(partner_ids))
            for partner in partners.sorted(lambda p: (p.display_name or '', p.id)):
                cumulative = axis_openings.get(partner.id, 0.0)
                partner_lines = sorted(per_partner.get(partner.id, []), key=self._sort_key)
                if not partner_lines and not cumulative:
                    continue
                if include_opening:
                    sequence += 1
                    rows.append({
                        'sequence': sequence,
                        'partner_id': partner.id,
                        'group_partner_id': partner.id,
                        'section': section,
                        'date': options['date_from'],
                        'operation_datetime': False,
                        'journal_id': False,
                        'move_id': False,
                        'move_line_id': False,
                        'name': '',
                        'ref': '',
                        'label': _('Opening balance'),
                        'date_maturity': False,
                        'debit': 0.0,
                        'credit': 0.0,
                        'balance': 0.0,
                        'cumulative': cumulative,
                        'amount_residual': 0.0,
                        'is_opening': True,
                    })
                for line in partner_lines:
                    cumulative += line.balance
                    sequence += 1
                    rows.append({
                        'sequence': sequence,
                        # The line's OWN partner, never the axis: on a
                        # consolidated statement this column is what tells the
                        # reader which company of the group each entry belongs
                        # to. Writing `partner.id` here would still satisfy
                        # every non-consolidated test, and quietly make the
                        # consolidated statement unreadable.
                        'partner_id': line.partner_id.id,
                        'group_partner_id': partner.id,
                        'section': section,
                        'date': line.date,
                        'operation_datetime': line.move_id.oski_operation_datetime,
                        'journal_id': line.journal_id.id,
                        'move_id': line.move_id.id,
                        'move_line_id': line.id,
                        'name': line.move_id.name or '',
                        'ref': line.ref or line.move_id.ref or '',
                        'label': line.name or '',
                        'date_maturity': line.date_maturity,
                        'debit': line.debit,
                        'credit': line.credit,
                        'balance': line.balance,
                        'cumulative': cumulative,
                        'amount_residual': line.amount_residual,
                        'is_opening': False,
                    })
        return rows
