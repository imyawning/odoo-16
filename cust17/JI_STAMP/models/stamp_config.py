from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StampConfig(models.Model):
    _name = 'stamp.config'
    _description = '用印申請設定'
    _rec_name = 'company_id'

    company_id = fields.Many2one('res.company', string='公司', required=True, default=lambda self: self.env.company)

    # EFGP 設定
    efgp_enabled = fields.Boolean('啟用 EFGP 整合', default=False)
    efgp_soap_url = fields.Char('EFGP SOAP URL',
                                default='http://192.168.3.229:8086/NaNaWeb/services/WorkflowService?wsdl',
                                help="EFGP 系統的 SOAP 服務網址")

    # 已移除：efgp_share_root 欄位

    _sql_constraints = [
        ('unique_company_config', 'unique(company_id)', '每個公司只能有一個設定記錄！')
    ]

    @api.model
    def get_config(self):
        """取得設定"""
        config = self.search([('company_id', '=', self.env.company.id)], limit=1)
        if not config:
            config = self.create({
                'company_id': self.env.company.id,
            })
        return config

    @api.model
    def ensure_config_exists(self):
        """確保設定記錄存在"""
        return self.get_config()

    @api.model
    def create(self, vals_list):
        """創建設定記錄"""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        records = super().create(vals_list)

        # 確保每個記錄都有必要的欄位
        for record in records:
            if not record.company_id:
                record.company_id = self.env.company

        return records

    def is_efgp_enabled(self):
        """檢查 EFGP 是否啟用"""
        config = self.get_config()
        return config.efgp_enabled and config.efgp_soap_url

    def test_efgp_connection(self):
        import requests
        url = self.efgp_soap_url
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                msg = '連線成功！'
            else:
                msg = f'連線失敗，狀態碼：{resp.status_code}'
        except Exception as e:
            msg = f'連線失敗：{e}'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '測試 EFGP 連線',
                'message': msg,
                'sticky': False,
            }
        }