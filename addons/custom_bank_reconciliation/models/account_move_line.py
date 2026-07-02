from odoo import models, api, fields
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Create a custom field for the closing balance to bypass Odoo core restrictions
    gdr_closing_balance = fields.Monetary(
        string='Closing Balance',
        compute='_compute_gdr_closing_balance',
        store=True,
        aggregator='sum',
        help="Custom closing balance for accurate month-wise grouping."
    )

    def _compute_gdr_closing_balance(self):
        for rec in self:
            rec.gdr_closing_balance = rec.cumulated_balance

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)
        # Trick the JS frontend into believing this is a standard stored field
        # so it enables the group row aggregates.
        if 'gdr_closing_balance' in res:
            res['gdr_closing_balance']['store'] = True
        return res

    @api.model
    @api.readonly
    def web_read_group(self, domain, groupby, aggregates=(), limit=None, offset=0, order=None, **kwargs):
        """Override to compute closing balance per group for our custom field."""
        has_custom = False
        cleaned_aggregates = []
        requested_cum_keys = []
        
        # We also support the original cumulated_balance just in case
        for agg in aggregates:
            if agg.startswith('gdr_closing_balance') or agg.startswith('cumulated_balance'):
                has_custom = True
                requested_cum_keys.append(agg)
            else:
                cleaned_aggregates.append(agg)

        # Force add if stripped
        if not requested_cum_keys:
            requested_cum_keys.extend(['gdr_closing_balance:sum', 'cumulated_balance:sum'])
            has_custom = True

        res = super().web_read_group(domain, groupby, cleaned_aggregates, limit=limit, offset=offset, order=order, **kwargs)

        if not has_custom:
            return res

        groups = res.get('groups', [])
        if not groups:
            return res

        base_model = self.sudo()

        for group in groups:
            extra_domain = group.get('__extra_domain', [])
            end_date = None
            
            for leaf in extra_domain:
                if isinstance(leaf, (list, tuple)) and len(leaf) == 3:
                    field, op, val = leaf
                    if field == 'date' and op == '<':
                        from datetime import date, timedelta
                        if isinstance(val, str):
                            end_date = date.fromisoformat(val[:10]) - timedelta(days=1)
                        elif isinstance(val, date):
                            end_date = val - timedelta(days=1)
                    elif field == 'date' and op == '<=':
                        from datetime import date as date_type
                        if isinstance(val, str):
                            end_date = date_type.fromisoformat(val[:10])
                        elif isinstance(val, date_type):
                            end_date = val

            if end_date:
                other_leaves = [
                    l for l in extra_domain 
                    if isinstance(l, (list, tuple)) and len(l) == 3 and l[0] != 'date'
                ]
                cum_domain = list(domain) + [('date', '<=', str(end_date))] + other_leaves
            else:
                cum_domain = expression.AND([domain, extra_domain])

            try:
                cum_query = base_model._search(cum_domain, bypass_access=True)
                from odoo.tools import SQL
                result = self.env.execute_query(cum_query.select(
                    SQL("COALESCE(SUM(%s), 0)", SQL.identifier(cum_query.table, "balance")),
                ))
                closing_balance = result[0][0] if result else 0.0
                
                # Assign to all requested keys
                for k in requested_cum_keys:
                    group[k] = closing_balance
                    
                # Explicit fallback injections just in case UI looks for base names
                group['gdr_closing_balance'] = closing_balance
                group['cumulated_balance'] = closing_balance
                    
            except Exception as e:
                _logger.error("Failed to compute closing_balance for group: %s", e)
                for k in requested_cum_keys:
                    group[k] = 0.0

        return res
