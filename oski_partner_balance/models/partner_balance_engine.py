from odoo import api, models

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
