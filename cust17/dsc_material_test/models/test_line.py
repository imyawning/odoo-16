# -*- coding: utf-8 -*-
from odoo import models, fields, api


class UnifiedTestLine(models.Model):
    _name = 'dsc.material.test.unified'
    _description = 'Unified Material Test Line'
    _order = 'sequence, id'

    report_id = fields.Many2one('dsc.material.test.report', string='Report', ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    test_item_id = fields.Many2one('dsc.material.test.item', string='測試項目', required=True)
    is_hardness = fields.Boolean(string="是否為硬度", compute='_compute_is_hardness')

    @api.depends('test_item_id')
    def _compute_is_hardness(self):
        for line in self:
            name = line.test_item_id.name or ''

            if '硬度' in name:
                line.is_hardness = True
            else:
                line.is_hardness = False

    method = fields.Many2one('dsc.material.test.config', string='Method 方法')
    unit = fields.Many2one('uom.uom', string='單位')
    spec = fields.Char(string='規格標準')

    test_1 = fields.Char(string='測試1', default='0')
    test_2 = fields.Char(string='測試2', default='0')
    test_3 = fields.Char(string='測試3', default='0')
    test_4 = fields.Char(string='測試4', default='0')
    test_5 = fields.Char(string='測試5', default='0')

    test_result = fields.Char(string='測試結果', compute='_compute_test_result_string', store=True)

    average = fields.Char(string='平均值', compute='_compute_test_evaluation', store=True, default='0')

    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Pass/Fail 判定', compute='_compute_test_evaluation', store=True)

    @api.depends('test_1', 'test_2', 'test_3', 'test_4', 'test_5')
    def _compute_test_result_string(self):
        for line in self:
            raw_values = [line.test_1, line.test_2, line.test_3, line.test_4, line.test_5]
            valid_values = []
            for v in raw_values:
                if v and v.strip() != '0':
                    valid_values.append(v.strip())

            line.test_result = ", ".join(valid_values)

    # --- 自動計算平均值與判定 ---
    @api.depends('test_1', 'test_2', 'test_3', 'test_4', 'test_5', 'spec')
    def _compute_test_evaluation(self):
        for line in self:
            line.average = '0'
            line.result = False
            avg_val = 0.0

            raw_values = [line.test_1, line.test_2, line.test_3, line.test_4, line.test_5]
            valid_floats = []

            for v in raw_values:
                if v and v.strip() != '0':
                    try:
                        val = float(v)
                        if val != 0.0:
                            valid_floats.append(val)
                    except ValueError:
                        continue

            # 3. 計算平均
            if valid_floats:
                avg_val = sum(valid_floats) / len(valid_floats)

                line.average = '{:g}'.format(avg_val)

                is_pass = False
                if line.spec:
                    try:
                        spec = line.spec.replace(' ', '').upper()
                        if '~' in spec:
                            parts = spec.split('~')
                            if len(parts) == 2:
                                is_pass = float(parts[0]) <= avg_val <= float(parts[1])
                        elif spec.startswith('>='):
                            is_pass = avg_val >= float(spec[2:])
                        elif spec.startswith('>'):
                            is_pass = avg_val > float(spec[1:])
                        elif spec.startswith('<='):
                            is_pass = avg_val <= float(spec[2:])
                        elif spec.startswith('<'):
                            is_pass = avg_val < float(spec[1:])
                        else:
                            is_pass = avg_val >= float(spec)
                    except Exception:
                        is_pass = False

                line.result = 'pass' if is_pass else 'fail'
            else:
                line.average = '0'
                line.result = False

    @api.onchange('test_item_id')
    def _onchange_test_item_updates(self):
        if not self.test_item_id:
            return {'domain': {'unit': [], 'method': []}}

        allowed_units = self.test_item_id.allowed_unit_ids
        allowed_unit_ids = allowed_units.ids
        domain_unit = []

        if allowed_unit_ids:
            domain_unit = [('id', 'in', allowed_unit_ids)]
            if self.unit and self.unit.id not in allowed_unit_ids:
                self.unit = False
            if not self.unit and len(allowed_units) == 1:
                self.unit = allowed_units[0]

        product_categ = False
        if self.report_id and self.report_id.product_id:
            product_categ = self.report_id.product_id.categ_id

        if product_categ:
            config_line = self.env['dsc.material.test.config.line'].search([
                ('test_item_id', '=', self.test_item_id.id),
                ('product_categ_id', '=', product_categ.id)
            ], limit=1)

            if config_line:
                self.method = config_line.config_id
                if config_line.unit:
                    self.unit = config_line.unit
                self.spec = config_line.spec

        valid_config_lines = self.env['dsc.material.test.config.line'].search([
            ('test_item_id', '=', self.test_item_id.id)
        ])
        valid_method_ids = valid_config_lines.mapped('config_id').ids

        if self.method and self.method.id not in valid_method_ids:
            self.method = False

        return {'domain': {
            'unit': domain_unit,
            'method': [('id', 'in', valid_method_ids)]
        }}

    @api.onchange('method', 'test_item_id', 'unit')
    def _onchange_method_apply_config(self):
        if not self.method or not self.test_item_id:
            return

        domain = [
            ('config_id', '=', self.method.id),
            ('test_item_id', '=', self.test_item_id.id)
        ]
        if self.unit:
            domain.append(('unit', '=', self.unit.id))

        config_line = self.env['dsc.material.test.config.line'].search(domain, limit=1)

        if config_line:
            self.spec = config_line.spec
            if not self.unit:
                self.unit = config_line.unit
        else:
            if self.unit:
                self.spec = False

    def _update_standard_config(self):
        ConfigLine = self.env['dsc.material.test.config.line']
        for line in self:
            if line.method and line.test_item_id and line.unit and line.spec:
                existing_config = ConfigLine.search([
                    ('config_id', '=', line.method.id),
                    ('test_item_id', '=', line.test_item_id.id)
                ], limit=1)

                if not existing_config:
                    ConfigLine.create({
                        'config_id': line.method.id,
                        'test_item_id': line.test_item_id.id,
                        'unit': line.unit.id,
                        'spec': line.spec,
                    })

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(UnifiedTestLine, self).create(vals_list)
        lines._update_standard_config()
        return lines

    def write(self, vals):
        res = super(UnifiedTestLine, self).write(vals)
        self._update_standard_config()
        return res