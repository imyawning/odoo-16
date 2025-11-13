# 財產目錄清冊
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ji Twins Studio
# License: Commercial License - see LICENSE file for details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date
import calendar
import logging
import io
import base64
import xlsxwriter
from odoo.tools.misc import format_date
from datetime import timedelta
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class AssetMasterReportWizard(models.TransientModel):
    _name = "asset.master.report.wizard"
    _description = "財產目錄清冊"

    def _default_report_date(self):
        config = self.env['asset.config'].search([], limit=1)
        if config and config.asset_close_date:
            return config.asset_close_date
        return date.today()

    category_id = fields.Many2many('asset.category', string='資產類別')
    asset_id = fields.Many2many('asset.master', string='財產編號')
    department_id = fields.Many2many('account.analytic.account', string='保管部門')
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirm', '確認'),
        ('depreciation', '折舊中'),
        ('done', '折畢'),
        ('written_off', '已銷帳'),
    ], string='狀態')
    report_date = fields.Date(string='報表日期', required=True, default=_default_report_date)
    output_format = fields.Selection([
        ('table', '表格'),
        ('pdf', 'PDF'),
        ('excel', 'EXCEL'),
    ], string="輸出格式", default='pdf', required=True)
    excel_file = fields.Binary('Excel檔案')
    excel_file_name = fields.Char('Excel檔案名稱')

    def action_generate_report(self):
        self.env['asset.master.report'].search([('wizard_id', '=', self.id)]).unlink()
        domain = []
        if self.category_id:
            domain += [('category_id', 'in', self.category_id.ids)]
        if self.asset_id:
            domain += [('id', 'in', self.asset_id.ids)]
        if self.department_id:
            domain += [('account_analytic_id', 'in', self.department_id.ids)]
        if self.state:
            domain += [('state', 'in', [self.state])]

        assets = self.env['asset.master'].search(domain, order='category_id, code')
        temp_lines = []

        for asset in assets:
            # 取得報表日期的折舊資料
            first_day = self.report_date.replace(day=1)
            last_day = self.report_date
            depreciation_record = self.env['asset.depreciation'].search([
                ('asset_id', '=', asset.id),
                ('date', '>=', first_day),
                ('date', '<=', last_day)
            ], order='date desc', limit=1)

            temp_lines.append({
                'wizard_id': self.id,
                'group': asset.group,
                'category_id': asset.category_id.id,
                'category_name': asset.category_id.name,
                'asset_id': asset.id,
                'asset_code': asset.code,
                'asset_name': asset.name,
                'account_date': asset.account_date,
                'depreciation_months': asset.depreciation_months,
                'remaining_months': depreciation_record.remaining_months if depreciation_record else 0,
                'quantity': asset.quantity,
                'amount': asset.amount,
                'ytd_depreciation': depreciation_record.ytd_depreciation if depreciation_record else 0.0,
                'accumulated_depreciation': depreciation_record.accumulated_depreciation if depreciation_record else 0.0,
                'value': depreciation_record.value if depreciation_record else asset.amount,
                'state': asset.state,
                'department_id': asset.account_analytic_id.id if asset.account_analytic_id else False,
                'responsible_id': asset.responsible_id.id if asset.responsible_id else False,
                'location': asset.location or '',
            })

        results = self.env['asset.master.report'].create(temp_lines)
        if not results:
            raise UserError("沒有符合條件的財產目錄資料！")

        if self.output_format == 'table':
            return {
                'type': 'ir.actions.act_window',
                'name': '財產目錄清冊',
                'res_model': 'asset.master.report',
                'view_mode': 'tree',
                'target': 'current',
                'domain': [('wizard_id', '=', self.id)],
            }
        elif self.output_format == 'pdf':
            report_ref = 'ji_accounting_asset.action_asset_master_report_pdf'
            return self.env.ref(report_ref).report_action(results)
        elif self.output_format == 'excel':
            return self._export_to_excel(results)

    def _export_to_excel(self, report_lines):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('財產目錄清冊')

        title_format = workbook.add_format({'align': 'center', 'bold': True, 'font_size': 14})
        header_format = workbook.add_format({'align': 'center', 'bold': True, 'bg_color': '#DCE6F1', 'border': 1})
        number_format = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})
        right_format = workbook.add_format({'align': 'right'})

        worksheet.set_column('A:P', 16)
        worksheet.merge_range('A1:P1', self.env.company.name or '', title_format)
        worksheet.merge_range('A2:P2', '財產目錄清冊', title_format)
        worksheet.merge_range('O3:P3', f'報表日期：{self.report_date.strftime("%Y-%m-%d")}', right_format)

        headers = ['資產群組', '資產類別', '財產編號', '財產名稱', '入帳日期', '耐用月數', '剩餘月數',
                   '數量', '取得金額', '本年折舊', '累計折舊', '帳面價值', '目前狀態', '保管部門', '保管人', '存放位置']

        for col, header in enumerate(headers):
            worksheet.write(3, col, header, header_format)

        row = 4
        for line in report_lines:
            worksheet.write(row, 0, line.group or '')
            worksheet.write(row, 1, line.category_id.name or '')
            worksheet.write(row, 2, line.asset_code or '')
            worksheet.write(row, 3, line.asset_name or '')
            worksheet.write(row, 4, line.account_date and line.account_date.strftime('%y/%m/%d') or '')
            worksheet.write(row, 5, line.depreciation_months or 0)
            worksheet.write(row, 6, line.remaining_months if line.remaining_months else 0)
            worksheet.write(row, 7, line.quantity or 0)
            worksheet.write(row, 8, line.amount or 0.0, number_format)
            worksheet.write(row, 9, line.ytd_depreciation or 0.0, number_format)
            worksheet.write(row, 10, line.accumulated_depreciation or 0.0, number_format)
            worksheet.write(row, 11, line.value or 0.0, number_format)

            # 狀態顯示
            state_display = {
                'draft': '草稿',
                'confirm': '確認',
                'depreciation': '折舊中',
                'done': '折畢',
                'written_off': '已銷帳',
            }
            worksheet.write(row, 12, state_display.get(line.state, ''))

            worksheet.write(row, 13, line.department_id.name if line.department_id else '')
            worksheet.write(row, 14, line.responsible_id.name if line.responsible_id else '')
            worksheet.write(row, 15, line.location or '')
            row += 1

        workbook.close()
        output.seek(0)
        xlsx_data = output.read()
        self.excel_file = base64.b64encode(xlsx_data)
        self.excel_file_name = '財產目錄清冊.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/asset.master.report.wizard/{self.id}/excel_file/{self.excel_file_name}?download=true',
            'target': 'self'
        }


class AssetMasterReport(models.TransientModel):
    _name = "asset.master.report"
    _description = '暫存財產目錄清冊'
    _order = 'category_id, asset_code'

    wizard_id = fields.Many2one('asset.master.report.wizard', string="精靈")
    group = fields.Char(string='資產群組')
    asset_id = fields.Many2one('asset.master', string='財產編號')
    asset_code = fields.Char(string='財產編號')
    asset_name = fields.Char(string='財產名稱')
    category_id = fields.Many2one('asset.category', string='資產類別')
    category_name = fields.Char(string='資產分類')
    account_date = fields.Date(string='入帳日期')
    depreciation_months = fields.Integer(string='耐用年限(月)')
    remaining_months = fields.Integer(string='未耐用年限(月)')
    quantity = fields.Integer(string='數量')
    amount = fields.Float(string='取得金額')
    ytd_depreciation = fields.Float(string='本年折舊')
    accumulated_depreciation = fields.Float(string='累計折舊')
    value = fields.Float(string='帳面價值')
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirm', '確認'),
        ('depreciation', '折舊中'),
        ('done', '折畢'),
        ('written_off', '已銷帳'),
    ], string='目前狀態')
    department_id = fields.Many2one('account.analytic.account', string='保管部門')
    responsible_id = fields.Many2one('res.users', string='保管人')
    location = fields.Char(string='存放位置')


class AssetMasterReportParser(models.AbstractModel):
    _name = 'report.ji_accounting_asset.asset_master_report_template'
    _description = '財產目錄清冊報表解析器'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['asset.master.report'].browse(docids)
        wizard_id = self.env.context.get('active_id')
        wizard = self.env['asset.master.report.wizard'].browse(wizard_id) if wizard_id else None
        report_date = wizard.report_date if wizard else None

        # 狀態顯示對應
        state_display = {
            'draft': '草稿',
            'confirm': '確認',
            'depreciation': '折舊中',
            'done': '折畢',
            'written_off': '已銷帳',
        }

        return {
            'doc_ids': docids,
            'doc_model': 'asset.master.report',
            'docs': docs,
            'company': self.env.company,
            'report_date': report_date,
            'category': ', '.join(wizard.category_id.mapped('name')) if wizard and wizard.category_id else '',
            'asset': ', '.join(wizard.asset_id.mapped('name')) if wizard and wizard.asset_id else '',
            'department': ', '.join(wizard.department_id.mapped('name')) if wizard and wizard.department_id else '',
            'state': state_display.get(wizard.state, '') if wizard and wizard.state else '',
            'format_date': lambda d: format_date(self.env, d),
        }