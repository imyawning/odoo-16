# 資產出售作業
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ji Twins Studio
# License: Commercial License - see LICENSE file for details.

from odoo import models, fields, api

class AssetSale(models.Model):
    _name = 'asset.sale'
    _description = '資產出售單'

    name = fields.Char('出售單號', required=True, copy=False, default='New')
    date = fields.Date('出售日期', required=True, default=fields.Date.context_today)
    buyer_id = fields.Many2one('res.partner', string='買方')
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirm', '已確認')
    ], string='狀態', default='draft', required=True)
    line_ids = fields.One2many('asset.sale.line', 'sale_id', string='出售明細')
    total_amount = fields.Float('出售總額', compute='_compute_total_amount', store=True)
    notes = fields.Text('備註')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.sale') or 'New'
        return super().create(vals)

    @api.depends('line_ids.sale_amount')
    def _compute_total_amount(self):
        for sale in self:
            sale.total_amount = sum(sale.line_ids.mapped('sale_amount'))

    # 新增 action_confirm 方法
    def action_confirm(self):
        """確認出售單，將狀態改為 'confirm'"""
        for rec in self:
            # TODO: 這裡應加入會計傳票創建與資產主檔數據更新的邏輯
            rec.state = 'confirm'

    # 新增 action_draft 方法
    def action_draft(self):
        """還原草稿，將狀態從 'confirm' 改回 'draft'"""
        for rec in self:
            if rec.state == 'confirm':
                # TODO: 如果有產生傳票，這裡需要執行傳票取消或刪除
                rec.state = 'draft'


class AssetSaleLine(models.Model):
    _name = 'asset.sale.line'
    _description = '資產出售明細'

    sale_id = fields.Many2one('asset.sale', string='出售單', required=True, ondelete='cascade')
    asset_id = fields.Many2one('asset.master', string='財產編號')
    name = fields.Char('資產名稱')
    original_amount = fields.Float('原始金額')
    accumulated_depreciation = fields.Float('累計折舊')
    book_value = fields.Float('帳面價值')
    sale_amount = fields.Float('出售金額')
    gain_loss = fields.Float('處分損益', compute='_compute_gain_loss', store=True)

    @api.depends('book_value', 'sale_amount')
    def _compute_gain_loss(self):
        for line in self:
            line.gain_loss = line.sale_amount - line.book_value