# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountDebitNoteLine(models.TransientModel):
    _name = 'account.debit.note.line'
    _description = 'Debit Note Line Selection'

    reversal_id = fields.Many2one('account.debit.note', string='Debit Note')
    move_line_id = fields.Many2one('account.move.line', string='Original Line')
    product_id = fields.Many2one('product.product', related='move_line_id.product_id', string='Product', readonly=True)
    name = fields.Char(related='move_line_id.name', string='Description', readonly=True)
    original_quantity = fields.Float(related='move_line_id.quantity', string='Original Qty', readonly=True)
    price_unit = fields.Float(related='move_line_id.price_unit', string='Unit Price', readonly=True)
    tax_ids = fields.Many2many('account.tax', related='move_line_id.tax_ids', string='Taxes', readonly=True)
    
    qty_to_debit = fields.Float(string='Qty to Debit')
    quantity = fields.Float(string='Qty to Debit')


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

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
    reversal_line_ids = fields.One2many('account.debit.note.line', 'reversal_id', string='Lines to Debit')

    @api.model
    def default_get(self, fields_list):
        res = super(AccountDebitNote, self).default_get(fields_list)
        if 'move_ids' in res and res.get('move_ids'):
            move_ids = self.env['account.move'].browse(res['move_ids'][0][2])
            debit_lines = []
            for move in move_ids:
                for line in move.invoice_line_ids:
                    if line.display_type == 'product':
                        debit_lines.append((0, 0, {
                            'move_line_id': line.id,
                            'quantity': line.quantity,
                        }))
            res['reversal_line_ids'] = debit_lines
            res['copy_lines'] = True
        return res

    def _prepare_default_values(self, move):
        res = super(AccountDebitNote, self)._prepare_default_values(move)
        if self.l10n_in_gst_reason:
            res['l10n_in_gst_reason'] = self.l10n_in_gst_reason
        # Ensure we don't drop lines if there are debit_lines
        if self.reversal_line_ids and 'line_ids' in res:
            del res['line_ids']
        return res

    def create_debit(self):
        # We temporarily force copy_lines to True to let standard logic copy lines
        orig_copy_lines = self.copy_lines
        if self.reversal_line_ids:
            self.copy_lines = True
            
        action = super(AccountDebitNote, self).create_debit()
        
        self.copy_lines = orig_copy_lines
        
        if action.get('res_id'):
            new_moves = self.env['account.move'].browse(action['res_id'])
        else:
            new_moves = self.env['account.move'].search(action['domain'])
            
        qty_mapping = {line.move_line_id.id: line.quantity for line in self.reversal_line_ids}
        
        for move in new_moves:
            orig_move = move.debit_origin_id
            if not orig_move:
                continue
                
            lines_commands = []
            new_product_lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
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
                
            # Recompute totals
            move.with_context(check_move_validity=False)._compute_tax_totals()
            
        return action
