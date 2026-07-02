from odoo import models, api, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def action_open_reconcile(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "custom_bank_reconciliation.action_bank_statement_line_reconcile"
        )
        action['domain'] = [
            ('journal_id', '=', self.id),
            ('is_reconciled', '=', False),
        ]
        action['context'] = {
            'default_journal_id': self.id,
            'search_default_journal_id': self.id,
            'search_default_to_reconcile': 1,
        }
        action['name'] = _('Reconcile %s', self.name)
        return action

    def action_open_import_file(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "custom_bank_reconciliation.action_bank_statement_import_wizard"
        )
        action['context'] = {
            'default_journal_id': self.id,
        }
        return action
