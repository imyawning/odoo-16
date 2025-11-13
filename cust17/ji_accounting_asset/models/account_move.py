# 錯誤
# -*- coding: utf-8 -*-
# Copyright (c) 2025 Ji Twins Studio
# License: Commercial License - see LICENSE file for details.

from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # 在這裡添加您需要客製化的欄位
    # 例如：
    # asset_related = fields.Boolean('與資產相關', default=False)
    pass