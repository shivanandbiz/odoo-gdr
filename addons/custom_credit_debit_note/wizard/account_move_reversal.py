# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMoveReversalLine(models.TransientModel):
    _name = 'account.move.reversal.line'
    _description = 'Credit Note Line Selection'

    reversal_id = fields.Many2one('account.move.reversal', string='Reversal')
    move_line_id = fields.Many2one('account.move.line', string='Original Line')
    product_id = fields.Many2one('product.product', related='move_line_id.product_id', string='Product', readonly=True)
    name = fields.Char(related='move_line_id.name', string='Description', readonly=True)
    original_quantity = fields.Float(related='move_line_id.quantity', string='Original Qty', readonly=True)
    price_unit = fields.Float(related='move_line_id.price_unit', string='Unit Price', readonly=True)
    tax_ids = fields.Many2many('account.tax', related='move_line_id.tax_ids', string='Taxes', readonly=True)
    
    quantity = fields.Float(string='Qty to Reverse')

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_in_gst_reason = fields.Selection(
        selection=[
            ('01', '01-Sales Return'),
            ('02', '02-Post Sale Discount'),
            ('03', '03-Deficiency in services'),
            ('04', '04-Correction in Invoice'),
            ('05', '05-Change in POS'),
            ('06', '06-Finalization of Provisional assessment'),
            ('07', '07-Others')
        ],
        string="GST Reason Code"
    )
    reversal_line_ids = fields.One2many('account.move.reversal.line', 'reversal_id', string='Lines to Reverse')

    @api.model
    def default_get(self, fields_list):
        res = super(AccountMoveReversal, self).default_get(fields_list)
        if 'move_ids' in res and res.get('move_ids'):
            move_ids = self.env['account.move'].browse(res['move_ids'][0][2])
            reversal_lines = []
            for move in move_ids:
                for line in move.invoice_line_ids:
                    if line.display_type == 'product':
                        reversal_lines.append((0, 0, {
                            'move_line_id': line.id,
                            'quantity': line.quantity,
                        }))
            res['reversal_line_ids'] = reversal_lines
        return res

    def _prepare_default_reversal(self, move):
        res = super(AccountMoveReversal, self)._prepare_default_reversal(move)
        if self.l10n_in_gst_reason:
            res['l10n_in_gst_reason'] = self.l10n_in_gst_reason
        return res

    def reverse_moves(self, is_modify=False):
        action = super(AccountMoveReversal, self).reverse_moves(is_modify=is_modify)
        
        # Get the new moves created
        if action.get('res_id'):
            new_moves = self.env['account.move'].browse(action['res_id'])
        else:
            new_moves = self.env['account.move'].search(action['domain'])
            
        moves_to_update = new_moves
        
        # If is_modify=True, new_moves are the new draft invoices. We also need to find the credit notes that were created.
        if is_modify:
            # Reversals are linked via reversed_entry_id
            reversals = self.env['account.move'].search([('reversed_entry_id', 'in', self.move_ids.ids)])
            moves_to_update |= reversals
            
        # Create a mapping of original move lines to new quantities
        qty_mapping = {line.move_line_id.id: line.quantity for line in self.reversal_line_ids}
        
        for move in moves_to_update:
            lines_commands = []
            new_product_lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
            
            orig_move = move.reversed_entry_id
            if not orig_move and is_modify:
                # This is the new draft invoice, not the reversal
                orig_move = self.move_ids[0] # Simplification for single move
            
            if orig_move:
                orig_lines = orig_move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
                for i, line in enumerate(new_product_lines):
                    if i < len(orig_lines):
                        orig_line = orig_lines[i]
                        if orig_line.id in qty_mapping:
                            qty = qty_mapping[orig_line.id]
                            if qty <= 0:
                                lines_commands.append((2, line.id, 0))
                            elif qty != line.quantity:
                                lines_commands.append((1, line.id, {'quantity': qty}))
                                
            if lines_commands:
                move.with_context(check_move_validity=False).write({'invoice_line_ids': lines_commands})
                
            # Recompute move totals
            move.with_context(check_move_validity=False)._compute_tax_totals()
            
        return action
