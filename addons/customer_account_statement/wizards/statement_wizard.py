# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date


class AccountPartnerStatementWizard(models.TransientModel):
    _name = 'account.partner.statement.wizard'
    _description = 'Account Statement Wizard'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    date_from = fields.Date(string='From Date', required=True, default=lambda self: self._default_date_from())
    date_to = fields.Date(string='To Date', required=True, default=lambda self: fields.Date.context_today(self))

    def _default_date_from(self):
        today = date.today()
        if today.month >= 4:
            return date(today.year, 4, 1)
        else:
            return date(today.year - 1, 4, 1)

    def action_generate_statement(self):
        self.ensure_one()
        partner = self.partner_id
        partner.write({'statement_date_from': self.date_from, 'statement_date_to': self.date_to})
        partner._generate_statement_lines(self.date_from, self.date_to)
        return {'type': 'ir.actions.act_window', 'res_model': 'res.partner', 'res_id': partner.id, 'view_mode': 'form', 'target': 'current'}

    def action_print_statement(self):
        self.ensure_one()
        partner = self.partner_id
        partner.write({'statement_date_from': self.date_from, 'statement_date_to': self.date_to})
        partner._generate_statement_lines(self.date_from, self.date_to)
        return self.env.ref('customer_account_statement.action_report_partner_statement').report_action(partner)

    def action_send_statement_email(self):
        self.ensure_one()
        partner = self.partner_id
        partner.write({'statement_date_from': self.date_from, 'statement_date_to': self.date_to})
        partner._generate_statement_lines(self.date_from, self.date_to)
        report = self.env.ref('customer_account_statement.action_report_partner_statement')
        pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(report, partner.ids)
        attachment = self.env['ir.attachment'].create({
            'name': 'Account_Statement_%s.pdf' % partner.name,
            'type': 'binary',
            'datas': self.env['ir.attachment']._encode(pdf_content),
            'res_model': 'res.partner',
            'res_id': partner.id,
            'mimetype': 'application/pdf',
        })
        mail_values = {
            'subject': 'Account Statement - %s' % partner.name,
            'body_html': '<p>Dear %s,</p><p>Please find attached your account statement from %s to %s.</p><p>Best regards,<br/>%s</p>' % (
                partner.name, self.date_from.strftime('%d/%m/%Y'), self.date_to.strftime('%d/%m/%Y'), self.env.company.name),
            'email_to': partner.email,
            'attachment_ids': [(6, 0, [attachment.id])],
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Statement Sent'), 'message': _('Account statement has been sent to %s') % partner.email, 'type': 'success', 'sticky': False},
        }
