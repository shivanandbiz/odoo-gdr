import base64
import csv
import io
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BankStatementImportWizard(models.TransientModel):
    _name = 'custom.bank.statement.import'
    _description = 'Import Bank Statement'

    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        required=True,
        domain=[('type', 'in', ['bank', 'cash'])],
    )
    import_file = fields.Binary(string='Statement File (CSV)', required=True, attachment=False)
    filename = fields.Char(string='Filename')

    def _parse_csv_file(self, file_data):
        """Parse the CSV file and return a list of transaction dicts."""
        try:
            content = base64.b64decode(file_data).decode('utf-8-sig')
        except Exception:
            raise UserError(_("Cannot decode file. Please use UTF-8 encoded CSV."))

        reader = csv.DictReader(io.StringIO(content))
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]

        # Map common header variations
        date_fields = ['date', 'transaction date', 'value date', 'txn date']
        label_fields = ['description', 'label', 'narration', 'particulars', 'remarks', 'details']
        amount_fields = ['amount', 'debit/credit', 'txn amount', 'transaction amount']
        debit_fields = ['debit', 'withdrawal', 'withdrawals', 'dr']
        credit_fields = ['credit', 'deposit', 'deposits', 'cr']

        def find_col(options):
            for opt in options:
                if opt in headers:
                    return opt
            return None

        date_col = find_col(date_fields)
        label_col = find_col(label_fields)
        amount_col = find_col(amount_fields)
        debit_col = find_col(debit_fields)
        credit_col = find_col(credit_fields)

        if not date_col:
            raise UserError(_("Could not find a 'Date' column. Expected: %s") % ', '.join(date_fields))
        if not label_col:
            raise UserError(_("Could not find a 'Description' column. Expected: %s") % ', '.join(label_fields))
        if not amount_col and not (debit_col or credit_col):
            raise UserError(_("Could not find an 'Amount' column. Expected: %s") % ', '.join(amount_fields))

        transactions = []
        # Re-read so we get original cased keys
        reader = csv.DictReader(io.StringIO(content))
        normalized = {h.strip().lower(): h.strip() for h in (reader.fieldnames or [])}

        def get_cell(row, col):
            if col and normalized.get(col):
                return (row.get(normalized[col]) or '').strip()
            return ''

        for i, row in enumerate(reader, start=2):
            date_str = get_cell(row, date_col)
            label = get_cell(row, label_col)

            if not date_str and not label:
                continue  # skip blank rows

            # Parse date
            parsed_date = None
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%m/%d/%Y', '%d.%m.%Y']:
                try:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
            if not parsed_date:
                raise UserError(_("Row %d: Cannot parse date '%s'. Use DD/MM/YYYY or YYYY-MM-DD.") % (i, date_str))

            # Parse amount
            def clean_amount(s):
                s = s.replace(',', '').replace('\xa0', '').strip()
                if s in ('', '-', 'N/A'):
                    return 0.0
                try:
                    return float(s)
                except ValueError:
                    return 0.0

            if amount_col:
                amount = clean_amount(get_cell(row, amount_col))
            else:
                debit = clean_amount(get_cell(row, debit_col))
                credit = clean_amount(get_cell(row, credit_col))
                # Debit = money out (negative), Credit = money in (positive)
                amount = credit - debit

            transactions.append({
                'date': parsed_date,
                'payment_ref': label,
                'amount': amount,
            })

        if not transactions:
            raise UserError(_("No valid transactions found in the file."))

        return transactions

    def action_import(self):
        self.ensure_one()
        transactions = self._parse_csv_file(self.import_file)

        lines_to_create = [
            {
                'journal_id': self.journal_id.id,
                'date': t['date'],
                'payment_ref': t['payment_ref'],
                'amount': t['amount'],
            }
            for t in transactions
        ]

        created = self.env['account.bank.statement.line'].create(lines_to_create)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Imported Transactions'),
            'res_model': 'account.bank.statement.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
            'context': {'create': False},
            'target': 'current',
        }
