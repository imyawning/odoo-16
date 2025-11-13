# 固定資產類別
# -*- coding: utf-8 -*-
from odoo import models, fields

class AssetCategory(models.Model):
    _name = 'asset.category'
    _description = 'Asset Category'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code')
    depreciation_method = fields.Selection([
        ('0_no_depreciation', '0.不提折舊'),
        ('1_straight_line', '1.平均年限法-無殘值'),
        ('2_straight_line_residual', '2.平均年限法-有殘值'),
    ], string='折舊方法')
    depreciation_months = fields.Integer(string='耐用年限(月)')
    is_redepreciation = fields.Boolean('折畢再提', default=False)
    redepreciation_months = fields.Integer('折畢再提月數')
    asset_account_id = fields.Many2one('account.account', string='資產科目')
    asset_account_acc_id = fields.Many2one('account.account', string='累折科目')
    asset_account_dep_id = fields.Many2one('account.account', string='折舊科目')
    
    def some_function(self):
        """範例函數 - 如果需要引用 asset.master，在函數內部導入"""
        # 如果需要的話，可以在這裡導入
        # asset_master = self.env['asset.master']
        # return asset_master.search([...])
        pass