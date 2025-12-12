# -*- coding: utf-8 -*-
from odoo import models, fields, api

class MaterialTestTemplate(models.Model):
    _name = 'dsc.material.test.template'
    _description = 'Material Test Template'

    name = fields.Char(string='樣板名稱', required=True)

    product_categ_id = fields.Many2one('product.category', string='產品類別')

    is_production = fields.Boolean(string="量產材料")
    is_development = fields.Boolean(string="開發/新產品")
    line_ids = fields.One2many('dsc.material.test.template.line', 'template_id', string='樣板細項')


class MaterialTestTemplateLine(models.Model):
    _name = 'dsc.material.test.template.line'
    _description = 'Material Test Template Line'
    _order = 'sequence, id'

    template_id = fields.Many2one('dsc.material.test.template', string='樣板', ondelete='cascade')
    sequence = fields.Integer(string='排序', default=10)

    test_item_id = fields.Many2one('dsc.material.test.item', string='測試項目', required=True)
    method_id = fields.Many2one('dsc.material.test.config', string='方法')
    unit_id = fields.Many2one('uom.uom', string='單位')
    spec = fields.Char(string='規格標準')

    @api.onchange('test_item_id')
    def _onchange_test_item_updates(self):
        if not self.test_item_id:
            return {'domain': {'unit_id': [], 'method_id': []}}

        allowed_units = self.test_item_id.allowed_unit_ids
        allowed_ids = allowed_units.ids

        domain_unit = []
        if allowed_ids:
            domain_unit = [('id', 'in', allowed_ids)]
            if self.unit_id and self.unit_id.id not in allowed_ids:
                self.unit_id = False
            if not self.unit_id and len(allowed_units) == 1:
                self.unit_id = allowed_units[0]

        product_categ = self.template_id.product_categ_id
        if product_categ:
            config_line = self.env['dsc.material.test.config.line'].search([
                ('test_item_id', '=', self.test_item_id.id),
                ('product_categ_id', '=', product_categ.id)
            ], limit=1)

            if config_line:
                self.method_id = config_line.config_id
                if config_line.unit:
                    self.unit_id = config_line.unit
                self.spec = config_line.spec

        valid_config_lines = self.env['dsc.material.test.config.line'].search([
            ('test_item_id', '=', self.test_item_id.id)
        ])
        valid_method_ids = valid_config_lines.mapped('config_id').ids

        if self.method_id and self.method_id.id not in valid_method_ids:
            self.method_id = False

        return {'domain': {
            'unit_id': domain_unit,
            'method_id': [('id', 'in', valid_method_ids)]
        }}

    @api.onchange('method_id', 'test_item_id', 'unit_id')
    def _onchange_method_apply_config(self):
        if not self.method_id or not self.test_item_id:
            return

        domain = [
            ('config_id', '=', self.method_id.id),
            ('test_item_id', '=', self.test_item_id.id)
        ]
        if self.unit_id:
            domain.append(('unit', '=', self.unit_id.id))

        config_line = self.env['dsc.material.test.config.line'].search(domain, limit=1)

        if config_line:
            self.spec = config_line.spec
            if not self.unit_id:
                self.unit_id = config_line.unit
        else:
            if self.unit_id:
                self.spec = False