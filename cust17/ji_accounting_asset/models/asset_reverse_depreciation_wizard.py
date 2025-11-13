# 批次還原折舊
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ji Twins Studio
# License: Commercial License - see LICENSE file for details.

from odoo import models, fields, api
from odoo.exceptions import UserError

class AssetReverseDepreciationWizard(models.TransientModel):
    _name = 'asset.reverse.depreciation.wizard'
    _description = '批次還原折舊精靈'

    depreciation_date = fields.Date('折舊日期', required=True, default=fields.Date.context_today)
    category_ids = fields.Many2many('asset.category', string='資產類別')
    
    def action_reverse(self):
        """執行批次還原折舊"""
        self.ensure_one()
        
        # 建立查詢條件
        domain = [
            ('date', '=', self.depreciation_date),
            ('state', '=', 'posted'),
        ]
        
        if self.category_ids:
            domain.append(('category_id', 'in', self.category_ids.ids))
        
        # 查詢符合條件的折舊記錄
        depreciations = self.env['asset.depreciation'].search(domain)
        
        if not depreciations:
            raise UserError('沒有找到符合條件的折舊記錄！')
        
        # 執行還原
        reversed_count = 0
        for depreciation in depreciations:
            depreciation.action_reverse()
            reversed_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '成功',
                'message': f'已還原 {reversed_count} 筆折舊記錄',
                'type': 'success',
                'sticky': False,
            }
        }