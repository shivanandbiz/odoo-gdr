from odoo import models, fields

class MrpMps(models.Model):
    _name = "mrp.mps"
    _description = "Master Production Schedule"

    product_id = fields.Many2one("product.product", required=True)
    date = fields.Date("Date", default=fields.Date.context_today)
    forecast_qty = fields.Float("Forecasted Qty")
    actual_qty = fields.Float("Actual Qty")
