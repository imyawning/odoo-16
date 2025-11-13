# 批次產生折舊
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ji Twins Studio
# License: Commercial License - see LICENSE file for details.

from odoo import models, fields, api
from odoo.exceptions import UserError

class AssetExeDepreciationWizard(models.TransientModel):
    _name = 'asset.exe.depreciation.wizard'
    _description = '批次產生折舊精靈'

    depreciation_date = fields.Date('折舊日期', required=True, default=fields.Date.context_today)
    category_ids = fields.Many2many('asset.category', string='資產類別')
    asset_ids = fields.Many2many('asset.master', string='指定資產')
    
    def action_execute(self):
        """執行批次折舊"""
        self.ensure_one()
        
        # 建立查詢條件
        domain = [
            ('state', 'in', ['confirm', 'depreciation']),
            ('depreciation_method', '!=', '0_no_depreciation'),
        ]
        
        if self.category_ids:
            domain.append(('category_id', 'in', self.category_ids.ids))
        
        if self.asset_ids:
            domain.append(('id', 'in', self.asset_ids.ids))
        
        # 查詢符合條件的資產
        assets = self.env['asset.master'].search(domain)
        
        if not assets:
            raise UserError('沒有找到符合條件的資產！')
        
        # 這裡實作批次產生折舊的邏輯
        # 實際使用時需要根據業務規則計算每個資產的折舊
        created_count = 0
        for asset in assets:
            # 檢查是否已有該月份的折舊記錄
            # 計算折舊金額
            # 建立折舊記錄
            depreciation_amount = asset.amount / asset.depreciation_months  # 假設最簡單的平均折舊計算
            
            self.env['asset.depreciation'].create({
                'date': self.depreciation_date,
                'asset_id': asset.id,
                'depreciation_amount': depreciation_amount,
                # 其他欄位如 accumulated_depreciation, value, remaining_months 
                # 需在 asset.depreciation 模型中實作計算邏輯
            })
            created_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '成功',
                'message': f'已產生 {created_count} 筆折舊記錄',
                'type': 'success',
                'sticky': False,
            }
        }