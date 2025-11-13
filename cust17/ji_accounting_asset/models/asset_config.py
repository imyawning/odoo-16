# 固定資產設定
# -*- coding: utf-8 -*-
from odoo import models, fields

class AssetConfig(models.Model):
    _name = 'asset.config'
    _description = 'Asset Config'

    name = fields.Char('名稱', required=True)
    asset_close_date = fields.Date('關帳日期')
    loss_account_id = fields.Many2one('account.account', string='資產處分損失科目')
    asset_journal_id = fields.Many2one('account.journal', string='預設帳別')
    depreciate_in_disposal = fields.Boolean('報廢前需提列折舊', default=False)
    depreciation_start_type = fields.Selection([
        ('current_month', '當月月底'),
        ('next_month', '次月月底'),
    ], string='開始折舊時點', default='next_month')
    asset_code_method = fields.Selection([
        ('sequence', '流水號'),
        ('category', '類別+流水號'),
    ], string='資產編碼方式', default='sequence')
    asset_code_padding = fields.Integer('資產編碼長度', default=4)