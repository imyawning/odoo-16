# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MaterialTestReport(models.Model):
    _name = 'dsc.material.test.report'
    _description = 'DSC Material Test Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_tested desc'

    name = fields.Char(string='Report No.', required=True, copy=False,
                       readonly=True, default='New')

    # Basic Information
    factory = fields.Char(string='FACTORY(廠商)', required=True,
                          default='Active Creation')

    is_production = fields.Boolean(string='PRODUCTION MATERIAL(量產材料)', default=False)

    material_description = fields.Selection([
        ('production', 'Production Material'),
        ('development', 'Development/New')
    ], string='MATERIAL DESCRIPTION(材料名稱)', required=True, default='production')

    color = fields.Char(string='COLOR(顏色)', required=True)
    po_number = fields.Char(string='P.O.#/QUANTITY(訂單號碼/數量)')
    is_development = fields.Boolean(string='DEVELOPMENT/NEW (開發/新產品)', default=False)
    date_tested = fields.Date(string='DATE TESTED(測試日期)', required=True,
                              default=fields.Date.today)
    tester = fields.Char(string='TESTER(測試員)', required=True)

    # Test Results
    # Hardness
    hardness_asker_c = fields.Float(string='Hardness ASKER-C')
    hardness_shore_000 = fields.Float(string='Hardness Shore 000')
    hardness_asker_f = fields.Float(string='Hardness ASKER-F')
    hardness_average = fields.Float(string='Hardness Average',
                                    compute='_compute_hardness_average',
                                    store=True)
    hardness_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Hardness Result')
    hardness_spec = fields.Char(string='Hardness Spec')

    # Tensile Strength
    tensile_strength_1 = fields.Float(string='Tensile Strength 1')
    tensile_strength_2 = fields.Float(string='Tensile Strength 2')
    tensile_strength_3 = fields.Float(string='Tensile Strength 3')
    tensile_strength_average = fields.Float(string='Tensile Strength Average',
                                            compute='_compute_tensile_average',
                                            store=True)
    tensile_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Tensile Result')
    tensile_spec = fields.Char(string='Tensile Spec')

    # Elongation Ratio
    elongation_1 = fields.Float(string='Elongation 1')
    elongation_2 = fields.Float(string='Elongation 2')
    elongation_3 = fields.Float(string='Elongation 3')
    elongation_average = fields.Float(string='Elongation Average',
                                      compute='_compute_elongation_average',
                                      store=True)
    elongation_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Elongation Result')
    elongation_spec = fields.Char(string='Elongation Spec')

    # Tear Strength
    tear_strength_1 = fields.Float(string='Tear Strength 1')
    tear_strength_2 = fields.Float(string='Tear Strength 2')
    tear_strength_3 = fields.Float(string='Tear Strength 3')
    tear_strength_average = fields.Float(string='Tear Strength Average',
                                         compute='_compute_tear_average',
                                         store=True)
    tear_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Tear Result')
    tear_spec = fields.Char(string='Tear Spec')

    # Resiliency
    resiliency_1 = fields.Float(string='Resiliency 1')
    resiliency_2 = fields.Float(string='Resiliency 2')
    resiliency_3 = fields.Float(string='Resiliency 3')
    resiliency_average = fields.Float(string='Resiliency Average',
                                      compute='_compute_resiliency_average',
                                      store=True)
    resiliency_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Resiliency Result')
    resiliency_spec = fields.Char(string='Resiliency Spec')

    # Specific Gravity
    specific_gravity_1 = fields.Float(string='Specific Gravity 1')
    specific_gravity_2 = fields.Float(string='Specific Gravity 2')
    specific_gravity_3 = fields.Float(string='Specific Gravity 3')
    specific_gravity_average = fields.Float(string='Specific Gravity Average',
                                            compute='_compute_gravity_average',
                                            store=True)
    specific_gravity_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Specific Gravity Result')
    specific_gravity_spec = fields.Char(string='Specific Gravity Spec')

    # Shrinkage
    shrinkage_1 = fields.Float(string='Shrinkage 1')
    shrinkage_2 = fields.Float(string='Shrinkage 2')
    shrinkage_3 = fields.Float(string='Shrinkage 3')
    shrinkage_average = fields.Float(string='Shrinkage Average',
                                     compute='_compute_shrinkage_average',
                                     store=True)
    shrinkage_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Shrinkage Result')
    shrinkage_spec = fields.Char(string='Shrinkage Spec')

    # Compression Set
    compression_set_1 = fields.Float(string='Compression Set 1')
    compression_set_2 = fields.Float(string='Compression Set 2')
    compression_set_3 = fields.Float(string='Compression Set 3')
    compression_set_average = fields.Float(string='Compression Set Average',
                                           compute='_compute_compression_average',
                                           store=True)
    compression_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Compression Result')
    compression_spec = fields.Char(string='Compression Spec')

    # Split Tear
    split_tear_1 = fields.Float(string='Split Tear 1')
    split_tear_2 = fields.Float(string='Split Tear 2')
    split_tear_3 = fields.Float(string='Split Tear 3')
    split_tear_average = fields.Float(string='Split Tear Average',
                                      compute='_compute_split_tear_average',
                                      store=True)
    split_tear_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail')
    ], string='Split Tear Result')
    split_tear_spec = fields.Char(string='Split Tear Spec')

    # Comments and Approvals
    comments = fields.Text(string='Comments')
    reviewer = fields.Char(string='Reviewer')
    production_manager = fields.Char(string='Production Manager')
    quality_control = fields.Char(string='Quality Control', default='THẢO')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('dsc.material.test.report') or 'New'
        return super(MaterialTestReport, self).create(vals)

    @api.depends('hardness_asker_c', 'hardness_shore_000', 'hardness_asker_f')
    def _compute_hardness_average(self):
        for record in self:
            values = [record.hardness_asker_c, record.hardness_shore_000,
                      record.hardness_asker_f]
            non_zero_values = [v for v in values if v]
            record.hardness_average = sum(non_zero_values) / len(non_zero_values) if non_zero_values else 0

    @api.depends('tensile_strength_1', 'tensile_strength_2', 'tensile_strength_3')
    def _compute_tensile_average(self):
        for record in self:
            values = [record.tensile_strength_1, record.tensile_strength_2,
                      record.tensile_strength_3]
            non_zero_values = [v for v in values if v]
            record.tensile_strength_average = sum(non_zero_values) / len(non_zero_values) if non_zero_values else 0

    @api.depends('elongation_1', 'elongation_2', 'elongation_3')
    def _compute_elongation_average(self):
        for record in self:
            values = [record.elongation_1, record.elongation_2, record.elongation_3]
            non_zero_values = [v for v in values if v]
            record.elongation_average = sum(non_zero_values) / len(non_zero_values) if non_zero_values else 0

    @api.depends('tear_strength_1', 'tear_strength_2', 'tear_strength_3')
    def _compute_tear_average(self):
        for record in self:
            values = [record.tear_strength_1, record.tear_strength_2,
                      record.tear_strength_3]
            non_zero_values = [v for v in values if v]
            record.tear_strength_average = sum(non_zero_values) / len(non_zero_values) if non_zero_values else 0

    @api.depends('resiliency_1', 'resiliency_2', 'resiliency_3')
    def _compute_resiliency_average(self):
        for record in self:
            values = [record.resiliency_1, record.resiliency_2, record.resiliency_3]
            non_zero_values = [v for v in values if v]
            record.resiliency_average = sum(non_zero_values) / len(non_zero_values) if non_zero_values else 0

    @api.depends('specific_gravity_1', 'specific_gravity_2', 'specific_gravity_3')
    def _compute_gravity_average(self):
        for record in self:
            values = [record.specific_gravity_1, record.specific_gravity_2,
                      record.specific_gravity_3]
            non_zero_values = [v for v in values if v]
            record.specific_gravity_average = sum(non_zero_values) / len(non_zero_values) if non_zero_values else 0

    @api.depends('shrinkage_1', 'shrinkage_2', 'shrinkage_3')
    def _compute_shrinkage_average(self):
        for record in self:
            values = [record.shrinkage_1, record.shrinkage_2, record.shrinkage_3]
            non_zero_values = [v for v in values if v]
            record.shrinkage_average = sum(non_zero_values) / len(non_zero_values) if non_zero_values else 0

    @api.depends('compression_set_1', 'compression_set_2', 'compression_set_3')
    def _compute_compression_average(self):
        for record in self:
            values = [record.compression_set_1, record.compression_set_2,
                      record.compression_set_3]
            non_zero_values = [v for v in values if v]
            record.compression_set_average = sum(non_zero_values) / len(non_zero_values) if non_zero_values else 0

    @api.depends('split_tear_1', 'split_tear_2', 'split_tear_3')
    def _compute_split_tear_average(self):
        for record in self:
            values = [record.split_tear_1, record.split_tear_2, record.split_tear_3]
            non_zero_values = [v for v in values if v]
            record.split_tear_average = sum(non_zero_values) / len(non_zero_values) if non_zero_values else 0

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        self.message_post(body="Test report confirmed.")

    def action_approve(self):
        self.write({'state': 'approved'})
        self.message_post(body="Test report approved.")

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self.message_post(body="Test report cancelled.")

    def action_draft(self):
        self.write({'state': 'draft'})
        self.message_post(body="Test report set back to draft.")