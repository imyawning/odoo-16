# 折舊明細表查詢
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ji Twins Studio
# License: Commercial License - see LICENSE file for details.

from odoo import models, fields, api
from odoo.exceptions import UserError

class AssetDepreciationReportWizard(models.TransientModel):
    """折舊明細表查詢精靈"""
    _name = 'asset.depreciation.report.wizard'
    _description = '折舊明細表查詢精靈'

    date_from = fields.Date('開始日期', required=True, default=fields.Date.context_today)
    date_to = fields.Date('結束日期', required=True, default=fields.Date.context_today)
    category_ids = fields.Many2many('asset.category', string='資產類別')
    asset_ids = fields.Many2many('asset.master', string='財產編號')
    department_ids = fields.Many2many('account.analytic.account', string='保管部門')
    state = fields.Selection([
        ('all', '全部'),
        ('posted', '已過帳'),
        ('draft', '草稿'),
    ], string='狀態', default='all')
    
    def action_generate_report(self):
        """產生報表"""
        self.ensure_one()
        
        # 驗證日期
        if self.date_from > self.date_to:
            raise UserError('開始日期不能大於結束日期！')
        
        # 建立查詢條件
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        if self.state != 'all':
            domain.append(('state', '=', self.state))
        
        if self.category_ids:
            domain.append(('category_id', 'in', self.category_ids.ids))
        
        if self.asset_ids:
            domain.append(('asset_id', 'in', self.asset_ids.ids))
        
        if self.department_ids:
            domain.append(('asset_id.account_analytic_id', 'in', self.department_ids.ids))
        
        # 查詢折舊記錄
        depreciations = self.env['asset.depreciation'].search(domain, order='date, asset_id')
        
        if not depreciations:
            raise UserError('沒有找到符合條件的折舊記錄！')
        
        # 建立暫存報表資料
        self.env['asset.depreciation.report'].search([('wizard_id', '=', self.id)]).unlink()
        
        report_lines = []
        for dep in depreciations:
            report_lines.append({
                'wizard_id': self.id,
                'depreciation_id': dep.id,
                'date': dep.date,
                'asset_id': dep.asset_id.id,
                'asset_code': dep.asset_id.code,
                'asset_name': dep.asset_id.name,
                'category_id': dep.category_id.id,
                'depreciation_amount': dep.depreciation_amount,
                'accumulated_depreciation': dep.accumulated_depreciation,
                'value': dep.value,
                'state': dep.state,
            })
        
        reports = self.env['asset.depreciation.report'].create(report_lines)
        
        # 返回樹狀視圖
        return {
            'type': 'ir.actions.act_window',
            'name': '折舊明細表',
            'res_model': 'asset.depreciation.report',
            'view_mode': 'tree',
            'target': 'current',
            'domain': [('wizard_id', '=', self.id)],
        }


class AssetDepreciationReport(models.TransientModel):
    """折舊明細表資料（暫存）"""
    _name = 'asset.depreciation.report'
    _description = '折舊明細表資料'
    _order = 'date, asset_code'

    wizard_id = fields.Many2one('asset.depreciation.report.wizard', string='精靈', ondelete='cascade')
    depreciation_id = fields.Many2one('asset.depreciation', string='折舊記錄')
    date = fields.Date('折舊日期')
    asset_id = fields.Many2one('asset.master', string='財產編號')
    asset_code = fields.Char('財產編號')
    asset_name = fields.Char('資產名稱')
    category_id = fields.Many2one('asset.category', string='資產類別')
    depreciation_amount = fields.Float('本期折舊')
    accumulated_depreciation = fields.Float('累計折舊')
    value = fields.Float('帳面價值')
    state = fields.Selection([
        ('draft', '草稿'),
        ('posted', '已過帳'),
        ('reversed', '已沖銷')
    ], string='狀態')


class AssetDepreciationReportQWeb(models.AbstractModel):
    """折舊明細表 QWeb 報表解析器"""
    _name = 'report.ji_accounting_asset.report_asset_depreciation'
    _description = '折舊明細表 QWeb 報表'

    @api.model
    def _get_report_values(self, docids, data=None):
        """準備報表資料"""
        docs = self.env['asset.depreciation.report'].browse(docids)
        wizard_id = self.env.context.get('active_id')
        wizard = self.env['asset.depreciation.report.wizard'].browse(wizard_id) if wizard_id else None
        
        # 計算統計資料
        total_depreciation = sum(docs.mapped('depreciation_amount'))
        total_accumulated = sum(docs.mapped('accumulated_depreciation'))
        
        return {
            'doc_ids': docids,
            'doc_model': 'asset.depreciation.report',
            'docs': docs,
            'company': self.env.company,
            'wizard': wizard,
            'total_depreciation': total_depreciation,
            'total_accumulated': total_accumulated,
        }