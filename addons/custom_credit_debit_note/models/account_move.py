# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

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
        string="GST Reason Code",
        copy=False,
    )
