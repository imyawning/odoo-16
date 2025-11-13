from odoo import fields, models, api


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    ithome_person = fields.Many2one('res.partner', string='業務主管')
    ithome_date = fields.Date(string='日期')
    ithome_info = fields.Char(string='電動床資訊')
