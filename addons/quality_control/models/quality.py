from odoo import models, fields

class QualityPoint(models.Model):
    _name = "quality.point"
    _description = "Quality Point"
    name = fields.Char("Reference", required=True)
    product_id = fields.Many2one("product.product", "Product")

class QualityCheck(models.Model):
    _name = "quality.check"
    _description = "Quality Check"
    name = fields.Char("Reference")
    product_id = fields.Many2one("product.product", "Product")
    workorder_id = fields.Many2one("mrp.workorder", "Work Order")
    state = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')], "Status")
