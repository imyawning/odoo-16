# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MaterialTestReport(models.Model):
    _name = 'dsc.material.test.report'
    _description = 'Material Test Report'
    _inherit = ['mail.thread']

    name = fields.Char(string="報告編號", required=True, copy=False, readonly=True, default='New')
    date_tested = fields.Date(string="測試日期")
    template_id = fields.Many2one('dsc.material.test.template', string='樣板')

    product_id = fields.Many2one('product.product', string="材料名稱", required=True)

    factory_type_id = fields.Many2one('dsc.material.test.factory.type', string="廠別")

    factory_id = fields.Many2one('res.partner', string="廠商", domain="[('is_company', '=', True)]")

    material_description = fields.Char(string="材料描述")
    color = fields.Char(string="顏色")
    po_number = fields.Char(string="訂單號碼")

    def _default_tester(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)

    tester_id = fields.Many2one('hr.employee', string="測試員", default=_default_tester)

    is_production = fields.Boolean(string="量產材料")
    is_development = fields.Boolean(string="開發/新產品")
    comments = fields.Text(string="備註")
    state = fields.Selection(
        [('draft', '草稿'),
         ('confirmed', '已確認'),
         ('cancelled', '已取消')],
        default='draft', tracking=True)

    test_line_ids = fields.One2many('dsc.material.test.unified', 'report_id', string='測試細項')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.template_id = False
        if not self.product_id:
            return

        product_categ = self.product_id.categ_id

        if product_categ:
            template = self.env['dsc.material.test.template'].search([
                ('product_categ_id', '=', product_categ.id)
            ], limit=1)

            if template:
                self.template_id = template.id

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if not self.template_id:
            return

        self.is_production = self.template_id.is_production
        self.is_development = self.template_id.is_development

        new_lines = []
        for line in self.template_id.line_ids:
            new_lines.append((0, 0, {
                'sequence': line.sequence,
                'test_item_id': line.test_item_id.id,
                'method': line.method_id.id,
                'unit': line.unit_id.id,
                'spec': line.spec,
            }))

        self.test_line_ids = [(5, 0, 0)] + new_lines

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('dsc.material.test.report') or 'New'
        return super(MaterialTestReport, self).create(vals_list)

    def action_confirm(self):
        self.state = 'confirmed'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_draft(self):
        self.state = 'draft'

    def action_print_report(self):
        # 這裡使用 Python 程式碼來呼叫報表，避開 XML 解析錯誤
        return self.env.ref('dsc_material_test.report_material_test').report_action(self)
