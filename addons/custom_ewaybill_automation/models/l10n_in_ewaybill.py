# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class L10nInEwaybill(models.Model):
    _inherit = 'l10n.in.ewaybill'

    transporter_detail = fields.Char(
        string="Transporter Detail", 
        compute="_compute_transporter_detail",
        help="Shows the name and GSTIN of the selected transporter."
    )

    @api.depends('transporter_id')
    def _compute_transporter_detail(self):
        for rec in self:
            if rec.transporter_id:
                rec.transporter_detail = f"{rec.transporter_id.name} ({rec.transporter_id.vat or 'No GSTIN'})"
            else:
                rec.transporter_detail = False

    def _get_known_transporters(self):
        """
        Dictionary of known Transporter IDs and their names.
        Add more common transporters here.
        """
        return {
            '88AACCA2894D1ZS': 'Allcargo Logistics',
            '29AAACT7966R2Z6': 'TCI Freight',
            # Add others as needed
        }

    def _update_transporter_from_doc_no(self, vals):
        doc_no = vals.get('transportation_doc_no')
        if doc_no:
            vat = doc_no.strip().upper()
            # Search for partner with matching GSTIN or Transporter ID
            partner = self.env['res.partner'].search([('vat', '=', vat)], limit=1)
            
            if not partner:
                # Check known transporters list
                known_transporters = self._get_known_transporters()
                name = known_transporters.get(vat)
                
                # If not in known list, use a placeholder name
                if not name:
                    name = f"Transporter: {vat}"
                
                # Automatically create the transporter partner
                partner = self.env['res.partner'].create({
                    'name': name,
                    'vat': vat,
                    'is_company': True,
                    'supplier_rank': 1, # Mark as a vendor/supplier
                })
            
            if partner:
                vals['transporter_id'] = partner.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'transportation_doc_no' in vals and not vals.get('transporter_id'):
                self._update_transporter_from_doc_no(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'transportation_doc_no' in vals and not vals.get('transporter_id'):
            self._update_transporter_from_doc_no(vals)
        return super().write(vals)

    @api.onchange('transportation_doc_no')
    def _onchange_transportation_doc_no(self):
        """
        Automatically populate Transporter field when Transporter Doc No is entered.
        If not found, it will trigger the create/write logic upon saving.
        To show it immediately in UI, we search/suggest here.
        """
        if self.transportation_doc_no:
            vat = self.transportation_doc_no.strip().upper()
            partner = self.env['res.partner'].search([('vat', '=', vat)], limit=1)
            
            if partner:
                self.transporter_id = partner
            else:
                # Suggest from known list in the UI immediately
                known = self._get_known_transporters()
                if vat in known:
                    # We don't create it in onchange (side effects), 
                    # but we can notify the user or wait for save.
                    pass

    @api.onchange('transporter_id')
    def _onchange_transporter_id(self):
        if self.transporter_id and self.transporter_id.vat:
            self.transportation_doc_no = self.transporter_id.vat
