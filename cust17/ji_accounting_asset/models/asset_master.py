# 資產主檔
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ji Twins Studio
# License: Commercial License - see LICENSE file for details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

class AssetMaster(models.Model):
    """資產主檔"""
    _name = 'asset.master'
    _description = '資產主檔'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code desc'
    _rec_name = 'code'

    code = fields.Char('財產編號', required=True, tracking=True, copy=False,  default=lambda self: self._get_next_temp_code(), index=True)
    name = fields.Char('資產名稱', required=True, tracking=True)
    group = fields.Char(string='資產群組')
    category_id = fields.Many2one('asset.category', string='資產類別', required=True, tracking=True)
    supplier_id = fields.Many2one('res.partner', string='供應商')
    unit = fields.Many2one('uom.uom', string='單位')
    quantity = fields.Float('數量', default=1.0)
    unit_price = fields.Float('單價')
    amount = fields.Float('金額', required=True, tracking=True)
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirm', '確認'),
        ('depreciation', '折舊中'),
        ('done', '折畢'),
        ('written_off', '已銷帳'),
    ], string='狀態', default='draft', tracking=True, readonly=True)
    
    # 折舊相關
    purchase_date = fields.Date('取得日期', required=True, tracking=True, default=fields.Date.context_today)
    account_date = fields.Date('入帳日期', required=True, tracking=True, default=fields.Date.context_today)
    depreciation_date = fields.Date(string='開始折舊日期', readonly=True)
    depreciation_method = fields.Selection([
        ('0_no_depreciation', '0.不提折舊'),
        ('1_straight_line', '1.平均年限法-無殘值'),
        ('2_straight_line_residual', '2.平均年限法-有殘值'),
    ], string='折舊方法')
    depreciation_months = fields.Integer(string='耐用年限(月)')
    remaining_months = fields.Integer(string='未耐用年限(月)')
    reserved_residual = fields.Float('預留殘值')
    ytd_depreciation = fields.Float('今年累折')
    accumulated_depreciation = fields.Float('累計折舊', tracking=True)
    value = fields.Float('帳面價值')
    last_depreciation_date = fields.Date('最近折舊日期', tracking=True, readonly=True)
    
    is_redepreciation = fields.Boolean('折畢再提', default=False)
    redepreciation_months = fields.Integer('折畢再提月數')
    
    asset_account_id = fields.Many2one('account.account',string='資產科目',)
    asset_account_acc_id = fields.Many2one('account.account',string='累折科目',)
    asset_account_dep_id = fields.Many2one('account.account',string='折舊科目', tracking=True)
    
    # 相關資訊
    invoice_id = fields.Many2one('account.move', string='帳款編號')
    ref = fields.Char(string='參考號碼')
    responsible_id = fields.Many2one('res.users', string='保管人', tracking=True)
    account_analytic_id = fields.Many2one('account.analytic.account', string='保管部門', tracking=True)
    location = fields.Char('存放地點' , tracking=True)
    notes = fields.Char('備註')
    
    # 折舊明細數量
    depreciation_count = fields.Integer(compute='_compute_depreciation_count', string='折舊明細數量')
    
    _sql_constraints = [
        ('code_uniq', 'unique(code)', '財產編號必須唯一!')
    ]
   
    @api.onchange('account_date')
    def _onchange_account_date(self):
        config = self.env['asset.config'].search([], limit=1)
        start_type = config.depreciation_start_type or 'next_month'

        base_date = self.account_date
        if start_type == 'next_month':
            # 次月月底
            next_month = base_date + relativedelta(months=1)
            last_day = calendar.monthrange(next_month.year, next_month.month)[1]
            self.depreciation_date = date(next_month.year, next_month.month, last_day)
        else:
            # 當月月底
            last_day = calendar.monthrange(base_date.year, base_date.month)[1]
            self.depreciation_date = date(base_date.year, base_date.month, last_day)

    @api.onchange('unit_price')
    def _onchange_unit_compute_amount(self):
        for rec in self:
            if rec.unit_price is not None and rec.quantity:
                rec.amount = rec.unit_price * rec.quantity
                config = self.env['asset.config'].sudo().search([], limit=1)
                currency = rec.env.company.currency_id
                if rec.amount > 0 and rec.depreciation_method == '2_straight_line_residual':
                    rec.reserved_residual = currency.round(rec.amount / (rec.depreciation_months + 12) * 12)
                else:
                    rec.reserved_residual = 0.0
                rec.value = (rec.amount or 0.0) - (rec.accumulated_depreciation or 0.0)

    @api.onchange('amount', 'accumulated_depreciation', 'reserved_residual', 'quantity')
    def _onchange_amount_compute_unit_price(self):
        for rec in self:
            if rec.amount is not None and rec.quantity:
                rec.unit_price = rec.amount / rec.quantity if rec.quantity != 0 else 0
                config = self.env['asset.config'].sudo().search([], limit=1)
                currency = rec.env.company.currency_id
                if rec.amount > 0 and rec.depreciation_method == '2_straight_line_residual':
                    rec.reserved_residual = currency.round(rec.amount / (rec.depreciation_months + 12) * 12)
                else:
                    rec.reserved_residual = 0.0
                rec.value = (rec.amount or 0.0)  - (rec.accumulated_depreciation or 0.0)
    @api.onchange('depreciation_method')
    def _onchange_depreciation_method(self):
        self._onchange_amount_compute_unit_price()
    
    @api.onchange('category_id')
    def _onchange_category_id_set_defaults(self):
        if self.category_id:
            self.depreciation_method = self.category_id.depreciation_method
            self.depreciation_months = self.category_id.depreciation_months
            self.remaining_months = self.category_id.depreciation_months
            self.is_redepreciation = self.category_id.is_redepreciation
            self.redepreciation_months = self.category_id.redepreciation_months
            self.asset_account_id = self.category_id.asset_account_id
            self.asset_account_acc_id = self.category_id.asset_account_acc_id
            self.asset_account_dep_id = self.category_id.asset_account_dep_id
    
    @api.model
    def _get_next_temp_code(self):
        # 找出所有以 New 或 New- 開頭的現有代碼
        existing_codes = self.search([('code', '=like', 'New%')]).mapped('code')
        next_seq = 1
    
        for code in existing_codes:
            if code == 'New':
                next_seq = max(next_seq, 2)
            elif code.startswith('New-'):
                try:
                    num = int(code[4:])
                    next_seq = max(next_seq, num + 1)
                except ValueError:
                    continue

        return 'New-0001' if next_seq == 1 else f"New-{str(next_seq).zfill(4)}"

    def action_confirm(self):
        config = self.env['asset.config'].sudo().search([], limit=1)
        if not config:
            raise ValidationError("請先建立固定資產設定（asset.config）")

        for asset in self:
            if config.asset_close_date and asset.account_date and asset.account_date <= config.asset_close_date:
                raise ValidationError('入帳日期不得早於或等於關帳日期（%s）！' % config.asset_close_date)
            if asset.code[:3] == 'New':
                if config.asset_code_method == 'category' and asset.category_id:
                    prefix = asset.category_id.code
                    padding = config.asset_code_padding
                    if not padding:
                        raise ValidationError("請先設定資產編碼長度（流水號位數）")

                    max_code = self.search([
                        ('category_id', '=', asset.category_id.id),
                        ('code', 'like', prefix + '%'),
                        ('id', '!=', asset.id),
                    ], order='code desc', limit=1)

                    if max_code and max_code.code.startswith(prefix):
                        current_number = int(max_code.code[len(prefix):])
                        next_number = current_number + 1
                    else:
                        next_number = 1

                    asset.code = f"{prefix}{str(next_number).zfill(padding)}"
                    asset.group = asset.code
                else:
                    asset.code = self.env['ir.sequence'].next_by_code('asset.master') or 'New'
                    asset.group = asset.code

            asset.state = 'confirm'
    
    def action_draft(self):
        for rec in self:
            if rec.state == 'draft':
                raise ValidationError('已經是草稿狀態')
            rec.state = 'draft'
            
    @api.constrains('account_date', 'purchase_date')
    def _check_dates(self):
        for record in self:
            if record.account_date and record.purchase_date and record.account_date < record.purchase_date:
                raise ValidationError('入帳日期不能早於取得日期')

    def unlink(self):
        """覆寫刪除方法，只允許刪除草稿狀態的記錄"""
        for record in self:
            if record.state != 'draft':
                raise ValidationError('只能刪除草稿狀態的資產記錄')
        return super(AssetMaster, self).unlink()

    def open_related_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': '來源帳款',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }

    @api.depends('name')
    def _compute_depreciation_count(self):
        """計算折舊明細數量"""
        for record in self:
            record.depreciation_count = self.env['asset.depreciation'].search_count([
                ('asset_id', '=', record.id)
            ])

    def action_view_depreciation(self):
        """查看折舊明細"""
        self.ensure_one()
        return {
            'name': '折舊明細',
            'type': 'ir.actions.act_window',
            'res_model': 'asset.depreciation',
            'view_mode': 'tree,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {
                'create': False,
                'edit': False,
            },
        }

    def action_batch_confirm(self):
        for rec in self:
            rec.action_confirm()



