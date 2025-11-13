# 資產調整作業
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ji Twins Studio
# License: Commercial License - see LICENSE file for details.

from odoo import models, fields, api

class AssetAdjust(models.Model):
    _name = 'asset.adjust'
    _description = '資產調整單'

    name = fields.Char('調整單號', required=True, copy=False, default='New')
    date = fields.Date('調整日期', required=True, default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirm', '已確認')
    ], string='狀態', default='draft', required=True)
    line_ids = fields.One2many('asset.adjust.line', 'adjust_id', string='調整明細')
    notes = fields.Text('備註')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.adjust') or 'New'
        return super().create(vals)

    # *** 新增流程方法以供 XML 視圖使用 ***
    def action_confirm(self):
        """確認調整單，將狀態改為 'confirm'"""
        for rec in self:
            rec.state = 'confirm'
            # TODO: 這裡應加入會計傳票創建與資產主檔數據更新的邏輯

    def action_draft(self):
        """還原草稿，將狀態從 'confirm' 改回 'draft'"""
        for rec in self:
            if rec.state == 'confirm':
                # TODO: 如果有產生傳票，這裡需要執行傳票取消或刪除
                rec.state = 'draft'
    # ****************************************


class AssetAdjustLine(models.Model):
    _name = 'asset.adjust.line'
    _description = '資產調整明細'

    adjust_id = fields.Many2one('asset.adjust', string='調整單', required=True, ondelete='cascade')
    asset_id = fields.Many2one('asset.master', string='財產編號')
    name = fields.Char('說明')
    old_value = fields.Float('原值')
    new_value = fields.Float('新值')
    difference = fields.Float('差額', compute='_compute_difference', store=True)

    @api.depends('old_value', 'new_value')
    def _compute_difference(self):
        for line in self:
            line.difference = line.new_value - line.old_value