# 折舊作業明細
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ji Twins Studio
# License: Commercial License - see LICENSE file for details.

from odoo import models, fields, api

class AssetDepreciation(models.Model):
    _name = 'asset.depreciation'
    _description = '資產折舊明細'
    _order = 'date desc, asset_id'

    name = fields.Char('折舊單號', required=True, copy=False, default='New', index=True)
    date = fields.Date('折舊日期', required=True, default=fields.Date.context_today, index=True)
    asset_id = fields.Many2one('asset.master', string='財產編號', required=True, ondelete='restrict', index=True)
    asset_name = fields.Char('資產名稱', related='asset_id.name', store=True)
    category_id = fields.Many2one('asset.category', string='資產類別', related='asset_id.category_id', store=True)
    
    # 折舊相關欄位
    depreciation_amount = fields.Float('本期折舊', required=True)
    accumulated_depreciation = fields.Float('累計折舊')
    ytd_depreciation = fields.Float('本年累計折舊')
    value = fields.Float('帳面價值')
    remaining_months = fields.Integer('剩餘月數')
    
    # 狀態與傳票
    state = fields.Selection([
        ('draft', '草稿'),
        ('posted', '已過帳'),
        ('reversed', '已沖銷')
    ], string='狀態', default='draft', required=True, index=True)
    move_id = fields.Many2one('account.move', string='會計傳票', readonly=True)
    
    # 科目資訊
    debit_account_id = fields.Many2one('account.account', string='折舊費用科目')
    credit_account_id = fields.Many2one('account.account', string='累計折舊科目')
    
    notes = fields.Text('備註')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.depreciation') or 'New'
        return super().create(vals)

    def action_post(self):
        """過帳折舊"""
        for record in self:
            if record.state != 'draft':
                continue
            # 這裡會建立會計傳票
            # 實際實作時需要根據業務邏輯建立 account.move
            record.state = 'posted'

    def action_reverse(self):
        """沖銷折舊"""
        for record in self:
            if record.state != 'posted':
                continue
            # 這裡會沖銷會計傳票
            record.state = 'reversed'