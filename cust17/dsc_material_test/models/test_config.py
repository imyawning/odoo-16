# -*- coding: utf-8 -*-
from odoo import models, fields, api

class MaterialTestItem(models.Model):
    _name = 'dsc.material.test.item'
    _description = 'Material Test Item Configuration'
    _order = 'sequence, id'

    name = fields.Char(string='測試項目', required=True, translate=True)
    sequence = fields.Integer(string='排序', default=10)

    allowed_unit_ids = fields.Many2many(
        'uom.uom',
        string='單位'
    )

class MaterialTestConfigLine(models.Model):
    _name = 'dsc.material.test.config.line'
    _description = 'Material Test Standard Configuration Line'
    _order = 'sequence, id'
    _rec_name = 'name'

    config_id = fields.Many2one('dsc.material.test.config', string='品牌', ondelete='cascade')

    product_categ_id = fields.Many2one('product.category', string='產品類別')

    name = fields.Char(string='說明', compute='_compute_name', store=True, required=False)

    sequence = fields.Integer(string='Sequence', default=10)
    test_item_id = fields.Many2one('dsc.material.test.item', string='測試項目', required=True)
    unit = fields.Many2one('uom.uom', string='單位', required=True)
    spec = fields.Char(string='規格標準', required=True)

    @api.depends('config_id')
    def _compute_name(self):
        for line in self:
            # 自動將方法/品牌名稱填入 name 欄位，避免空值錯誤
            if line.config_id:
                line.name = line.config_id.name
            else:
                line.name = line.name or '/'

    @api.onchange('test_item_id')
    def _onchange_test_item_filter_unit(self):
        if not self.test_item_id:
            return {'domain': {'unit': []}}

        allowed_units = self.test_item_id.allowed_unit_ids
        allowed_ids = allowed_units.ids

        domain_unit = []
        if allowed_ids:
            domain_unit = [('id', 'in', allowed_ids)]
            if self.unit and self.unit.id not in allowed_ids:
                self.unit = False
            if not self.unit and len(allowed_units) == 1:
                self.unit = allowed_units[0]

        return {'domain': {'unit': domain_unit}}


class MaterialTestConfig(models.Model):
    _name = 'dsc.material.test.config'
    _description = 'Material Test Standard Configuration'

    name = fields.Char(string='品牌', required=True)

    config_line_ids = fields.One2many('dsc.material.test.config.line', 'config_id', string='品牌標準設定')

    _sql_constraints = [('name_unique', 'unique (name)', '該品牌標準已存在!')]

class MaterialTestFactoryType(models.Model):
    _name = 'dsc.material.test.factory.type'
    _description = 'Factory Type Configuration'
    _rec_names_search = ['name', 'code']

    code = fields.Char(string='代號', required=True)
    name = fields.Char(string='廠別名稱', required=True)

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            if record.code and record.name:
                record.display_name = f"{record.code} {record.name}"
            else:
                record.display_name = record.name